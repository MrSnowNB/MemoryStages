"""
Stage 7 MVP - Test Orchestrator
Tests for the rule-based orchestrator and swarm decision making.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.agents.orchestrator import RuleBasedOrchestrator, OrchestratorDecision
from src.agents.agent import AgentResponse


class TestRuleBasedOrchestrator:
    """Test cases for rule-based orchestrator functionality."""

    @pytest.fixture
    def mock_registry(self):
        """Create a mock agent registry."""
        registry = Mock()
        registry.initialize_swarm.return_value = ["agent_1", "agent_2", "agent_3", "agent_4"]
        registry.get_agent.return_value = Mock()
        registry.get_swarm_health.return_value = {
            "total_agents": 4,
            "healthy_agents": 4,
            "health_status": "healthy",
            "ollama_service_healthy": True
        }
        return registry

    @pytest.fixture
    def orchestrator(self, mock_registry):
        """Create orchestrator with mocked registry."""
        with patch('src.agents.orchestrator.AgentRegistry', return_value=mock_registry):
            orc = RuleBasedOrchestrator()
            orc.agents = ["agent_1", "agent_2", "agent_3", "agent_4"]  # Override swarm init
            return orc

    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initializes correctly."""
        assert orchestrator.agent_registry is not None
        assert isinstance(orchestrator.agents, list)
        assert len(orchestrator.archives) == 0

    def test_orchestrator_status(self, orchestrator):
        """Test orchestrator status reporting."""
        status = orchestrator.get_orchestrator_status()
        assert status['orchestrator_type'] == 'rule_based'
        assert 'swarm_health' in status
        assert 'timestamp' in status
        assert 'agents_available' in status

    @patch('src.agents.orchestrator.dao')
    def test_process_user_message_no_agents(self, mock_dao, orchestrator):
        """Test processing message when no agents are available."""
        orchestrator.agents = []  # Simulate no agents

        response = orchestrator.process_user_message(
            message="Hello",
            session_id="test_session",
            user_id="test_user"
        )

        assert isinstance(response, AgentResponse)
        assert "don't have enough information" in response.content.lower()
        assert response.confidence == 0.1
        assert not response.metadata.get('validation_passed', True)

    @patch('src.agents.orchestrator.dao')
    def test_process_user_message_with_agents(self, mock_dao, orchestrator):
        """Test processing message with multiple agents."""
        # Mock agent responses
        mock_agent = Mock()
        mock_responses = [
            AgentResponse(
                content="This is response 1",
                model_used="test-model",
                confidence=0.6,
                metadata={"agent_id": "agent_1"}
            ),
            AgentResponse(
                content="This is a longer, more detailed response 2",
                model_used="test-model",
                confidence=0.8,
                metadata={"agent_id": "agent_2"}
            ),
            AgentResponse(
                content="Short response 3 according to my knowledge",
                model_used="test-model",
                confidence=0.7,
                metadata={"agent_id": "agent_3"}
            )
        ]

        # Mock registry to return mock agent
        orchestrator.agent_registry.get_agent.side_effect = lambda agent_id: mock_agent
        mock_agent.process_message.side_effect = mock_responses

        response = orchestrator.process_user_message(
            message="What is AI?",
            session_id="test_session",
            user_id="test_user"
        )

        assert isinstance(response, AgentResponse)
        assert response.content is not None
        assert response.confidence > 0
        assert response.processing_time_ms >= 0
        assert "agents_consulted" in response.metadata

        # Verify logging
        mock_dao.add_event.assert_called()

    def test_orchestrator_decision_scoring(self, orchestrator):
        """Test the response scoring algorithm."""
        # Test with memory context
        memory_context = [{"content": "AI is artificial intelligence", "source": "memory"}]

        # High scoring response (references memory, good length, addresses query)
        response1 = AgentResponse(
            content="AI is artificial intelligence technology",
            model_used="test-model",
            confidence=0.8,
            metadata={"agent_id": "agent_1"}
        )

        # Low scoring response (hallucination indicators, poor length)
        response2 = AgentResponse(
            content="According to my knowledge, this is AI.",
            model_used="test-model",
            confidence=0.4,
            metadata={"agent_id": "agent_2"}
        )

        score1 = orchestrator._score_response(response1, "What is AI?", memory_context)
        score2 = orchestrator._score_response(response2, "What is AI?", memory_context)

        assert score1 > score2
        assert score1 > 0.7  # Should score well
        assert score2 < 0.5  # Should score poorly

    def test_response_references_memory(self, orchestrator):
        """Test memory reference detection."""
        memory_context = [
            {"content": "Python is a programming language used for web development"},
            {"content": "Machine learning is part of AI"}
        ]

        # Should detect reference
        assert orchestrator._response_references_memory(
            "Python is great for programming and web development",
            memory_context
        )

        # Should not detect reference - use completely different example
        assert not orchestrator._response_references_memory(
            "The weather today is sunny and clear",
            memory_context
        )

    def test_hallucination_penalty(self, orchestrator):
        """Test hallucination penalty calculation."""
        # Response with hallucination indicators
        hallucinating_response = "According to my knowledge, based on my experience, I believe that..."

        # Response without indicators
        clean_response = "This is a direct statement without qualifiers."

        penalty1 = orchestrator._calculate_hallucination_penalty(hallucinating_response)
        penalty2 = orchestrator._calculate_hallucination_penalty(clean_response)

        assert penalty1 < penalty2  # More negative penalty for hallucinating
        assert penalty1 <= -0.1  # At least some penalty
        assert penalty2 == 0  # No penalty

    def test_response_addresses_query(self, orchestrator):
        """Test query addressing detection."""
        query = "What is machine learning"

        # Direct address
        assert orchestrator._response_addresses_query(
            "Machine learning is a subset of AI algorithms",
            query
        )

        # Indirect address
        assert orchestrator._response_addresses_query(
            "Machine learning involves algorithms that learn from data",
            query
        )

        # No address
        assert not orchestrator._response_addresses_query(
            "Python is a programming language",
            query
        )

    def test_factual_claims_detection(self, orchestrator):
        """Test detection of factual claims in responses."""
        assert orchestrator._response_makes_factual_claims("Python is fast")
        assert orchestrator._response_makes_factual_claims("AI has applications")
        assert not orchestrator._response_makes_factual_claims("Hello there")
        assert not orchestrator._response_makes_factual_claims("How are you?")

    def test_validation_disabled(self, orchestrator):
        """Test validation behavior when strict validation is disabled."""
        # Mock the config variable
        with patch('src.agents.orchestrator.RESPONSE_VALIDATION_STRICT', False):
            result = orchestrator._validate_response_against_memory(
                "Some response with facts",
                [],
                "Test query"
            )

            # Should return original response when validation disabled
            assert result == "Some response with facts"

    def test_validation_with_factual_claims(self, orchestrator):
        """Test validation when response makes factual claims."""
        # Mock the config variable
        with patch('src.agents.orchestrator.RESPONSE_VALIDATION_STRICT', True):
            # Response making claims but no memory context
            memory_context = []  # No memory

            result = orchestrator._validate_response_against_memory(
                "Python is the best language",
                memory_context,
                "What is the best language?"
            )

            # Should be allowed since no memory context to validate against
            assert result == "Python is the best language"

    def test_decision_archiving(self, orchestrator):
        """Test that decisions are archived for analysis."""
        decision = OrchestratorDecision(
            selected_response="Test response",
            confidence=0.8,
            agents_consulted=["agent1"],
            validation_passed=True,
            memory_sources=["memory"],
            decision_reasoning="test_reasoning"
        )

        agent_responses = [AgentResponse(content="resp", model_used="model", confidence=0.5)]
        final_response = AgentResponse(
            content="final",
            model_used="model",
            confidence=0.8,
            processing_time_ms=100
        )

        orchestrator._archive_decision(decision, agent_responses, "test message", final_response)

        assert len(orchestrator.archives) == 1
        archive = orchestrator.archives[0]
        assert archive['user_message'] == "test message"
        assert archive['decision']['confidence'] == 0.8

    def test_empty_response_handling(self, orchestrator):
        """Test handling of empty or invalid agent responses."""
        # Simulate agent failure with empty content
        agent_responses = [
            AgentResponse(content="", model_used="model", confidence=0.5),
            AgentResponse(content="Valid response here", model_used="model", confidence=0.7)
        ]

        decision = orchestrator._make_orchestrator_decision(
            "Test query",
            agent_responses,
            []
        )

        # Should still select a valid response
        assert decision.selected_response is not None
        assert len(decision.selected_response) > 0
        assert decision.confidence >= 0

    def test_error_response_creation(self, orchestrator):
        """Test that error responses are properly structured."""
        message = Mock()
        message.content = "test message"

        error_response = orchestrator._create_error_response("Test error", message)

        assert isinstance(error_response, AgentResponse)
        assert error_response.confidence == 0.0
        assert "Test error" in error_response.content
        assert error_response.metadata.get('error_occurred') is True


class TestOrchestratorDecision:
    """Test the OrchestratorDecision dataclass."""

    def test_decision_dataclass(self):
        """Test OrchestratorDecision creation and attributes."""
        decision = OrchestratorDecision(
            selected_response="Test response",
            confidence=0.85,
            agents_consulted=["agent1", "agent2"],
            validation_passed=True,
            memory_sources=["memory", "vector"],
            decision_reasoning="rule_based_selection"
        )

        assert decision.selected_response == "Test response"
        assert decision.confidence == 0.85
        assert len(decision.agents_consulted) == 2
        assert decision.validation_passed is True
        assert len(decision.memory_sources) == 2
        assert decision.decision_reasoning == "rule_based_selection"


@pytest.fixture
def basic_orchestrator():
    """Create basic orchestrator for testing without swarm initialization."""
    orchestrator = RuleBasedOrchestrator()
    orchestrator.agents = []  # Disable swarm for controlled testing
    return orchestrator
