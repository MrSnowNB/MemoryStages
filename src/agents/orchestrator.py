"""
Stage 7 MVP - Rule-Based Orchestrator
Manages Ollama agent swarm with strict memory validation and rule-based decision making.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
try:
    import re
except ImportError:
    re = None  # Fallback, though re should be in stdlib
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
        try:
            import logging
            logging.getLogger().setLevel(logging.DEBUG)
        except Exception:
            pass  # Continue safely

        print("DEBUG: Orchestrator.__init__ starting...")  # Immediate debug output

        try:
            self.agent_registry = AgentRegistry()
            print("DEBUG: Agent registry created")  # Debug output
        except Exception as e:
            print(f"DEBUG: Agent registry creation failed: {e}")
            raise

        try:
            self.memory_adapter = MemoryAdapter()
            print("DEBUG: Memory adapter created")  # Debug output
        except Exception as e:
            print(f"DEBUG: Memory adapter creation failed: {e}")
            raise

        self.archives: List[Dict[str, Any]] = []  # Store past decisions for learning

        # Initialize swarm if SWARM_ENABLED
        print(f"DEBUG: SWARM_ENABLED = {SWARM_ENABLED}, OLLAMA_MODEL = {OLLAMA_MODEL}")
        if SWARM_ENABLED:
            try:
                self.agents = self._initialize_swarm()
                print(f"DEBUG: Swarm initialization completed, {len(self.agents)} agents created")
                if self.agents:
                    print(f"DEBUG: Agent IDs: {self.agents}")
                else:
                    print("DEBUG: WARNING - Swarm enabled but no agents created!")
            except Exception as e:
                print(f"DEBUG: Swarm initialization exception: {e}")
                self.agents = []
        else:
            print("DEBUG: Swarm disabled, setting empty agents list")
            self.agents = []

        # Log orchestrator startup (Stage 5)
        try:
            startup_summary = f"Rule-based orchestrator initialized with {len(self.agents)} agents"
            dao.add_event(
                user_id="system",
                session_id=None,  # System event
                event_type="system",
                message=startup_summary,
                summary="Orchestrator startup completed successfully"
            )
            print("DEBUG: Orchestrator startup event logged successfully")
        except Exception as e:
            print(f"DEBUG: Failed to log orchestrator startup event: {e}")

        print(f"DEBUG: Orchestrator initialization complete. Agents: {len(self.agents)}")

    def _initialize_swarm(self) -> List[str]:
        """Initialize swarm of Ollama agents using global model."""
        try:
            print(f"DEBUG: Orchestrator calling agent_registry.initialize_swarm()")
            created_agents = self.agent_registry.initialize_swarm()
            print(f"DEBUG: Orchestrator received agent list: {created_agents} (length: {len(created_agents)})")
            return created_agents
        except Exception as e:
            print(f"DEBUG: Orchestrator _initialize_swarm exception: {e}")
            # Log initialization failure but continue
            dao.add_event(
                user_id="system",
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
            # Check for canonical memory reads before orchestrating
            memory_read_response = self._check_canonical_memory_reads(message, user_id)
            if memory_read_response:
                # Found canonical memory - use it directly
                memory_provenance = [
                    {
                        "type": "kv",
                        "key": memory_read_response.get('key', ''),
                        "value": memory_read_response.get('value', ''),
                        "score": 1.0,
                        "explanation": "Exact/canonical match from stored key"
                    }
                ]
                final_response = AgentResponse(
                    content=memory_read_response['content'],
                    model_used=OLLAMA_MODEL,
                    confidence=1.0,  # 100% confidence for verified memory
                    tool_calls=[],
                    processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                    metadata={
                        "orchestrator_type": "rule_based",
                        "agents_consulted": [],
                        "validation_passed": True,
                        "memory_provenance": memory_provenance,
                        "canonical_memory_hit": True
                    },
                    audit_info={
                        "session_id": session_id,
                        "user_id": user_id,
                        "memory_read": True,
                        "processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000)
                    }
                )
                return final_response

            # Check for semantic memory matches before using agent swarm
            semantic_memory_response = self._check_semantic_memory_query(message, user_id)
            if semantic_memory_response:
                # Found semantic memory match - use it directly
                final_response = AgentResponse(
                    content=semantic_memory_response['content'],
                    model_used=OLLAMA_MODEL,
                    confidence=semantic_memory_response['confidence'],
                    tool_calls=[],
                    processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                    metadata={
                        "orchestrator_type": "rule_based",
                        "agents_consulted": [],
                        "validation_passed": True,
                        "memory_provenance": semantic_memory_response['memory_provenance'],
                        "semantic_memory_hit": True
                    },
                    audit_info={
                        "session_id": session_id,
                        "user_id": user_id,
                        "semantic_search": True,
                        "processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000)
                    }
                )
                return final_response

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

            # If no agents available, provide helpful fallback response
            if not self.agents:
                memory_provenance = []
                fallback_response = AgentResponse(
                    content="I'm currently unable to generate full responses because my agent swarm isn't available. However, I can still help with questions about your stored information. Try asking about your display name, favorite color, or other saved preferences.",
                    model_used=OLLAMA_MODEL,
                    confidence=0.5,
                    tool_calls=[],
                    processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                    metadata={
                        "orchestrator_type": "rule_based",
                        "agents_consulted": [],
                        "validation_passed": True,
                        "memory_provenance": memory_provenance,
                        "swarm_size": 0,
                        "fallback_mode": True
                    },
                    audit_info={
                        "session_id": session_id,
                        "user_id": user_id,
                        "fallback_reason": "no_agents_available",
                        "processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000)
                    }
                )

                # Log fallback usage
                dao.add_event(
                    user_id="system",
                    actor="orchestrator",
                    action="fallback_response_used",
                    payload=json.dumps({
                        "reason": "no_agents_available",
                        "session_id": session_id,
                        "model": OLLAMA_MODEL,
                        "swarm_enabled": SWARM_ENABLED
                    })
                )
                return fallback_response

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
            memory_provenance = [{"type": "llm", "score": decision.confidence, "explanation": "No memory match—answer generated by LLM agents."}]
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
                    "memory_provenance": memory_provenance,
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

            # Enhanced debug output for troubleshooting
            print(f"DEBUG: orchestrate_user_message exception: {str(e)}")
            print(f"DEBUG: exception type: {type(e).__name__}")
            import traceback
            print(f"DEBUG: traceback: {traceback.format_exc()}")

            error_response = AgentResponse(
                content=error_msg,
                model_used=OLLAMA_MODEL,
                confidence=0.0,
                tool_calls=[],
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                metadata={"error": str(e), "orchestrator_type": "rule_based", "agents_available": len(self.agents), "swarm_enabled": SWARM_ENABLED, "memory_provenance": []},
                audit_info={
                    "session_id": session_id,
                    "error_occurred": True,
                    "error_type": type(e).__name__,
                    "agents_count": len(self.agents)
                }
            )

            # Log error
            dao.add_event(
                user_id="system",
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
                        user_id="system",
                        actor="orchestrator_warning",
                        action="agent_not_found",
                        payload=json.dumps({"agent_id": agent_id, "session_id": session_id})
                    )
            except Exception as e:
                # Log agent failure but continue with other agents
                dao.add_event(
                    user_id="system",
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
                user_id="system",
                actor="orchestrator_warning",
                action="memory_context_error",
                payload=json.dumps({"error": str(e), "query_length": len(query), "user_id": user_id})
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
            user_id="system",
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

    def _normalize_key(self, raw: str) -> str:
        """Normalize raw keys to canonical form using same logic as chat.py"""
        from ..core.config import KEY_NORMALIZATION_STRICT
        if not KEY_NORMALIZATION_STRICT:
            return raw.strip()

        k = raw.strip().lower()
        if k in {'displayName', 'displayname', 'name'}:
            return 'displayName'
        if 'favoriteColor' in k or 'favorite color' in k:
            return 'favoriteColor'
        if 'favoriteLanguage' in k or 'favorite language' in k:
            return 'favoriteLanguage'

        # Convert spaces to camelCase for other compound words
        parts = k.split() if ' ' in k else [k]
        if not parts:
            return k
        return parts[0] + "".join(p.capitalize() for p in parts[1:])

    def _check_canonical_memory_reads(self, message: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Check if this is a canonical memory read request that should be answered
        directly from KV storage rather than through agent orchestration.

        Args:
            message: User message to check
            user_id: User ID for scoped memory access

        Returns:
            Dict with content, sources, and confidence if matched, None otherwise
        """
        message_lower = message.lower()

        # Ensure user_id defaults to 'default' for backward compatibility
        user_id = user_id or "default"

        # Known memory read patterns
        memory_patterns = [
            (r'what is my ([\w\s]+)', 'query', 'what_is_my'),
            (r'what\'s my ([\w\s]+)', 'query', 'what_is_my'),
            (r'what is (my [\w\s]+)', 'query', 'what_is_my_prefix'),
            (r'my ([\w\s]+) is what\?', 'query', 'example_reverse'),
            (r'(.+)', 'query', 'general'),  # Catchall but don't match everything
        ]

        for pattern_str, req_type, pattern_key in memory_patterns:
            match = re.search(pattern_str, message_lower, re.IGNORECASE)
            if match:
                key_candidates = []

                if 'displayName' in message_lower or 'display name' in message_lower:
                    key_candidates.append('displayName')

                if 'name' in message_lower and not key_candidates:
                    key_candidates.append('displayName')  # Default to displayName for name queries

                # Add other common patterns
                for phrase in ['favoriteColor', 'favorite color', 'name', 'age']:
                    if phrase in message_lower.replace(' ', ''):
                        # Simple key normalization
                        if phrase == 'favorite color':
                            key_candidates.insert(0, 'favoriteColor')
                        elif phrase == 'favorite_color':
                            key_candidates.insert(0, 'favoriteColor')
                        elif phrase == 'name':
                            key_candidates.insert(0, 'displayName')
                        else:
                            key_candidates.append(phrase)

                # Try to get value from memory with user_id
                for key in key_candidates:
                    try:
                        kv_value = dao.get_key(user_id=user_id, key=key)
                        if kv_value and kv_value.value:
                            canonical_key = self._normalize_key(key)
                            response_content = f"Your {canonical_key} is '{kv_value.value}'."
                            return {
                                'content': response_content,
                                'key': canonical_key,  # Return canonical key
                                'value': kv_value.value,
                                'confidence': 1.0,
                                'memory_hit': True
                            }
                    except Exception:
                        continue  # Try next key

        return None

    def _check_semantic_memory_query(self, message: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Check if this is a query that should prefer semantic hits over agent responses.
        When VECTOR is ON and scores exceed threshold, prefer semantic hits and attach memory_provenance.

        Enhanced to extract cleaner search terms from verbose memory queries.

        Returns eligible semantic matches for UI Memory Results panel if threshold met.
        """
        try:
            from ..core.search_service import semantic_search
            from ..core.config import are_vector_features_enabled

            # Only proceed if vector features are enabled
            if not are_vector_features_enabled():
                print("DEBUG: Vector features not enabled")
                return None

            # Ensure user_id defaults to 'default'
            user_id = user_id or "default"

            # Extract cleaner search terms from memory queries
            search_query = self._extract_memory_search_terms(message)

            # Fallback to full message if extraction fails
            if not search_query or not search_query.strip():
                search_query = message

            print(f"DEBUG: Semantic search using query: '{search_query}' (extracted from: '{message}')")

            # Perform semantic search - get top_k=5 for better coverage
            search_results = semantic_search(query=search_query, user_id=user_id, top_k=5)

            if not search_results:
                print("DEBUG: No semantic search results found")
                return None

            # Filter results by threshold - only return if score >= threshold (0.6)
            eligible_hits = [h for h in search_results if h.get("score", 0.0) >= 0.6]
            if not eligible_hits:
                print(f"DEBUG: No eligible hits above threshold 0.6: {[round(h.get('score', 0), 3) for h in search_results]}")
                return None

            print(f"DEBUG: Found {len(eligible_hits)} eligible semantic hits above 0.6: {[h.get('key') for h in eligible_hits]}")

            # Use top eligible hit for response construction
            top_hit = eligible_hits[0]
            key = top_hit.get('key', '')
            value = top_hit.get('value', '')

            # Build response content referencing memory
            content = f"Based on your stored information, {key} is '{value}'."

            # Calculate average confidence across eligible hits
            avg_score = sum(h["score"] for h in eligible_hits) / len(eligible_hits)

            # Attach all eligible hits as memory_provenance for Memory Results panel
            # Convert hits to proper provenance format
            memory_provenance = []
            for hit in eligible_hits:
                provenance_item = {
                    "type": "semantic",
                    "key": hit.get("key", ""),
                    "value": hit.get("value", ""),
                    "score": hit.get("score", 0.0),
                    "source": "vector_search",
                    "explanation": f"Semantic match for query '{search_query}'"
                }
                memory_provenance.append(provenance_item)

            print(f"DEBUG: Returning semantic memory response with {len(memory_provenance)} provenance items")

            return {
                "content": content,
                "memory_provenance": memory_provenance,
                "confidence": min(0.9, avg_score),  # Cap at 0.9 for semantic
                "semantic_hit": True,
            }

        except Exception as e:
            # Log error but don't crash - semantic search is optional feature
            print(f"DEBUG: Semantic memory query failed: {e}")
            import traceback
            print(f"DEBUG: Semantic query traceback: {traceback.format_exc()}")
            dao.add_event(
                user_id="system",
                actor="orchestrator_warning",
                action="semantic_query_failed",
                payload=json.dumps({"error": str(e), "query": message[:100]})
            )

        return None

    def _extract_memory_search_terms(self, message: str) -> str:
        """
        Extract cleaner search terms from memory retrieval queries.

        Handles patterns like:
        - "Retrieve anything about Python from memory"
        - "Search memory for 'primary teaching language'"
        - "What can you tell me about Python?"
        """
        message_lower = message.lower().strip()

        # Patterns for memory retrieval queries
        memory_patterns = [
            # "Retrieve anything about X from memory"
            r"retrieve\s+(?:anything\s+)?about\s+(.+?)\s+from\s+memory",
            # "Search memory for X"
            r"search\s+memory\s+(?:for\s+)?(.+)",
            # "What can you tell me about X"
            r"what\s+can\s+you\s+tell\s+me\s+about\s+(.+)\??",
            # "Anything about X in memory"
            r"(?:anything|something)\s+about\s+(.+?)\s+in\s+memory",
            # "Find X in memory" or "Look up X"
            r"(?:find|look\s+up|tell\s+me\s+about)\s+(.+)",
        ]

        for pattern in memory_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                # Clean up extracted term
                extracted = re.sub(r"^(?:my\s+|\s*the\s+)", "", extracted)  # Remove "my " or "the " prefix
                extracted = re.sub(r"[,;:!?.]+$", "", extracted)  # Remove trailing punctuation
                if extracted and len(extracted) > 2:  # Must be substantive
                    return extracted

        # If no specific pattern matched, try to extract key nouns/topics
        # Simple heuristic: look for proper nouns, programming terms, etc.
        words = re.findall(r'\b\w+\b', message_lower)
        topics = []

        # Keywords that suggest memory topics
        topic_indicators = {"python", "javascript", "programming", "language", "hobby", "interest", "favorite"}
        special_topics = set()

        for word in words:
            if word in topic_indicators or len(word) > 6:  # Longer words likely specific
                special_topics.add(word)

        if special_topics:
            return " ".join(list(special_topics)[:3])  # Take up to 3 topics

        return ""  # Return empty to use full message

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


def check_orchestrator_agents_status(orchestrator_instance):
    """Emergency diagnostic: Check if agents were created successfully"""
    try:
        agent_count = len(orchestrator_instance.agents) if orchestrator_instance.agents else 0
        agent_names = [a.agent_id for a in orchestrator_instance.agents] if orchestrator_instance.agents else []
        return f"{agent_count} agents: {agent_names}"
    except Exception as e:
        return f"ERROR checking agents: {e}"
