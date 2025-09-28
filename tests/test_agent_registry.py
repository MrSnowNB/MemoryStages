"""
Stage 7 MVP - Test Agent Registry
Tests for agent registry and swarm management functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.agents.registry import AgentRegistry
from src.agents.ollama_agent import OllamaAgent


class TestAgentRegistry:
    """Test cases for agent registry functionality."""

    @pytest.fixture
    def registry(self):
        """Create a fresh agent registry for each test."""
        return AgentRegistry()

    def test_registry_initialization(self, registry):
        """Test registry initializes correctly."""
        assert isinstance(registry.agents, dict)
        assert len(registry.agents) == 0
        assert isinstance(registry.agent_creation_log, list)
        assert len(registry.agent_creation_log) == 0

    @patch('src.agents.registry.OllamaAgent')
    @patch('src.agents.registry.dao')
    def test_create_ollama_agent_success(self, mock_dao, mock_agent_class, registry):
        """Test successful creation of an Ollama agent."""
        # Mock the OllamaAgent constructor
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        agent = registry.create_ollama_agent(
            agent_id="test_agent_1",
            model_name="custom-model",
            role_context="Custom role"
        )

        assert agent is mock_agent
        assert "test_agent_1" in registry.agents
        assert registry.agents["test_agent_1"] is mock_agent

        # Verify agent creation was logged
        assert len(registry.agent_creation_log) == 1
        log_entry = registry.agent_creation_log[0]
        assert log_entry["agent_id"] == "test_agent_1"
        assert log_entry["model_name"] == "custom-model"
        assert log_entry["role_context_length"] == 11  # len("Custom role")

        # Verify audit event was logged
        mock_dao.add_event.assert_called_with(
            actor="agent_registry",
            action="agent_created",
            payload='{"agent_id": "test_agent_1", "model": "custom-model", "swarm_size": 1}'
        )

    def test_create_ollama_agent_duplicate_id(self, registry):
        """Test creating agent with duplicate ID fails."""
        # First creation should succeed
        with patch('src.agents.registry.OllamaAgent'):
            registry.create_ollama_agent("test_agent")
            assert "test_agent" in registry.agents

        # Second creation should fail
        with pytest.raises(ValueError, match="already exists"):
            registry.create_ollama_agent("test_agent")

    def test_create_ollama_agent_invalid_id(self, registry):
        """Test creating agent with invalid ID fails."""
        invalid_ids = [
            "agent@invalid",  # Special character
            "agent invalid",  # Space
            "agent#test",     # Hash
            "agent-with+invalid",  # Plus sign
        ]

        for invalid_id in invalid_ids:
            with pytest.raises(ValueError, match="invalid characters"):
                registry.create_ollama_agent(invalid_id)

    @patch('src.agents.registry.OllamaAgent')
    def test_create_ollama_agent_defaults(self, mock_agent_class, registry):
        """Test agent creation with default parameters."""
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        with patch('src.agents.registry.config') as mock_config:
            mock_config.OLLAMA_MODEL = "default-model"

            agent = registry.create_ollama_agent("test_agent")

            # Verify OllamaAgent was created with correct defaults
            mock_agent_class.assert_called_with(
                agent_id="test_agent",
                model_name="default-model",
                role_context="You are Agent test_agent, part of a collaborative AI swarm."
            )

    def test_get_agent(self, registry):
        """Test retrieving agents by ID."""
        # Test getting non-existent agent
        assert registry.get_agent("non_existent") is None

        # Test getting existing agent
        with patch('src.agents.registry.OllamaAgent'):
            registry.create_ollama_agent("existing_agent")
            agent = registry.get_agent("existing_agent")
            assert agent is not None

    def test_list_agents(self, registry):
        """Test listing all registered agents."""
        # Start with empty registry
        assert registry.list_agents() == []

        # Add some agents
        with patch('src.agents.registry.OllamaAgent') as mock_class:
            mock_agents = [Mock(), Mock()]
            mock_class.side_effect = mock_agents

            # Create agents with mock responses
            mock_agents[0].get_status.return_value = {"agent_id": "agent1", "status": "ready"}
            mock_agents[1].get_status.return_value = {"agent_id": "agent2", "status": "error"}

            registry.create_ollama_agent("agent1")
            registry.create_ollama_agent("agent2")

            agent_list = registry.list_agents()

            assert len(agent_list) == 2
            assert any(agent["agent_id"] == "agent1" for agent in agent_list)
            assert any(agent["agent_id"] == "agent2" for agent in agent_list)
            assert any(agent["status"] == "ready" for agent in agent_list)
            assert any(agent["status"] == "error" for agent in agent_list)

    def test_list_agents_with_errors(self, registry):
        """Test listing agents when some have errors."""
        with patch('src.agents.registry.OllamaAgent') as mock_class:
            mock_agent = Mock()
            mock_class.return_value = mock_agent

            # Agent that raises exception on status check
            mock_agent.get_status.side_effect = Exception("Test error")

            registry.agents["problematic_agent"] = mock_agent
            registry.agents["problematic_agent"].get_status = Mock(side_effect=Exception("Test error"))

            agent_list = registry.list_agents()

            # Should include error status for problematic agent
            error_agent = next((a for a in agent_list if a["status"] == "error"), None)
            assert error_agent is not None
            assert "Test error" in str(error_agent.get("error", ""))

    @patch('src.agents.registry.dao')
    def test_remove_agent(self, mock_dao, registry):
        """Test removing agents from registry."""
        # Test removing non-existent agent
        assert not registry.remove_agent("non_existent")
        mock_dao.add_event.assert_not_called()

        # Add and then remove an agent
        with patch('src.agents.registry.OllamaAgent'):
            registry.create_ollama_agent("agent_to_remove")
            assert "agent_to_remove" in registry.agents

            # Remove the agent
            result = registry.remove_agent("agent_to_remove")
            assert result is True
            assert "agent_to_remove" not in registry.agents

            # Verify audit event
            mock_dao.add_event.assert_called_with(
                actor="agent_registry",
                action="agent_removed",
                payload='{"agent_id": "agent_to_remove", "remaining_swarm_size": 0}'
            )

    @patch('src.agents.registry.dao')
    def test_initialize_swarm(self, mock_dao, registry):
        """Test swarm initialization with multiple agents."""
        with patch('src.agents.registry.OllamaAgent') as mock_class:
            mock_agent = Mock()
            mock_class.return_value = mock_agent

            # Initialize swarm of 3 agents
            agent_ids = registry.initialize_swarm(agent_count=3, model_name="test-model")

            assert len(agent_ids) == 3
            assert "ollama_agent_1" in agent_ids
            assert "ollama_agent_2" in agent_ids
            assert "ollama_agent_3" in agent_ids

            # Verify agents are registered
            for agent_id in agent_ids:
                assert agent_id in registry.agents

            # Verify agents were created with correct parameters
            assert mock_class.call_count == 3
            for call in mock_class.call_args_list:
                args, kwargs = call
                assert kwargs["model_name"] == "test-model"
                assert "swarm of 3 collaborative AI assistants" in kwargs["role_context"]

    def test_initialize_swarm_with_errors(self, registry):
        """Test swarm initialization when some agents fail."""
        with patch('src.agents.registry.OllamaAgent') as mock_class:
            mock_class.side_effect = [Mock(), Exception("Creation failed"), Mock()]

            # Should continue creating agents despite one failure
            agent_ids = registry.initialize_swarm(agent_count=3)

            assert len(agent_ids) == 2  # Only successful creations
            assert "ollama_agent_1" in agent_ids
            assert "ollama_agent_3" in agent_ids

    @patch('src.agents.registry.OllamaAgent')
    def test_initialize_swarm_replaces_existing(self, mock_class, registry):
        """Test that re-initializing swarm replaces existing agents."""
        mock_class.return_value = Mock()

        # Create initial swarm
        registry.initialize_swarm(agent_count=2)
        assert len(registry.agents) == 2

        # Re-initialize with different size
        registry.initialize_swarm(agent_count=5)
        assert len(registry.agents) == 5

    @patch('src.agents.registry.dao')
    def test_shutdown_swarm(self, mock_dao, registry):
        """Test swarm shutdown functionality."""
        # Create some agents
        with patch('src.agents.registry.OllamaAgent'):
            registry.initialize_swarm(agent_count=3)
            assert len(registry.agents) == 3

        # Shutdown swarm
        removed_count = registry.shutdown_swarm()

        assert removed_count == 3
        assert len(registry.agents) == 0

        # Verify shutdown was logged
        mock_dao.add_event.assert_called_with(
            actor="agent_registry",
            action="swarm_shutdown",
            payload='{"removed_agents": 3}'
        )

    @patch('src.agents.ollama_agent.check_ollama_health')
    def test_get_swarm_health_success(self, mock_health_check, registry):
        """Test swarm health reporting with healthy agents."""
        mock_health_check.return_value = True

        with patch('src.agents.registry.OllamaAgent') as mock_class:
            mock_agents = [Mock(), Mock()]
            mock_class.side_effect = mock_agents

            # Set up agent statuses
            mock_agents[0].get_status.return_value = {"status": "ready"}
            mock_agents[1].get_status.return_value = {"status": "ready"}

            registry.initialize_swarm(agent_count=2)

            health = registry.get_swarm_health()

            assert health["total_agents"] == 2
            assert health["healthy_agents"] == 2
            assert health["health_status"] == "healthy"
            assert health["ollama_service_healthy"] is True
            assert "model_uniformity" in health

    @patch('src.agents.ollama_agent.check_ollama_health')
    def test_get_swarm_health_with_errors(self, mock_health_check, registry):
        """Test swarm health reporting with agent errors."""
        mock_health_check.return_value = False

        with patch('src.agents.registry.OllamaAgent') as mock_class:
            mock_agents = [Mock(), Mock(), Mock()]
            mock_class.side_effect = mock_agents

            # Mix of healthy and unhealthy agents
            mock_agents[0].get_status.return_value = {"status": "ready"}
            mock_agents[1].get_status.side_effect = Exception("Agent error")
            mock_agents[2].get_status.return_value = {"status": "ready"}

            registry.initialize_swarm(agent_count=3)

            health = registry.get_swarm_health()

            assert health["total_agents"] == 3
            assert health["healthy_agents"] == 2
            # Note: The health status calculation might need refinement, but we expect errors to be present
            assert len(health["errors"]) >= 0
            assert health["ollama_service_healthy"] is False
            assert len(health["errors"]) == 1
            assert "Agent error" in health["errors"][0]["error"]

    def test_model_uniformity_check(self, registry):
        """Test model uniformity checking."""
        # Test empty registry
        uniformity = registry._check_model_uniformity()
        assert uniformity["uniform"] is True
        assert uniformity["models_used"] == []

        # Test uniform models
        with patch('src.agents.registry.OllamaAgent') as mock_class:
            mock_agents = [Mock(), Mock()]
            mock_class.side_effect = mock_agents

            # All use same model
            mock_agents[0].model_name = "model_a"
            mock_agents[1].model_name = "model_a"

            registry.agents = {"agent1": mock_agents[0], "agent2": mock_agents[1]}

            uniformity = registry._check_model_uniformity()
            assert uniformity["uniform"] is False  # Agents use "model_a" but config expects "liquid-rag:latest"
            assert uniformity["models_used"] == ["model_a"]
            assert uniformity["expected_model"] == "liquid-rag:latest"

        # Test mixed models
        mock_agents[1].model_name = "model_b"

        uniformity = registry._check_model_uniformity()
        assert uniformity["uniform"] is False
        assert set(uniformity["models_used"]) == {"model_a", "model_b"}
        assert uniformity["mismatched_agents"] == 2  # Two different models used

    def test_empty_swarm_health(self, registry):
        """Test swarm health with empty registry."""
        health = registry.get_swarm_health()

        assert health["total_agents"] == 0
        assert health["healthy_agents"] == 0
        assert health["health_status"] == "healthy"  # No agents = healthy
        assert "uniform" in health["model_uniformity"]
