#!/usr/bin/env python3

import requests
import json
import time

API_BASE = "http://localhost:8000"

def test_episodic_endpoints():
    """Manual testing of episodic endpoints"""

    print("=== Testing Episodic Memory API Endpoints ===\n")

    # Test 1: Log an episodic event
    print("1. Testing event logging...")
    event_data = {
        "session_id": "test-session-123",
        "event_type": "user",
        "message": "Test user message for Stage 5 validation",
        "summary": "Testing episodic memory logging",
        "sensitive": False
    }

    try:
        response = requests.post(f"{API_BASE}/episodic/event", json=event_data)
        print(f"Event log result: {response.status_code}")
        if response.status_code == 200:
            print("✅ Event logged successfully")
        else:
            print(f"❌ Failed to log event: {response.text}")
    except Exception as e:
        print(f"❌ Error logging event: {e}")

    # Test 2: Log AI response
    print("\n2. Testing AI event logging...")
    ai_event_data = {
        "session_id": "test-session-123",
        "event_type": "ai",
        "message": "Test AI response generated",
        "summary": "AI generated response for test",
        "sensitive": False
    }

    try:
        response = requests.post(f"{API_BASE}/episodic/event", json=ai_event_data)
        print(f"AI event log result: {response.status_code}")
        if response.status_code == 200:
            print("✅ AI event logged successfully")
        else:
            print(f"❌ Failed to log AI event: {response.text}")
    except Exception as e:
        print(f"❌ Error logging AI event: {e}")

    # Test 3: Log sensitive event
    print("\n3. Testing sensitive event logging...")
    sensitive_event_data = {
        "session_id": "test-session-sensitive",
        "event_type": "system",
        "message": "Sensitive test credentials: admin/password123",
        "summary": "Sensitive credential test",
        "sensitive": True
    }

    try:
        response = requests.post(f"{API_BASE}/episodic/event", json=sensitive_event_data)
        print(f"Sensitive event log result: {response.status_code}")
        if response.status_code == 200:
            print("✅ Sensitive event logged successfully")
        else:
            print(f"❌ Failed to log sensitive event: {response.text}")
    except Exception as e:
        print(f"❌ Error logging sensitive event: {e}")

    # Test 4: Retrieve recent events
    print("\n4. Testing recent events retrieval...")
    try:
        response = requests.get(f"{API_BASE}/episodic/recent?user_id=default&limit=10")
        print(f"Recent events result: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Retrieved {data.get('count', 0)} events")
            events = data.get('events', [])
            if events:
                print(f"Sample event: {events[0]}")
        else:
            print(f"❌ Failed to retrieve events: {response.text}")
    except Exception as e:
        print(f"❌ Error retrieving events: {e}")

    # Test 5: Retrieve session events
    print("\n5. Testing session events retrieval...")
    try:
        response = requests.get(f"{API_BASE}/episodic/recent?session_id=test-session-123&limit=5")
        print(f"Session events result: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Retrieved {data.get('count', 0)} events for session")
        else:
            print(f"❌ Failed to retrieve session events: {response.text}")
    except Exception as e:
        print(f"❌ Error retrieving session events: {e}")

    # Test 6: Summarize events
    print("\n6. Testing event summarization...")
    try:
        summary_data = {
            "session_id": "test-session-123",
            "use_ai": False,
            "limit": 10
        }
        response = requests.post(f"{API_BASE}/episodic/summarize", json=summary_data)
        print(f"Summarize result: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Summary generated: {data.get('summary', '')[:100]}...")
        else:
            print(f"❌ Failed to summarize: {response.text}")
    except Exception as e:
        print(f"❌ Error summarizing events: {e}")

    # Test 7: List sessions
    print("\n7. Testing session listing...")
    try:
        response = requests.get(f"{API_BASE}/episodic/sessions?limit=5")
        print(f"Session list result: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Retrieved {data.get('count', 0)} recent sessions")
            sessions = data.get('sessions', [])
            if sessions:
                print(f"Sample session: {sessions[0]}")
        else:
            print(f"❌ Failed to list sessions: {response.text}")
    except Exception as e:
        print(f"❌ Error listing sessions: {e}")

    print("\n=== Episodic API Testing Complete ===")

if __name__ == "__main__":
    test_episodic_endpoints()
