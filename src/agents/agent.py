"""
Stage 7 MVP - Base Agent Interface
Abstract interfaces and data classes for all agents in the swarm.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from abc import ABC, abstractmethod


@dataclass
class AgentMessage:
    """Message format for agent communication."""
    content: str
    role: str  # "user", "assistant", or "system"
    timestamp: datetime
    metadata: Dict[str, Any]
    model_used: str = ""

    def __post_init__(self):
        if not self.metadata:
            self.metadata = {}


@dataclass
class AgentResponse:
    """Response format from any agent."""
    content: str
    model_used: str
    confidence: float = 0.0
    tool_calls: List[Dict[str, Any]] = None
    processing_time_ms: int = 0
    metadata: Dict[str, Any] = None
    audit_info: Dict[str, Any] = None

    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []
        if self.metadata is None:
            self.metadata = {}
        if self.audit_info is None:
            self.audit_info = {"timestamp": datetime.now().isoformat()}


@dataclass
class ToolCall:
    """Represents a tool execution by an agent."""
    name: str
    parameters: Dict[str, Any]
    result: Optional[Any] = None


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the swarm.
    All agents must implement the process_message method.
    """

    def __init__(self, agent_id: str, model_name: str):
        self.agent_id = agent_id
        self.model_name = model_name

    @abstractmethod
    def process_message(self, message: AgentMessage, context: List[AgentMessage]) -> AgentResponse:
        """
        Process a user message with conversation context.

        Args:
            message: The current user message to process
            context: List of previous messages in the conversation

        Returns:
            AgentResponse: The agent's response to the message
        """
        pass

    def get_status(self) -> Dict[str, Any]:
        """Get current status of this agent."""
        return {
            "agent_id": self.agent_id,
            "model_name": self.model_name,
            "agent_type": self.__class__.__name__,
            "status": "ready"
        }
