"""
Stage 7 MVP - Agent Registry
Manages agent swarm lifecycle and provides agent discovery/services.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from .agent import BaseAgent
from .ollama_agent import OllamaAgent
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
            actor="agent_registry",
            action="agent_created",
            payload=json.dumps({
                'agent_id': agent_id,
                'model': model_name,
                'swarm_size': len(self.agents)
            })
        )

        return agent

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
        Initialize a complete agent swarm with default configuration.

        Args:
            agent_count: Number of agents to create (defaults to config)
            model_name: Model for all agents (defaults to config)

        Returns:
            List of created agent IDs
        """
        agent_count = agent_count or config.SWARM_AGENT_COUNT
        model_name = model_name or config.OLLAMA_MODEL

        created_agents = []

        # Clear existing swarm if reinitializing
        if self.agents:
            for agent_id in list(self.agents.keys()):
                self.remove_agent(agent_id)

        # Create new swarm
        for i in range(agent_count):
            agent_id = f"ollama_agent_{i+1}"
            try:
                agent = self.create_ollama_agent(
                    agent_id=agent_id,
                    model_name=model_name,
                    role_context=f"You are Agent {i+1} in a swarm of {agent_count} collaborative AI assistants. Work together to provide helpful, accurate responses."
                )
                created_agents.append(agent_id)
            except Exception as e:
                # Log but continue creating other agents
                dao.add_event(
                    actor="agent_registry",
                    action="swarm_initialization_error",
                    payload=json.dumps({
                        'agent_id': agent_id,
                        'error': str(e),
                        'progress': f"{len(created_agents)}/{agent_count}"
                    })
                )

        # Log successful swarm initialization
        dao.add_event(
            actor="agent_registry",
            action="swarm_initialized",
            payload=json.dumps({
                'agent_count': len(created_agents),
                'model': model_name,
                'success_rate': len(created_agents) / agent_count
            })
        )

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
            actor="agent_registry",
            action="swarm_shutdown",
            payload=json.dumps({'removed_agents': removed_count})
        )

        return removed_count
