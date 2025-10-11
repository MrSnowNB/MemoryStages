import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


def test_chat_simple_endpoint():
    with patch('src.core.config.CHAT_API_ENABLED', True):
        from src.api import main
        client = TestClient(main.app)

        response = client.post("/chat", json={"message": "ping", "user_id": "t"})

        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
