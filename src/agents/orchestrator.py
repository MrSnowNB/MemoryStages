"""
Stage 3: Bot Swarm Orchestration - Main Orchestrator Service
Coordinates multi-agent swarm execution with planning, tool use, and safety validation.

This is the main entry point for Stage 3 swarm orchestration. The OrchestratorService:

1. Receives chat requests and coordinates agent execution
2. Delegates planning to Manager agent
3. Routes tool calls through ToolRouter
4. Applies memory retrieval and reconciliation via MemoryAgent
5. Synthesizes final responses through Reasoner
6. Validates all outputs through SafetyAgent
7. Emits comprehensive episodic events for audit trail
"""

import asyncio
import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from ..core.config import SWARM_ENABLED, CHAT_API_ENABLED
from ..core.dao import add_event
from ..agents.manager import PlanningAgent
from ..agents.memory_agent import MemoryAgent
from ..agents.reasoner import ReasonerAgent
from ..agents.safety import SafetyAgent
from ..agents.tools import ToolRouter
from ..core.working_memory import WorkingMemory
from .agent import AgentResponse
from ..api.schemas import SwarmMessageRequest, SwarmMessageResponse, SwarmTimelineEvent


class OrchestratorService:
    """
    Main orchestrator for multi-agent swarm operations.
    Coordinates planning → execution → synthesis → validation flow.
    """

    def __init__(self):
        """Initialize the orchestrator with all agents and infrastructure."""
        self.planning_agent = PlanningAgent()
        self.memory_agent = MemoryAgent()
        self.reasoner = ReasonerAgent()
        self.safety_agent = SafetyAgent()
        self.tools = ToolRouter()
        self.working_memory = WorkingMemory()

        # Track current conversation state
        self.current_conversation_id = None
        self.current_turn_id = None

        # Swarm configuration
        self.max_tool_calls = 5  # Prevent infinite loops
        self.max_iterations = 3  # Reasoning depth limit

        print("🧠 Orchestrator initialized with 4 agents: Planning, Memory, Reasoner, Safety")
        print("🛠️  ToolRouter ready with semantic.query, kv.get/set capabilities")

    async def process_message(self, request: SwarmMessageRequest) -> SwarmMessageResponse:
        """
        Execute full swarm orchestration workflow for a chat message.

        Args:
            request: Chat message with content, user_id, conversation context

        Returns:
            Swarm response with answer, provenance, and execution timeline
        """
        if not SWARM_ENABLED:
            return self._fallback_response("Swarm mode disabled")

        # Initialize conversation tracking
        self.current_conversation_id = getattr(request, 'conversation_id', str(uuid.uuid4()))
        self.current_turn_id = str(uuid.uuid4())

        # Initialize working memory for this turn
        self.working_memory.clear()
        self.working_memory.set("conversation_id", self.current_conversation_id)
        self.working_memory.set("turn_id", self.current_turn_id)
        self.working_memory.set("user_query", request.content)
        self.working_memory.set("user_id", getattr(request, 'user_id', 'default'))

        timeline = []
        start_time = datetime.now()

        try:
            # Step 1: Safety pre-check
            timeline.append(await self._create_timeline_event("safety_precheck", "Pre-validating user input"))
            safety_result = await self.safety_agent.validate_input(request.content)
            if not safety_result.allowed:
                return self._build_response(
                    content=safety_result.safe_response or "I cannot respond to this request due to safety guidelines.",
                    provenance={"blocked": True, "reason": safety_result.reason},
                    timeline=timeline,
                    safety_blocked=True
                )

            # Step 2: Planning phase
            timeline.append(await self._create_timeline_event("planning", "Creating execution plan"))
            plan = await self.planning_agent.create_plan(request.content)
            self.working_memory.set("plan", plan)
            timeline.append(await self._create_timeline_event("plan_complete", f"Plan created: {plan.steps[:1]}..."))

            # Step 3: Tool execution phase
            tool_results = []
            for step in plan.steps:
                if len(tool_results) >= self.max_tool_calls:
                    break

                result = await self._execute_tool_step(step, timeline)
                if result:
                    tool_results.append(result)

            # Step 4: Memory reconciliation
            timeline.append(await self._create_timeline_event("reconciliation", "Reconciling KV and semantic memory"))
            memory_facts = await self.memory_agent.reconcile_memories(
                query=request.content,
                tool_results=tool_results
            )
            self.working_memory.set("memory_facts", memory_facts)

            # Step 5: Response synthesis
            timeline.append(await self._create_timeline_event("synthesis", "Synthesizing final response"))
            synthesis_input = {
                "original_query": request.content,
                "plan": plan,
                "tool_results": tool_results,
                "memory_facts": memory_facts,
                "working_memory": self.working_memory.get_all()
            }
            answer = await self.reasoner.synthesize_response(synthesis_input)

            # Step 6: Safety post-validation
            timeline.append(await self._create_timeline_event("safety_postcheck", "Post-validating generated response"))
            final_safety = await self.safety_agent.validate_output(answer.content, context=answer.provenance)
            if not final_safety.allowed:
                answer.content = final_safety.safe_response or "Response blocked due to safety guidelines."
                answer.provenance["blocked"] = True

            # Step 7: Final audit logging
            await self._log_final_response(answer, timeline, start_time)

            return self._build_response(
                content=answer.content,
                provenance=answer.provenance,
                timeline=timeline,
                memory_facts=memory_facts
            )

        except Exception as e:
            # Emergency error handling
            error_msg = f"Swarm orchestration failed: {str(e)}"
            timeline.append(await self._create_timeline_event("error", error_msg))
            await self._log_error_event(error_msg)

            return self._build_response(
                content="I encountered an error processing your request. Please try again.",
                provenance={"error": str(e)},
                timeline=timeline
            )

    async def _execute_tool_step(self, step: Dict[str, Any], timeline: List[SwarmTimelineEvent]) -> Optional[Dict[str, Any]]:
        """Execute a single tool step from the plan."""
        try:
            tool_name = step.get("tool", "")
            tool_params = step.get("parameters", {})
            description = step.get("description", f"Calling {tool_name}")

            timeline.append(await self._create_timeline_event("tool_call", description))

            # Route through ToolRouter
            result = await self.tools.call_tool(
                name=tool_name,
                parameters=tool_params,
                conversation_id=self.current_conversation_id,
                turn_id=self.current_turn_id
            )

            # Store result in working memory
            result_key = f"tool_result_{len(self.working_memory.get('tool_results', []))}"
            self.working_memory.set(result_key, result)

            timeline.append(await self._create_timeline_event("tool_result",
                f"{tool_name} returned {len(result.get('data', []))} items"))

            await self._log_tool_event(tool_name, tool_params, result)

            return result

        except Exception as e:
            timeline.append(await self._create_timeline_event("tool_error", f"Tool call failed: {str(e)}"))
            await self._log_error_event(f"Tool execution error: {str(e)}")
            return None

    async def _create_timeline_event(self, event_type: str, description: str) -> SwarmTimelineEvent:
        """Create a timeline event for UI display."""
        return SwarmTimelineEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            description=description,
            duration_ms=0  # Could be enhanced with timing
        )

    def _build_response(self, content: str, provenance: Dict[str, Any], timeline: List[SwarmTimelineEvent],
                       memory_facts: Optional[List[Dict[str, Any]]] = None, safety_blocked: bool = False) -> SwarmMessageResponse:
        """Build structured swarm response."""
        return SwarmMessageResponse(
            message_id=str(uuid.uuid4()),
            content=content,
            provenance=provenance,
            timeline=timeline,
            memory_facts=memory_facts or [],
            safety_blocked=safety_blocked,
            conversation_id=self.current_conversation_id,
            turn_id=self.current_turn_id,
            model_used="swarm-orchestrator",
            processing_time_ms=0  # Could calculate actual time
        )

    def _fallback_response(self, reason: str) -> SwarmMessageResponse:
        """Fallback response when swarm is disabled or unavailable."""
        return SwarmMessageResponse(
            message_id=str(uuid.uuid4()),
            content="Swarm orchestration is currently unavailable.",
            provenance={"fallback": True, "reason": reason},
            timeline=[],
            memory_facts=[],
            safety_blocked=False,
            conversation_id=None,
            turn_id=None,
            model_used="fallback",
            processing_time_ms=0
        )

    # Event logging methods (implement episodic logging)
    async def _log_final_response(self, answer: Any, timeline: List[SwarmTimelineEvent], start_time: datetime):
        """Log final response to shadow ledger."""
        import json
        await add_event(
            user_id=self.working_memory.get("user_id", "unknown"),
            actor="orchestrator",
            action="swarm_response_complete",
            payload=json.dumps({
                "conversation_id": self.current_conversation_id,
                "turn_id": self.current_turn_id,
                "query": self.working_memory.get("user_query"),
                "answer": answer.content[:500],  # Truncate for storage
                "provenance": answer.provenance,
                "timeline_length": len(timeline),
                "processing_time": (datetime.now() - start_time).total_seconds()
            }),
            session_id=self.current_conversation_id,
            event_type="finalize_response",
            message=f"Swarm response: {answer.content[:100]}..."
        )

    async def _log_tool_event(self, tool_name: str, params: Dict[str, Any], result: Dict[str, Any]):
        """Log tool execution to shadow ledger."""
        import json
        await add_event(
            user_id=self.working_memory.get("user_id", "unknown"),
            actor="orchestrator",
            action=f"tool_call_{tool_name}",
            payload=json.dumps({
                "tool": tool_name,
                "parameters": params,
                "result_count": len(result.get("data", [])),
                "conversation_id": self.current_conversation_id,
                "turn_id": self.current_turn_id
            }),
            session_id=self.current_conversation_id,
            event_type="tool_result",
            message=f"Tool {tool_name} executed successfully"
        )

    async def _log_error_event(self, error_msg: str):
        """Log errors to shadow ledger."""
        import json
        await add_event(
            user_id=self.working_memory.get("user_id", "unknown"),
            actor="orchestrator",
            action="swarm_error",
            payload=json.dumps({
                "error": error_msg,
                "conversation_id": self.current_conversation_id,
                "turn_id": self.current_turn_id
            }),
            session_id=self.current_conversation_id,
            event_type="error",
            message=f"Swarm error: {error_msg[:100]}..."
        )

    # Health check method
    async def health_check(self) -> Dict[str, Any]:
        """Check health of orchestrator and all agents."""
        health = {
            "orchestrator": "healthy",
            "agents": {},
            "tools": {}
        }

        # Check each agent
        try:
            health["agents"]["planning"] = "healthy" if await self.planning_agent.health_check() else "unhealthy"
        except:
            health["agents"]["planning"] = "unhealthy"

        try:
            health["agents"]["memory"] = "healthy" if await self.memory_agent.health_check() else "unhealthy"
        except:
            health["agents"]["memory"] = "unhealthy"

        try:
            health["agents"]["reasoner"] = "healthy" if await self.reasoner.health_check() else "unhealthy"
        except:
            health["agents"]["reasoner"] = "unhealthy"

        try:
            health["agents"]["safety"] = "healthy" if await self.safety_agent.health_check() else "unhealthy"
        except:
            health["agents"]["safety"] = "unhealthy"

        # Overall status
        agent_health = all(status == "healthy" for status in health["agents"].values())
        health["overall"] = "healthy" if agent_health else "degraded"

        return health
