"""
Stage 7 MVP - Mock Agent Implementation
Mock agent that simulates bot behavior without external dependencies.
Used for testing, development, and graceful degradation.
"""

import random
from typing import List, Dict, Any, Optional
from datetime import datetime
from .agent import BaseAgent, AgentMessage, AgentResponse
from ..core.config import RESPONSE_VALIDATION_STRICT

class MockAgent(BaseAgent):
    """
    Mock agent that provides realistic bot-like responses without external dependencies.
    Used for testing, development, and when Ollama is unavailable.
    """

    # Pre-defined response patterns for different types of queries
    RESPONSE_PATTERNS = {
        "greeting": [
            "Hello! I'm here to help with your questions.",
            "Hi there! How can I assist you today?",
            "Greetings! I'm a mock AI assistant ready to help."
        ],
        "general": [
            "That's an interesting point. Let me think about that for a moment.",
            "I understand your question. Here's my perspective as an AI assistant.",
            "That's a good question. From what I know, the answer involves considering several factors."
        ],
        "factual": [
            "Based on general knowledge, I can tell you that this topic involves important considerations.",
            "From my training data, I know this is an area that requires careful analysis.",
            "Historically speaking, this has been a subject of much discussion and research."
        ],
        "memory_answer": [
            "I remember that information being stored in our conversation memory.",
            "That detail was saved in our previous interaction.",
            "Yes, I have that stored from when you mentioned it earlier."
        ],
        "error": [
            "I apologize, but I'm running in simulation mode and have limited capabilities right now.",
            "I'm currently operating in offline mode, so my responses may be limited.",
            "Please note that I'm functioning in mock mode and can't access external services."
        ]
    }

    def __init__(self, agent_id: str, model_name: str = "mock-model", role_context: str = "You are a helpful mock AI assistant."):
        super().__init__(agent_id, model_name)
        self.role_context = role_context
        self.is_activated = True  # Mock agents are always "activated" for testing

    def process_message(self, message: AgentMessage, context: List[AgentMessage]) -> AgentResponse:
        """
        Process a user message with realistic mock responses.

        Args:
            message: Current user message
            context: Previous conversation context

        Returns:
            AgentResponse with mock-generated content
        """
        start_time = datetime.now()

        # Analyze input to choose appropriate response pattern
        response_content = self._generate_mock_response(message.content)

        # Simulate realistic processing time (50-200ms)
        processing_time = random.randint(50, 200)
        confidence = random.uniform(0.6, 0.9)  # Mock agents show moderate confidence

        # Create response
        response = AgentResponse(
            content=response_content,
            model_used=self.model_name,
            confidence=confidence,
            tool_calls=[],
            processing_time_ms=processing_time,
            metadata={
                'agent_type': 'mock',
                'agent_id': self.agent_id,
                'activated': self.is_activated,
                'role_context': self.role_context,
                'response_type': self._classify_request(message.content)
            },
            audit_info={
                'timestamp': datetime.now().isoformat(),
                'message_length': len(message.content),
                'context_messages': len(context),
                'response_length': len(response_content),
                'mock_agent': True
            }
        )

        return response

    def _generate_mock_response(self, content: str) -> str:
        """Generate a mock response based on input analysis."""
        content_lower = content.lower()

        # Check for memory-related queries
        if any(phrase in content_lower for phrase in ['displayName', 'display name', 'name', 'what is my']):
            return self._get_random_response('memory_answer')

        # Check for factual or specific questions
        if any(word in content_lower for word in ['what is', 'how does', 'why does', 'explain']):
            return self._get_random_response('factual')

        # Check for greetings
        if any(word in content_lower for word in ['hello', 'hi', 'hey', 'greetings']):
            return self._get_random_response('greeting')

        # Check for error-prone or complex queries
        if len(content.split()) > 20 or any(char in content for char in ['?', '!', 'code']):
            return self._get_random_response('error') + " For complex queries, you'll need a fully operational AI model."

        # Default to general response
        return self._get_random_response('general')

    def _get_random_response(self, category: str) -> str:
        """Get a random response from the specified category."""
        if category not in self.RESPONSE_PATTERNS:
            return self.RESPONSE_PATTERNS['general'][0]

        return random.choice(self.RESPONSE_PATTERNS[category])

    def _classify_request(self, content: str) -> str:
        """Classify the request type for mock response generation."""
        content_lower = content.lower()

        if any(phrase in content_lower for phrase in ['displayName', 'display name', 'name']):
            return 'memory_query'
        elif any(word in content_lower for word in ['hello', 'hi', 'hey']):
            return 'greeting'
        elif any(word in content_lower for word in ['what is', 'how does', 'why']):
            return 'factual'
        else:
            return 'general'

    def get_status(self) -> Dict[str, Any]:
        """Get status with mock agent specifics."""
        status = super().get_status()
        status.update({
            'agent_type': 'mock',
            'role_context': self.role_context,
            'activated': self.is_activated,
            'capabilities': ['text_responses', 'memory_simulation', 'classification'],
            'confidence_range': '0.60-0.90',
            'response_types': list(self.RESPONSE_PATTERNS.keys())
        })
        return status

    def simulate_activation_toggle(self, active: bool) -> bool:
        """
        Simulate activation/deactivation for testing.
        Mock agents can always be in either state.
        """
        self.is_activated = active
        return True

def create_mock_swarm(count: int, model_name: str = "mock-model") -> List[MockAgent]:
    """
    Create a swarm of mock agents for testing/developent.

    Args:
        count: Number of agents to create
        model_name: Model name to report

    Returns:
        List of configured MockAgent instances
    """
    agents = []
    for i in range(count):
        agent_id = f"mock_agent_{i+1}"
        agent = MockAgent(
            agent_id=agent_id,
            model_name=model_name,
            role_context=f"You are Mock Agent {i+1}, simulating AI behavior in a collaborative swarm."
        )
        agents.append(agent)

    return agents
