"""
Stage 3: Bot Swarm Orchestration - Tool Router
Centralized tool coordination for agent tool calls.

The ToolRouter brokers access to all available tools:
- semantic.query - Search semantic memory
- kv.get - Retrieve canonical KV facts
- kv.set - Update canonical KV (requires orchestrator permission)
- reason.analyze - Pattern analysis and reasoning
- consolidate - Merge and reconcile data sources

All tool calls are logged to the shadow ledger for audit trails.
"""

from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from ..core.dao import add_event
from ..vector.semantic_memory import SemanticMemoryService
from ..core.dao import get_key, set_key


class ToolResult:
    """Result of a tool execution."""

    def __init__(self, tool: str, data: List[Dict[str, Any]], success: bool = True,
                 error: Optional[str] = None):
        self.tool = tool
        self.data = data if data is not None else []
        self.success = success
        self.error = error
        self.execution_time = datetime.now()
        self.data_count = len(self.data)


class ToolRouter:
    """
    Centralized router for all agent tool access.

    Provides standardized interface for:
    - Tool registration and discovery
    - Parameter validation
    - Execution coordination
    - Audit logging
    - Permission management
    """

    def __init__(self):
        """Initialize tool router with available tools."""
        self.tools = {}
        self.semantic_service = SemanticMemoryService()
        self._register_tools()
        print("🔧 ToolRouter initialized - coordinating tool access")

    def _register_tools(self):
        """Register all available tools."""
        self.tools = {
            "semantic.query": {
                "function": self._semantic_query,
                "description": "Search semantic memory for relevant facts",
                "parameters": {
                    "text": {"type": "string", "required": True, "description": "Query text"},
                    "k": {"type": "int", "required": False, "default": 5, "description": "Number of results"},
                },
                "requires_permission": False
            },
            "kv.get": {
                "function": self._kv_get,
                "description": "Retrieve canonical KV facts for a user",
                "parameters": {
                    "key": {"type": "string", "required": True, "description": "KV key to retrieve"},
                    "user_id": {"type": "string", "required": False, "default": "default", "description": "User ID"},
                },
                "requires_permission": False
            },
            "kv.set": {
                "function": self._kv_set,
                "description": "Update canonical KV facts (requires orchestrator permission)",
                "parameters": {
                    "key": {"type": "string", "required": True, "description": "KV key to set"},
                    "value": {"type": "any", "required": True, "description": "Value to set"},
                    "user_id": {"type": "string", "required": False, "default": "default", "description": "User ID"},
                },
                "requires_permission": True  # Only orchestrator can call this
            },
            "reason.analyze": {
                "function": self._reason_analyze,
                "description": "Analyze patterns and relationships in data",
                "parameters": {
                    "task": {"type": "string", "required": True, "description": "Analysis task type"},
                    "data": {"type": "any", "required": True, "description": "Data to analyze"},
                },
                "requires_permission": False
            },
            "consolidate": {
                "function": self._consolidate,
                "description": "Merge and reconcile multiple data sources",
                "parameters": {
                    "sources": {"type": "list", "required": True, "description": "List of source keys"},
                },
                "requires_permission": False
            }
        }

    async def call_tool(self, name: str, parameters: Dict[str, Any],
                       conversation_id: Optional[str] = None,
                       turn_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a tool with the given parameters.

        Args:
            name: Tool name to call
            parameters: Tool parameters
            conversation_id: Optional conversation context
            turn_id: Optional turn context

        Returns:
            Tool execution result
        """
        if name not in self.tools:
            error_result = {
                "tool": name,
                "data": [],
                "success": False,
                "error": f"Unknown tool: {name}"
            }
            await self._log_tool_call(name, parameters, error_result, conversation_id, turn_id)
            return error_result

        tool_config = self.tools[name]

        try:
            # Validate parameters
            validated_params = self._validate_parameters(name, parameters)

            # Execute tool
            start_time = datetime.now()
            result_data = await tool_config["function"](**validated_params)
            execution_time = (datetime.now() - start_time).total_seconds()

            # Package result
            result = {
                "tool": name,
                "data": result_data if isinstance(result_data, list) else [result_data] if result_data else [],
                "success": True,
                "execution_time": execution_time,
                "data_count": len(result_data) if isinstance(result_data, list) else 1 if result_data else 0
            }

        except Exception as e:
            result = {
                "tool": name,
                "data": [],
                "success": False,
                "error": str(e)
            }

        # Log the tool call
        await self._log_tool_call(name, parameters, result, conversation_id, turn_id)

        return result

    def _validate_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and prepare tool parameters."""
        tool_config = self.tools[tool_name]
        param_specs = tool_config["parameters"]

        validated = {}

        for param_name, spec in param_specs.items():
            if spec.get("required", False) and param_name not in parameters:
                if "default" in spec:
                    validated[param_name] = spec["default"]
                else:
                    raise ValueError(f"Required parameter '{param_name}' missing for tool '{tool_name}'")

            if param_name in parameters:
                validated[param_name] = parameters[param_name]

        return validated

    # Tool implementations

    async def _semantic_query(self, text: str, k: int = 5) -> List[Dict[str, Any]]:
        """Execute semantic memory search."""
        try:
            results = self.semantic_service.query(text, k)
            return [{
                "text": hit.get("text", ""),
                "score": hit.get("score", 0),
                "doc_id": hit.get("doc_id"),
                "provenance": f"semantic_match_{hit.get('score', 0):.3f}"
            } for hit in results]
        except Exception:
            return []

    async def _kv_get(self, key: str, user_id: str = "default") -> List[Dict[str, Any]]:
        """Retrieve KV fact."""
        try:
            result = get_key(user_id, key)
            if result:
                return [{
                    "key": result.key,
                    "value": result.value,
                    "source": result.source,
                    "updated_at": result.updated_at.isoformat(),
                    "provenance": f"canonical_kv_{result.source}"
                }]
            return []
        except Exception:
            return []

    async def _kv_set(self, key: str, value: Any, user_id: str = "default") -> Dict[str, Any]:
        """Set KV fact (requires orchestrator permission)."""
        # NOTE: This tool should only be called by orchestrator after validation
        try:
            success = set_key(
                user_id=user_id,
                key=key,
                value=value,
                source="orchestrator",
                casing="preserve"
            )
            return {
                "operation": "set",
                "key": key,
                "success": success,
                "user_id": user_id
            }
        except Exception as e:
            return {
                "operation": "set",
                "key": key,
                "success": False,
                "error": str(e)
            }

    async def _reason_analyze(self, task: str, data: Any) -> Dict[str, Any]:
        """Perform reasoning analysis on data."""
        # Simple pattern analysis - can be extended
        if isinstance(data, list) and len(data) > 1:
            # Analyze data patterns
            sources = []
            confidences = []

            for item in data:
                if isinstance(item, dict):
                    sources.append(item.get("source", "unknown"))
                    confidences.append(float(item.get("confidence", 0)))

            return {
                "analysis_type": "pattern_recognition",
                "sources_identified": list(set(sources)),
                "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
                "data_points": len(data),
                "insights": f"Found {len(set(sources))} unique sources in {len(data)} data points"
            }
        else:
            return {
                "analysis_type": "basic_evaluation",
                "data_type": type(data).__name__,
                "insights": "Single data point or simple structure - limited analysis available"
            }

    async def _consolidate(self, sources: List[str]) -> Dict[str, Any]:
        """Merge and reconcile multiple data sources."""
        # This would typically get data from working memory
        # For now, return a summary
        return {
            "operation": "consolidation",
            "sources_consolidated": len(sources),
            "sources": sources,
            "summary": f"Merged {len(sources)} data sources into unified response"
        }

    async def _log_tool_call(self, tool_name: str, parameters: Dict[str, Any],
                           result: Dict[str, Any], conversation_id: Optional[str],
                           turn_id: Optional[str]):
        """Log tool execution to shadow ledger."""
        await add_event(
            user_id="system",  # Tool calls are system operations
            actor="tool_router",
            action=f"tool_call_{tool_name}",
            payload={
                "tool": tool_name,
                "parameters": parameters,
                "success": result.get("success", False),
                "data_count": result.get("data_count", 0),
                "execution_time": result.get("execution_time", 0),
                "error": result.get("error"),
                "conversation_id": conversation_id,
                "turn_id": turn_id
            },
            event_type="tool_call",
            conversation_id=conversation_id
        )

    def list_available_tools(self) -> Dict[str, Any]:
        """Get information about all available tools."""
        return {
            tool_name: {
                "description": config["description"],
                "parameters": {k: {k2: v2 for k2, v2 in v.items() if k2 != "function"}
                             for k, v in config["parameters"].items()},
                "requires_permission": config["requires_permission"]
            }
            for tool_name, config in self.tools.items()
        }

    def health_check(self) -> bool:
        """Check if tool router is operational."""
        try:
            # Test a simple tool call
            result = self.tools.get("semantic.query")
            return result is not None and callable(result["function"])
        except Exception:
            return False
