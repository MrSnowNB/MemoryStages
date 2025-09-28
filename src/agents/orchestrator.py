"""
Stage 7 MVP - Rule-Based Orchestrator
Manages Ollama agent swarm with strict memory validation and rule-based decision making.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
from .agent import AgentMessage, AgentResponse
from .registry import AgentRegistry
from .memory_adapter import MemoryAdapter
from ..core import dao
from ..core.config import (
    OLLAMA_MODEL,
    SWARM_ENABLED,
    SWARM_AGENT_COUNT,
    SWARM_ORCHESTRATOR_TYPE,
    RESPONSE_VALIDATION_STRICT,
    debug_enabled
)


@dataclass
class OrchestratorDecision:
    """Represents orchestrator's decision on which response to use."""
    selected_response: str
    confidence: float
    agents_consulted: List[str]
    validation_passed: bool
    memory_sources: List[str]
    decision_reasoning: str


class RuleBasedOrchestrator:
    """
    Rule-based orchestrator managing Ollama agent swarm.
    Validates all responses against canonical memory before user delivery.
    Uses simple heuristics to select best response from agent swarm.
    """

    def __init__(self):
        self.agent_registry = AgentRegistry()
        self.memory_adapter = MemoryAdapter()
        self.archives: List[Dict[str, Any]] = []  # Store past decisions for learning

        # Initialize swarm if SWARM_ENABLED
        if SWARM_ENABLED:
            self.agents = self._initialize_swarm()
        else:
            self.agents = []

        # Log orchestrator startup
        dao.add_event(
            actor="orchestrator",
            action="orchestrator_started",
            payload=json.dumps({
                "swarm_enabled": SWARM_ENABLED,
                "initial_agent_count": len(self.agents),
                "model": OLLAMA_MODEL,
                "orchestrator_type": "rule_based",
                "memory_adapter_enabled": True
            })
        )

    def _initialize_swarm(self) -> List[str]:
        """Initialize swarm of Ollama agents using global model."""
        try:
            created_agents = self.agent_registry.initialize_swarm()
            return created_agents
        except Exception as e:
            # Log initialization failure but continue
            dao.add_event(
                actor="orchestrator",
                action="swarm_initialization_failed",
                payload=json.dumps({"error": str(e)})
            )
            return []

    def process_user_message(self, message: str, session_id: str, user_id: Optional[str] = None) -> AgentResponse:
        """
        Process user message through agent swarm with strict validation.
        All responses must be validated against canonical memory.

        Args:
            message: User input message
            session_id: Session identifier
            user_id: Optional user identifier

        Returns:
            Validated response from agent swarm
        """
        start_time = datetime.now()

        try:
            # Create agent message for processing
            agent_message = AgentMessage(
                content=message,
                role="user",
                timestamp=datetime.now(),
                metadata={"session_id": session_id, "user_id": user_id},
                model_used=OLLAMA_MODEL
            )

            # Get memory context for validation (will be enhanced in next slice)
            memory_context = self._get_basic_memory_context(message, user_id)

            # Collect responses from swarm
            agent_responses = self._collect_swarm_responses(agent_message, session_id)

            # Apply rule-based decision logic
            decision = self._make_orchestrator_decision(
                user_message=message,
                agent_responses=agent_responses,
                memory_context=memory_context
            )

            # Validate final response against memory
            validated_response = self._validate_response_against_memory(
                response=decision.selected_response,
                memory_context=memory_context,
                user_query=message
            )

            # Create final response
            final_response = AgentResponse(
                content=validated_response,
                model_used=OLLAMA_MODEL,
                confidence=decision.confidence,
                tool_calls=[],
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                metadata={
                    "orchestrator_type": "rule_based",
                    "agents_consulted": decision.agents_consulted,
                    "validation_passed": decision.validation_passed,
                    "memory_sources": decision.memory_sources,
                    "swarm_size": len(agent_responses)
                },
                audit_info={
                    "session_id": session_id,
                    "user_id": user_id,
                    "decision_reasoning": decision.decision_reasoning,
                    "processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000)
                }
            )

            # Archive decision for potential future learning
            self._archive_decision(decision, agent_responses, message, final_response)

            # Log orchestrator decision
            self._log_orchestrator_decision(decision, final_response, message)

            return final_response

        except Exception as e:
            # Create comprehensive error response but don't fail entirely
            error_msg = "I apologize, but I encountered an error processing your request. Please try rephrasing your question."
            if debug_enabled():
                error_msg += f" (Debug: {str(e)})"

            error_response = AgentResponse(
                content=error_msg,
                model_used=OLLAMA_MODEL,
                confidence=0.0,
                tool_calls=[],
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                metadata={"error": str(e), "orchestrator_type": "rule_based"},
                audit_info={
                    "session_id": session_id,
                    "error_occurred": True,
                    "error_type": type(e).__name__
                }
            )

            # Log error
            dao.add_event(
                actor="orchestrator_error",
                action="processing_failed",
                payload=json.dumps({
                    "error": str(e),
                    "session_id": session_id,
                    "model": OLLAMA_MODEL,
                    "swarm_enabled": SWARM_ENABLED
                })
            )

            return error_response

    def _collect_swarm_responses(self, message: AgentMessage, session_id: str) -> List[AgentResponse]:
        """Collect responses from all agents in swarm."""
        if not self.agents:
            return []

        responses = []

        for agent_id in self.agents:
            try:
                agent = self.agent_registry.get_agent(agent_id)
                if agent:
                    # For MVP, pass empty context (will be enhanced later)
                    context = []  # TODO: Add conversation history context
                    response = agent.process_message(message, context)
                    responses.append(response)
                else:
                    # Log missing agent but continue
                    dao.add_event(
                        actor="orchestrator_warning",
                        action="agent_not_found",
                        payload=json.dumps({"agent_id": agent_id, "session_id": session_id})
                    )
            except Exception as e:
                # Log agent failure but continue with other agents
                dao.add_event(
                    actor="orchestrator_error",
                    action="agent_failed",
                    payload=json.dumps({
                        "agent_id": agent_id,
                        "error": str(e),
                        "session_id": session_id
                    })
                )

        return responses

    def _make_orchestrator_decision(self, user_message: str,
                                  agent_responses: List[AgentResponse],
                                  memory_context: List[Dict[str, Any]]) -> OrchestratorDecision:
        """
        Rule-based decision making for response selection.
        Prioritizes responses that can be validated against memory.
        """
        if not agent_responses:
            return OrchestratorDecision(
                selected_response="I don't have enough information to answer that question right now. Please try again later.",
                confidence=0.1,
                agents_consulted=[],
                validation_passed=False,
                memory_sources=[],
                decision_reasoning="No agent responses available"
            )

        best_response = None
        best_score = 0.0
        reasoning_parts = []
        consulted_agents = []

        for response in agent_responses:
            consulted_agents.append(f"agent_{response.metadata.get('agent_id', 'unknown')}")
            score = self._score_response(response, user_message, memory_context)

            if response.metadata:
                reasoning_parts.append(f"agent_{response.metadata.get('agent_id', 'unknown')}_score_{score:.2f}")

            if score > best_score:
                best_score = score
                best_response = response

        # Validate final decision
        validation_passed = best_score > 0.3  # MVP threshold
        if RESPONSE_VALIDATION_STRICT and not validation_passed:
            validation_passed = False

        if best_response:
            return OrchestratorDecision(
                selected_response=best_response.content,
                confidence=min(best_score, 0.95),  # Cap at 0.95
                agents_consulted=consulted_agents,
                validation_passed=validation_passed,
                memory_sources=[ctx.get("source", "unknown") for ctx in memory_context],
                decision_reasoning="; ".join(reasoning_parts) if reasoning_parts else "default_selection"
            )
        else:
            return OrchestratorDecision(
                selected_response="I need more information to help you with that question.",
                confidence=0.1,
                agents_consulted=consulted_agents,
                validation_passed=False,
                memory_sources=[],
                decision_reasoning="no_suitable_response_found"
            )

    def _score_response(self, response: AgentResponse, user_query: str,
                       memory_context: List[Dict[str, Any]]) -> float:
        """
        Score a response based on multiple criteria.
        Returns score between 0.0 and 1.0.
        """
        score = 0.0

        # Rule 1: Prefer validated responses (0.4 points)
        if memory_context and self._response_references_memory(response.content, memory_context):
            score += 0.4

        # Rule 2: Prefer confident agent responses (0.3 * confidence)
        score += response.confidence * 0.3

        # Rule 3: Prefer responses with reasonable length (0.2 points)
        content_length = len(response.content)
        if 20 <= content_length <= 500:
            score += 0.2
        elif content_length < 20:
            score -= 0.1  # Penalize very short responses
        elif content_length > 500:
            score -= 0.1  # Penalize very long responses

        # Rule 4: Avoid potentially hallucinated responses (up to -0.2 points)
        hallucination_penalty = self._calculate_hallucination_penalty(response.content)
        score += hallucination_penalty

        # Rule 5: Prefer responses that directly address the query (0.1 points)
        if self._response_addresses_query(response.content, user_query):
            score += 0.1

        return max(0.0, min(score, 1.0))  # Clamp to [0.0, 1.0]

    def _create_error_response(self, error_msg: str, original_message: AgentMessage) -> AgentResponse:
        """Create consistent error response format."""
        return AgentResponse(
            content=error_msg,
            model_used=OLLAMA_MODEL,
            confidence=0.0,
            tool_calls=[],
            processing_time_ms=0,
            metadata={
                'agent_type': 'orchestrator',
                'orchestrator_type': 'rule_based',
                'error_occurred': True
            },
            audit_info={
                'timestamp': datetime.now().isoformat(),
                'error': error_msg,
                'message_length': len(original_message.content) if original_message else 0
            }
        )

    def _validate_response_against_memory(self, response: str,
                                        memory_context: List[Dict[str, Any]],
                                        user_query: str) -> str:
        """
        Validate response against canonical memory.
        Returns validated response or requests clarification if invalid.
        """
        if not RESPONSE_VALIDATION_STRICT:
            return response

        # Basic validation: Check for factual claims vs memory
        if memory_context and self._response_makes_factual_claims(response):
            # MVP: Simple keyword overlap validation
            if self._response_references_memory(response, memory_context):
                return response
            else:
                return "I don't have verified information about that topic. Could you please provide more specific details?"
        else:
            # No factual claims or no memory context - allow response
            return response

    def _response_references_memory(self, response: str, memory_context: List[Dict[str, Any]]) -> bool:
        """Check if response references information from memory context."""
        if not memory_context:
            return False

        response_lower = response.lower()
        for ctx in memory_context:
            content = ctx.get("content", "").lower()
            if content and len(content) > 10:
                # Simple keyword overlap check (enhanced matching will come in next slice)
                content_words = set(content.split())
                response_words = set(response_lower.split())
                overlap = len(content_words & response_words)
                if overlap >= min(3, len(content_words) // 2):
                    return True
        return False

    def _calculate_hallucination_penalty(self, response: str) -> float:
        """Calculate penalty for potentially hallucinated response characteristics."""
        hallucination_indicators = [
            "according to my knowledge",
            "i remember that",
            "in my experience",
            "i believe that",
            "it's commonly known that",
            "as far as i know",
            "i think that"
        ]

        response_lower = response.lower()
        penalty = 0.0

        for indicator in hallucination_indicators:
            if indicator in response_lower:
                penalty -= 0.05  # Small penalty per indicator

        return max(penalty, -0.2)  # Cap penalty at -0.2

    def _response_addresses_query(self, response: str, query: str) -> bool:
        """Check if response directly addresses the user's query."""
        query_words = set(query.lower().split())
        response_words = set(response.lower().split())

        overlap = len(query_words & response_words)
        return overlap >= min(2, len(query_words) // 2)

    def _response_makes_factual_claims(self, response: str) -> bool:
        """Check if response makes factual claims that should be validated."""
        factual_indicators = ['is', 'are', 'was', 'were', 'has', 'have', 'will']
        response_lower = response.lower()

        # Don't consider questions as factual claims
        if '?' in response or response_lower.startswith(('what', 'how', 'why', 'when', 'where', 'who')):
            return False

        return any(indicator in response_lower for indicator in factual_indicators)

    def _get_basic_memory_context(self, query: str, user_id: Optional[str]) -> List[Dict[str, Any]]:
        """Get memory context using memory adapter for validation."""
        try:
            return self.memory_adapter.get_validation_context(query, user_id)
        except Exception as e:
            # Log error but return empty context for safety
            dao.add_event(
                actor="orchestrator_warning",
                action="memory_context_error",
                payload=json.dumps({"error": str(e), "query_length": len(query)})
            )
            return []

    def _archive_decision(self, decision: OrchestratorDecision, agent_responses: List[AgentResponse],
                         user_message: str, final_response: AgentResponse):
        """Archive decision for potential future learning/analysis."""
        archive_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_message': user_message,
            'decision': {
                'selected_response': decision.selected_response[:100],  # Truncate for storage
                'confidence': decision.confidence,
                'agents_consulted': decision.agents_consulted,
                'validation_passed': decision.validation_passed,
                'decision_reasoning': decision.decision_reasoning
            },
            'agent_responses_count': len(agent_responses),
            'final_processing_time_ms': final_response.processing_time_ms
        }

        self.archives.append(archive_entry)

        # Keep only last 100 archives to prevent memory bloat
        if len(self.archives) > 100:
            self.archives.pop(0)

    def _log_orchestrator_decision(self, decision: OrchestratorDecision,
                                 final_response: AgentResponse, user_message: str):
        """Log orchestrator decision for audit and debugging."""
        dao.add_event(
            actor="orchestrator",
            action="decision_made",
            payload=json.dumps({
                "user_message_length": len(user_message),
                "selected_response_length": len(decision.selected_response),
                "confidence": decision.confidence,
                "agents_consulted": decision.agents_consulted,
                "validation_passed": decision.validation_passed,
                "memory_sources_count": len(decision.memory_sources),
                "decision_reasoning": decision.decision_reasoning,
                "model": OLLAMA_MODEL,
                "processing_time_ms": final_response.processing_time_ms,
                "swarm_size": len(self.agents)
            })
        )

    def get_orchestrator_status(self) -> Dict[str, Any]:
        """Get orchestrator status for monitoring."""
        swarm_health = self.agent_registry.get_swarm_health() if self.agent_registry else {}

        return {
            'orchestrator_type': 'rule_based',
            'swarm_enabled': SWARM_ENABLED,
            'model': OLLAMA_MODEL,
            'agents_available': len(self.agents),
            'swarm_health': swarm_health,
            'response_validation_strict': RESPONSE_VALIDATION_STRICT,
            'archives_count': len(self.archives),
            'timestamp': datetime.now().isoformat()
        }
