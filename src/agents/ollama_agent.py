"""
Stage 7 MVP - Ollama Agent Implementation
Ollama-based agent that interacts with local Ollama models.
"""

import ollama
from typing import List, Dict, Any, Optional
from datetime import datetime
from .agent import BaseAgent, AgentMessage, AgentResponse
from ..core import dao


class OllamaAgent(BaseAgent):
    """
    Agent implementation that uses Ollama models.
    Provides simple integration with local Ollama instance.
    """

    def __init__(self, agent_id: str, model_name: str, role_context: str = "You are a helpful assistant."):
        super().__init__(agent_id, model_name)
        self.role_context = role_context

    def process_message(self, message: AgentMessage, context: List[AgentMessage]) -> AgentResponse:
        """
        Process a user message using Ollama API.

        Args:
            message: Current user message
            context: Previous conversation context

        Returns:
            AgentResponse with Ollama model output
        """
        try:
            # Build messages array for Ollama
            messages = self._build_ollama_messages(message, context)

            # Track processing time
            start_time = datetime.now()

            # Make Ollama API call
            response = ollama.chat(
                model=self.model_name,
                messages=messages,
                options={
                    'temperature': 0.7,  # Reasonable creativity for MVP
                    'top_p': 0.9
                }
            )

            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Extract response content
            response_content = response.get('message', {}).get('content', '')

            if not response_content:
                # Handle empty response
                response_content = "I didn't receive a clear response. Could you please rephrase your question?"

            # Create agent response
            agent_response = AgentResponse(
                content=response_content,
                model_used=self.model_name,
                confidence=self._calculate_confidence(response_content),
                tool_calls=[],  # No tool calls in MVP
                processing_time_ms=processing_time,
                metadata={
                    'agent_type': 'ollama',
                    'agent_id': self.agent_id,
                    'role_context': self.role_context,
                    'ollama_response': response
                },
                audit_info={
                    'timestamp': datetime.now().isoformat(),
                    'message_length': len(message.content),
                    'context_messages': len(context),
                    'response_length': len(response_content),
                    'ollama_model': self.model_name
                }
            )

            # Log agent activity (except in high-volume scenarios)
            if len(context) <= 5:  # Only log shorter conversations to avoid spam
                user_id = message.metadata.get('user_id', 'default') if message.metadata else 'default'
                dao.add_event(
                    user_id=user_id,
                    actor=f"agent_{self.agent_id}",
                    action="message_processed",
                    payload={
                        'model': self.model_name,
                        'processing_time_ms': processing_time,
                        'confidence': agent_response.confidence,
                        'response_length': len(response_content)
                    }
                )

            return agent_response

        except ollama.ResponseError as e:
            # Handle Ollama-specific errors
            error_msg = f"Ollama model error: {str(e)}"
            return self._create_error_response(error_msg, message)

        except Exception as e:
            # Handle general errors
            error_msg = f"I apologize, but I encountered an error: {str(e)}"
            return self._create_error_response(error_msg, message)

    def _build_ollama_messages(self, message: AgentMessage, context: List[AgentMessage]) -> List[Dict[str, str]]:
        """
        Build messages array in Ollama format.
        Includes system context and conversation history.
        """
        messages = []

        # Add system message with role context
        if self.role_context:
            messages.append({
                'role': 'system',
                'content': self.role_context
            })

        # Add conversation context (limit to recent messages)
        recent_context = context[-3:] if len(context) > 3 else context  # Limit context for MVP

        for ctx_msg in recent_context:
            messages.append({
                'role': ctx_msg.role,
                'content': ctx_msg.content
            })

        # Add current message
        messages.append({
            'role': message.role,
            'content': message.content
        })

        return messages

    def _calculate_confidence(self, response_content: str) -> float:
        """
        Simple confidence heuristic based on response characteristics.
        Higher scores for longer, more informative responses.
        """
        if not response_content:
            return 0.0

        confidence = 0.5  # Base confidence

        # Longer responses generally indicate more confident answers
        length_score = min(len(response_content) / 500, 0.3)  # Max 0.3 for length
        confidence += length_score

        # Responses with specific details score higher
        if any(keyword in response_content.lower() for keyword in ['because', 'therefore', 'specifically', 'according to']):
            confidence += 0.1

        # Capped at 0.9 for MVP
        return min(confidence, 0.9)

    def _create_error_response(self, error_msg: str, original_message: AgentMessage) -> AgentResponse:
        """Create consistent error response format."""
        return AgentResponse(
            content=error_msg,
            model_used=self.model_name,
            confidence=0.0,
            tool_calls=[],
            processing_time_ms=0,
            metadata={
                'agent_type': 'ollama',
                'agent_id': self.agent_id,
                'error_occurred': True
            },
            audit_info={
                'timestamp': datetime.now().isoformat(),
                'error': error_msg,
                'message_length': len(original_message.content)
            }
        )

    def get_status(self) -> Dict[str, Any]:
        """Get current status with Ollama-specific information."""
        status = super().get_status()
        status.update({
            'role_context': self.role_context,
            'ollama_available': self._check_ollama_health()
        })
        return status

    def _check_ollama_health(self) -> bool:
        """Check if Ollama is available and model is accessible."""
        try:
            # Quick model list check
            models = ollama.list()
            model_names = [model['name'] for model in models.get('models', [])]
            return self.model_name in model_names
        except Exception:
            return False


def check_ollama_health() -> bool:
    """
    Global function to check Ollama service health.
    Used by orchestrator and API endpoints.
    """
    try:
        # Test basic Ollama connectivity
        ollama.list()
        return True
    except Exception:
        return False
