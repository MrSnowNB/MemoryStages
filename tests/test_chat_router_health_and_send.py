import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


def test_chat_health_endpoint():
    with patch('src.core.config.CHAT_API_ENABLED', True):
        from src.api import main
        client = TestClient(main.app)

        response = client.get("/chat/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data


def test_chat_message_simple_send():
    with patch('src.core.config.CHAT_API_ENABLED', True):
        from src.api import main
        client = TestClient(main.app)

        response = client.post("/chat/message", json={"content": "ping", "user_id": "t"})

        assert response.status_code == 200
