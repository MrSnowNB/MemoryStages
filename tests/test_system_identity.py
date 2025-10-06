"""
Stage 6: System Identity Tests
Tests for system identity question detection and bypass logic.
"""

import pytest
from unittest.mock import patch


class TestSystemIdentity:
    """Test system identity question detection and bypass."""

    @pytest.mark.parametrize("question,expected_source", [
        ("What model are you using?", "OLLAMA_MODEL"),
        ("What AI model is this?", "OLLAMA_MODEL"),
        ("What language model do you use?", "OLLAMA_MODEL"),
        ("What orchestrator are you running?", "orchestrator_type"),
        ("What system type is being used?", "orchestrator_type"),
        ("How many agents do you have?", "agents_available"),
        ("What agents are running?", "agents_available"),
        ("What architecture does this use?", "system_architecture"),
        ("What is the system configuration?", "system_architecture"),
    ])
    def test_system_identity_question_detection(self, question, expected_source):
        """Test detection of system identity questions."""
        from src.api.chat import _check_system_identity_question

        result = _check_system_identity_question(question)
        assert result is not None
        assert result["source"] == expected_source
        assert "content" in result
        assert "confidence" in result
        assert "value" in result

    def test_system_identity_question_responses(self):
        """Test that system identity questions return expected responses."""
        from src.api.chat import _check_system_identity_question

        # Test model question
        result = _check_system_identity_question("What model are you using?")
        assert result is not None
        assert "llama3.2" in result["content"].lower()  # From OLLAMA_MODEL
        assert result["confidence"] == 1.0

        # Test orchestrator question
        result = _check_system_identity_question("What orchestrator do you use?")
        assert result is not None
        assert "rule_based" in result["content"].lower()
        assert result["confidence"] == 1.0

        # Test architecture question
        result = _check_system_identity_question("What architecture does this system use?")
        assert result is not None
        assert "modular" in result["content"].lower()
        assert "orchestrator" in result["content"].lower()

    def test_system_identity_non_questions_ignored(self):
        """Test that non-identity questions are not intercepted."""
        from src.api.chat import _check_system_identity_question

        # Test regular query that should not be intercepted
        result = _check_system_identity_question("What is the weather like today?")
        assert result is None

        result = _check_system_identity_question("Tell me about pizza")
        assert result is None

        result = _check_system_identity_question("Set my display name to John")
        assert result is None

    @patch('src.api.chat.orchestrator')
    def test_chat_api_identity_bypass_integration(self, mock_orchestrator):
        """Test that chat API bypasses orchestrator for identity questions."""
        from src.api.chat import router
        from fastapi.testclient import TestClient
        from fastapi import FastAPI

        # Create test app with router
        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)

        # Make request for identity question (should bypass orchestrator)
        response = client.post("/message", json={
            "content": "What model are you using?",
            "user_id": "test_user"
        })

        assert response.status_code == 200
        data = response.json()
        assert "llama3.2" in data["content"].lower()
        assert data["orchestrator_type"] == "bypassed"
        assert data["agents_consulted"] == []  # No agents consulted
        assert len(data["memory_results"]) == 1
        assert data["memory_results"][0]["type"] == "system_config"

        # Verify orchestrator was not called
        mock_orchestrator.process_user_message.assert_not_called()

    def test_system_identity_agent_count_response(self):
        """Test agent count response from system identity."""
        from src.api.chat import _check_system_identity_question

        # Test agent count question
        result = _check_system_identity_question("How many agents do you have?")
        assert result is not None
        assert "agents" in result["content"].lower()
        assert result["confidence"] == 1.0
        assert "agents_available" in result["source"]

    def test_system_identity_direct_config_access(self):
        """Test that identity answers come from direct config access, not LLM."""
        from src.api.chat import _get_system_identity_answer

        # Test model identity
        result = _get_system_identity_answer("What model are you using?")
        assert result is not None
        assert "llama3.2" in result["content"].lower()
        assert result["source"] == "OLLAMA_MODEL"
        assert result["confidence"] == 1.0
