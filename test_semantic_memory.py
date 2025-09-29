#!/usr/bin/env python3
"""
Quick test to verify semantic memory is working for the reported issue.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastapi.testclient import TestClient
from src.api.main import app

def test_semantic_memory_fix():
    """Test that semantic queries now hit memory instead of going to agents."""

    client = TestClient(app)

    # First, store a memory about favorite dessert
    chat_payload = {
        "content": "remember my favorite dessert is chocolate cake",
        "user_id": "test_user"
    }
    response = client.post("/chat/message", json=chat_payload, headers={"Authorization": "Bearer web-demo-token"})
    print(f"Set memory response: {response.status_code}")
    assert response.status_code == 200

    # Now test the semantic query
    query_payload = {
        "content": "What sweet foods do I like?",
        "user_id": "test_user"
    }
    response = client.post("/chat/message", json=query_payload, headers={"Authorization": "Bearer web-demo-token"})
    print(f"Query response status: {response.status_code}")
    assert response.status_code == 200

    data = response.json()
    content = data.get("content", "")
    agents_consulted = len(data.get("agents_consulted", [])) if data.get("agents_consulted") else 0

    print(f"Response content: {content}")
    print(f"Agents consulted: {agents_consulted}")
    print(f"Memory sources: {data.get('memory_sources', [])}")

    # Check if semantic memory hit worked
    if "chocolate" in content.lower() or "cake" in content.lower():
        print("✅ SUCCESS: Semantic memory returned chocolate cake!")
        return True
    elif agents_consulted > 0:
        print("❌ FAILED: Still going to agents instead of semantic memory")
        return False
    else:
        print(f"❓ INCONCLUSIVE: Got response '{content}' with {agents_consulted} agents - may need vector indexing")
        return False

if __name__ == "__main__":
    try:
        success = test_semantic_memory_fix()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Test failed with exception: {e}")
        sys.exit(1)
