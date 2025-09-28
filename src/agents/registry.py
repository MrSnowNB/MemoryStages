"""
Stage 7 MVP - Agent Registry
Manages agent swarm lifecycle and provides agent discovery/services.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from .agent import BaseAgent
from .ollama_agent import OllamaAgent
from .mock_agent import MockAgent
from ..core import config
from ..core import dao


class AgentRegistry:
    """
    Registry for managing agent swarm.
    Handles agent lifecycle, discovery, and orchestration coordination.
    """

    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_creation_log: List[Dict[str, Any]] = []

    def create_ollama_agent(self, agent_id: str, model_name: Optional[str] = None,
                           role_context: Optional[str] = None) -> BaseAgent:
        """
        Create and register a new Ollama agent.

        Args:
            agent_id: Unique identifier for the agent
            model_name: Ollama model to use (defaults to config.OLLAMA_MODEL)
            role_context: System prompt/context for the agent

        Returns:
            OllamaAgent instance
        """
        if agent_id in self.agents:
            raise ValueError(f"Agent with ID '{agent_id}' already exists")

        # Use defaults from config
        model_name = model_name or config.OLLAMA_MODEL
        role_context = role_context or f"You are Agent {agent_id}, part of a collaborative AI swarm."

        # Validate agent ID format (simple MVP rules)
        if not agent_id.replace('_', '').replace('-', '').isalnum():
            raise ValueError(f"Agent ID '{agent_id}' contains invalid characters")

        # Create the agent
        agent = OllamaAgent(
            agent_id=agent_id,
            model_name=model_name,
            role_context=role_context
        )

        # Register the agent
        self.agents[agent_id] = agent

        # Log creation
        creation_info = {
            'timestamp': datetime.now().isoformat(),
            'agent_id': agent_id,
            'agent_type': 'OllamaAgent',
            'model_name': model_name,
            'role_context_length': len(role_context)
        }
        self.agent_creation_log.append(creation_info)

        # Audit log the agent creation
        dao.add_event(
            user_id="system",
            actor="agent_registry",
            action="agent_created",
            payload=json.dumps({
                'agent_id': agent_id,
                'model': model_name,
                'swarm_size': len(self.agents)
            })
        )

        return agent

    def create_mock_agent(self, agent_id: str, model_name: Optional[str] = None,
                         role_context: Optional[str] = None) -> BaseAgent:
        """
        Create and register a new mock agent for testing/development.

        Args:
            agent_id: Unique identifier for the agent
            model_name: Model name to report (defaults to config)
            role_context: System prompt/context for the agent

        Returns:
            MockAgent instance
        """
        if agent_id in self.agents:
            raise ValueError(f"Agent with ID '{agent_id}' already exists")

        # Use defaults from config
        model_name = model_name or "mock-model"
        role_context = role_context or f"You are Mock Agent {agent_id}, simulating AI behavior for testing."

        # Create the mock agent (always succeeds)
        agent = MockAgent(
            agent_id=agent_id,
            model_name=model_name,
            role_context=role_context
        )

        # Register the agent
        self.agents[agent_id] = agent

        # Log creation
        creation_info = {
            'timestamp': datetime.now().isoformat(),
            'agent_id': agent_id,
            'agent_type': 'MockAgent',
            'model_name': model_name,
            'activated': True  # Mock agents are always activated
        }
        self.agent_creation_log.append(creation_info)

        # Audit log the agent creation
        dao.add_event(
            user_id="system",
            actor="agent_registry",
            action="mock_agent_created",
            payload=json.dumps({
                'agent_id': agent_id,
                'model': model_name,
                'swarm_size': len(self.agents),
                'development_mode': True
            })
        )

        return agent

    def create_agent_by_priority(self, agent_id: str, model_name: Optional[str] = None,
                                role_context: Optional[str] = None) -> BaseAgent:
        """
        Create an agent using priority-based fallback strategy.
        Always creates an agent, falling back to mock when needed.

        Priority Order:
        1. OllamaAgent (if Ollama available and SWARM_FORCE_MOCK=false)
        2. MockAgent (for development/testing or when Ollama unavailable)

        Args:
            agent_id: Unique identifier for the agent
            model_name: Model name for the agent
            role_context: System prompt/context for the agent

        Returns:
            Agent instance (OllamaAgent or MockAgent)
        """
        from .ollama_agent import check_ollama_health

        # Check if we should force mock agents
        if config.SWARM_FORCE_MOCK:
            print(f"DEBUG: Creating mock agent {agent_id} (SWARM_FORCE_MOCK=True)")
            return self.create_mock_agent(agent_id, model_name, role_context)

        # Check if Ollama is available
        ollama_available = check_ollama_health()

        if ollama_available:
            try:
                print(f"DEBUG: Creating Ollama agent {agent_id} (Ollama available)")
                return self.create_ollama_agent(agent_id, model_name, role_context)
            except Exception as e:
                print(f"DEBUG: Failed to create Ollama agent {agent_id}, falling back to mock: {e}")
                # Fall back to mock if Ollama agent creation fails
                return self.create_mock_agent(agent_id, model_name, role_context)
        else:
            print(f"DEBUG: Creating mock agent {agent_id} (Ollama not available)")
            return self.create_mock_agent(agent_id, model_name, role_context)

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """
        Retrieve an agent by ID.

        Args:
            agent_id: ID of the agent to retrieve

        Returns:
            Agent instance or None if not found
        """
        return self.agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        """
        List all registered agents with their status info.

        Returns:
            List of agent status dictionaries
        """
        agent_list = []
        for agent_id, agent in self.agents.items():
            try:
                status = agent.get_status()
                agent_list.append(status)
            except Exception as e:
                # Include error status for broken agents
                agent_list.append({
                    'agent_id': agent_id,
                    'model_name': getattr(agent, 'model_name', 'unknown'),
                    'agent_type': type(agent).__name__,
                    'status': 'error',
                    'error': str(e)
                })

        return agent_list

    def remove_agent(self, agent_id: str) -> bool:
        """
        Remove an agent from the registry.

        Args:
            agent_id: ID of agent to remove

        Returns:
            True if removed, False if not found
        """
        if agent_id in self.agents:
            del self.agents[agent_id]

            # Audit log the removal
            dao.add_event(
                user_id="system",
                actor="agent_registry",
                action="agent_removed",
                payload=json.dumps({
                    'agent_id': agent_id,
                    'remaining_swarm_size': len(self.agents)
                })
            )

            return True
        return False

    def get_swarm_health(self) -> Dict[str, Any]:
        """
        Get overall health status of the agent swarm.

        Returns:
            Dictionary with swarm health metrics
        """
        total_agents = len(self.agents)
        healthy_agents = 0
        errors = []

        for agent_id, agent in self.agents.items():
            try:
                status = agent.get_status()
                if status.get('status') == 'ready':
                    healthy_agents += 1
            except Exception as e:
                errors.append({
                    'agent_id': agent_id,
                    'error': str(e)
                })

        health_status = "healthy" if errors else "warning" if healthy_agents < total_agents else "healthy"

        # Check global Ollama health
        from .ollama_agent import check_ollama_health
        ollama_healthy = check_ollama_health()

        return {
            'total_agents': total_agents,
            'healthy_agents': healthy_agents,
            'health_status': health_status,
            'ollama_service_healthy': ollama_healthy,
            'errors': errors,
            'timestamp': datetime.now().isoformat(),
            'model_uniformity': self._check_model_uniformity()
        }

    def _check_model_uniformity(self) -> Dict[str, Any]:
        """
        Check if all agents are using the same model as configured.

        Returns:
            Dictionary with model uniformity information
        """
        if not self.agents:
            return {'uniform': True, 'models_used': []}

        models_used = set()
        for agent in self.agents.values():
            models_used.add(getattr(agent, 'model_name', 'unknown'))

        expected_model = config.OLLAMA_MODEL
        uniform = len(models_used) == 1 and expected_model in models_used

        return {
            'uniform': uniform,
            'expected_model': expected_model,
            'models_used': list(models_used),
            'mismatched_agents': len(models_used) - (1 if uniform else 0)
        }

    def initialize_swarm(self, agent_count: Optional[int] = None,
                        model_name: Optional[str] = None) -> List[str]:
        """
        Initialize a complete agent swarm with Bots Always Activated logic.

        This method ALWAYS creates agents (unlike the old logic).
        Uses smart agent factory that falls back to mocks when needed.

        Args:
            agent_count: Number of agents to create (defaults to config)
            model_name: Model for all agents (defaults to config)

        Returns:
            List of created agent IDs (guaranteed to be non-empty in development)
        """
        agent_count = agent_count or config.SWARM_AGENT_COUNT
        model_name = model_name or config.OLLAMA_MODEL

        created_agents = []

        print(f"DEBUG: Initializing swarm with {agent_count} agents (always activated mode)")

        # Clear existing swarm if reinitializing
        if self.agents:
            for agent_id in list(self.agents.keys()):
                self.remove_agent(agent_id)

        # Create new swarm - ALWAYS SUCCEEDS due to fallback logic
        for i in range(agent_count):
            agent_id = f"swarm_agent_{i+1}"
            try:
                # Use smart factory that ALWAYS creates an agent
                agent = self.create_agent_by_priority(
                    agent_id=agent_id,
                    model_name=model_name,
                    role_context=f"You are Agent {i+1} in a swarm of {agent_count} collaborative AI assistants. Work together to provide helpful, accurate responses."
                )
                created_agents.append(agent_id)
                print(f"DEBUG: Created agent {agent_id} ({type(agent).__name__})")
            except Exception as e:
                # This should never happen with the new design, but log if it does
                print(f"ERROR: Failed to create agent {agent_id}: {e}")
                dao.add_event(
                    user_id="system",
                    actor="agent_registry",
                    action="swarm_initialization_critical_error",
                    payload=json.dumps({
                        'agent_id': agent_id,
                        'error': str(e),
                        'unexpected_failure': True
                    })
                )

        # Verify we created agents (should always be true)
        if not created_agents:
            print("CRITICAL: No agents created - this should never happen!")
            # Emergency fallback - create single mock agent
            fallback_agent_id = "emergency_mock_agent_1"
            try:
                self.create_mock_agent(fallback_agent_id, model_name, "Emergency fallback agent.")
                created_agents = [fallback_agent_id]
                print(f"EMERGENCY: Created fallback mock agent {fallback_agent_id}")
            except Exception as e:
                print(f"CRITICAL: Even emergency agent creation failed: {e}")

        # Log successful swarm initialization
        agent_types = []
        for agent_id in created_agents:
            agent = self.get_agent(agent_id)
            agent_types.append(type(agent).__name__ if agent else "Unknown")

        dao.add_event(
            user_id="system",
            actor="agent_registry",
            action="swarm_initialized_always_activated",
            payload=json.dumps({
                'agent_count': len(created_agents),
                'model': model_name,
                'agent_types': agent_types,
                'activated_bots': len(created_agents),
                'success_rate': len(created_agents) / agent_count,
                'development_mode': config.DEVELOPMENT_MODE
            })
        )

        print(f"DEBUG: Swarm initialization complete - {len(created_agents)} activated bots")

        return created_agents

    def shutdown_swarm(self) -> int:
        """
        Shutdown entire agent swarm.

        Returns:
            Number of agents successfully removed
        """
        removed_count = 0
        for agent_id in list(self.agents.keys()):
            if self.remove_agent(agent_id):
                removed_count += 1

        dao.add_event(
            user_id="system",
            actor="agent_registry",
            action="swarm_shutdown",
            payload=json.dumps({'removed_agents': removed_count})
        )

        return removed_count
