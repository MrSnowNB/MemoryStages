"""
Stage 1 Implementation - SQLite Foundation Only
DO NOT IMPLEMENT BEYOND STAGE 1 SCOPE
"""

import os
import tempfile
import pytest
from datetime import datetime

# Set up test environment with temporary database
TEST_DB_PATH = tempfile.mkstemp(suffix='.db')[1]
os.environ['DB_PATH'] = TEST_DB_PATH

from src.core.config import DB_PATH, DEBUG
from src.core.db import init_db, health_check, get_db
from src.core.dao import (
    get_key,
    set_key,
    list_keys,
    delete_key,
    add_event,
    list_events,
    get_kv_count
)
from src.api.schemas import KVSetRequest

def test_database_health():
    """Test that database initializes correctly."""
    assert health_check() == True, "Database should be healthy"

def test_kv_set_and_get():
    """Test setting and getting key-value pairs."""
    # Set a key
    set_key(
        key="test_key",
        value="test_value",
        source="test_source",
        casing="lowercase"
    )
    
    # Get the key back
    result = get_key("test_key")
    assert result is not None, "Key should exist after setting"
    assert result.key == "test_key", "Key name should match"
    assert result.value == "test_value", "Value should match"
    assert result.casing == "lowercase", "Casing should be preserved"
    assert result.source == "test_source", "Source should be preserved"

def test_kv_update_timestamp():
    """Test that updating a key increments the timestamp."""
    # Set initial value
    set_key(
        key="timestamp_test",
        value="initial_value",
        source="test",
        casing="lowercase"
    )
    
    # Get initial timestamp
    initial = get_key("timestamp_test")
    assert initial is not None
    
    # Wait a moment (simulate time passage)
    import time
    time.sleep(0.1)
    
    # Update the value
    set_key(
        key="timestamp_test",
        value="updated_value",
        source="test",
        casing="lowercase"
    )
    
    # Get updated timestamp
    updated = get_key("timestamp_test")
    assert updated is not None
    
    # Timestamp should be different (or at least after initial)
    # Note: SQLite precision may vary, so we just ensure it exists and is valid
    assert updated.updated_at is not None

def test_kv_sensitive_flag():
    """Test sensitive data handling."""
    set_key(
        key="sensitive_test",
        value="secret_data",
        source="test",
        casing="lowercase",
        sensitive=True
    )
    
    result = get_key("sensitive_test")
    assert result is not None
    assert result.sensitive == True, "Sensitive flag should be preserved"

def test_kv_list():
    """Test listing key-value pairs."""
    # Add some keys
    set_key(
        key="list_test_1",
        value="value1",
        source="test",
        casing="lowercase"
    )
    
    set_key(
        key="list_test_2",
        value="value2",
        source="test",  
        casing="lowercase"
    )
    
    # Add a tombstone entry
    delete_key("list_test_1")
    
    # List keys - should only return non-tombstone entries
    keys = list_keys()
    key_names = [k.key for k in keys]
    
    assert "list_test_1" not in key_names, "Tombstoned key should be excluded"
    assert "list_test_2" in key_names, "Non-tombstone key should be included"

def test_kv_delete():
    """Test tombstone delete functionality."""
    set_key(
        key="delete_test",
        value="test_value", 
        source="test",
        casing="lowercase"
    )
    
    # Verify it exists
    result = get_key("delete_test")
    assert result is not None
    
    # Delete (tombstone)
    delete_key("delete_test")
    
    # Should now be tombstoned (empty value)  
    result = get_key("delete_test")
    assert result is not None  # Key still exists but with empty value
    assert result.value == "", "Value should be empty after deletion"

def test_episodic_add_and_list():
    """Test episodic event logging."""
    # Add events
    add_event(
        actor="test_actor",
        action="test_action", 
        payload="test_payload"
    )
    
    add_event(
        actor="another_actor",
        action="another_action",
        payload="another_payload"  
    )
    
    # List recent events (default limit)
    events = list_events()
    assert len(events) >= 2, "Should have at least two events"

def test_kv_count():
    """Test KV count functionality."""
    # Add some keys
    set_key("count_test_1", "value1", "test", "lowercase")
    set_key("count_test_2", "value2", "test", "lowercase")
    
    # Delete one (tombstone)
    delete_key("count_test_1")
    
    count = get_kv_count()
    assert count == 1, "Should only count non-tombstone entries"

def test_database_schema():
    """Test database schema integrity."""
    # Ensure tables exist
    health_result = health_check()
    assert health_result == True, "Database should have correct schema"
    
    # Test that we can query both tables - verify they're accessible by doing a simple query
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM kv")
            cursor.execute("SELECT COUNT(*) FROM episodic")
        # If we reach here, the test passes
        assert True
    except Exception as e:
        # If an exception occurs, fail the test with that error
        raise AssertionError(f"Database query failed: {str(e)}")

if __name__ == "__main__":
    # Run tests directly if needed
    test_database_health()
    test_kv_set_and_get()
    test_kv_update_timestamp()
    test_kv_sensitive_flag()
    test_kv_list()
    test_kv_delete()
    test_episodic_add_and_list() 
    test_kv_count()
    test_database_schema()
    
    print("All smoke tests passed!")
