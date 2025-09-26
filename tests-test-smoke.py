"""Smoke tests for Stage 1 bot-swarm memory system."""

import os
import tempfile
import pytest
from unittest import TestCase

from src.core.config import Config
from src.core.db import init_database, check_db_health
from src.core import dao

class TestStage1Smoke(TestCase):
    """Smoke tests for Stage 1 functionality."""
    
    def setUp(self):
        """Set up test with temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Override config for testing
        original_path = Config.DB_PATH
        Config.DB_PATH = self.temp_db.name
        
        # Initialize test database
        init_database()
        
        # Store original for cleanup
        self.original_db_path = original_path
    
    def tearDown(self):
        """Clean up test database."""
        Config.DB_PATH = self.original_db_path
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_database_health(self):
        """Test database health check."""
        self.assertTrue(check_db_health())
    
    def test_kv_set_and_get_with_casing(self):
        """Test setting and getting KV with exact casing preservation."""
        # Set displayName with exact casing
        result = dao.set_key('displayName', 'Mark', source='user')
        self.assertEqual(result['key'], 'displayName')
        self.assertEqual(result['value'], 'Mark')
        self.assertIsNotNone(result['updated_at'])
        
        # Get it back and verify casing preserved
        kv_result = dao.get_key('displayName')
        self.assertIsNotNone(kv_result)
        self.assertEqual(kv_result.key, 'displayName')
        self.assertEqual(kv_result.value, 'Mark')
        self.assertEqual(kv_result.source, 'user')
        self.assertEqual(kv_result.casing, 'displayName')
        self.assertFalse(kv_result.sensitive)
    
    def test_kv_update_with_timestamp_change(self):
        """Test KV update increments timestamp."""
        # Set initial value
        dao.set_key('favorite_color', 'Purple', source='user')
        first_result = dao.get_key('favorite_color')
        first_timestamp = first_result.updated_at
        
        # Update value
        import time
        time.sleep(0.01)  # Ensure timestamp difference
        dao.set_key('favorite_color', 'Blue', source='user')
        second_result = dao.get_key('favorite_color')
        
        # Verify value changed and timestamp increased
        self.assertEqual(second_result.value, 'Blue')
        self.assertGreater(second_result.updated_at, first_timestamp)
    
    def test_kv_sensitive_flag(self):
        """Test sensitive flag handling."""
        # Set sensitive data
        dao.set_key('secret_key', 'sensitive_value', source='user', sensitive=1)
        result = dao.get_key('secret_key')
        
        self.assertTrue(result.sensitive)
        self.assertEqual(result.value, 'sensitive_value')
    
    def test_kv_list(self):
        """Test listing all KV pairs."""
        # Add multiple keys
        dao.set_key('key1', 'value1', source='test')
        dao.set_key('key2', 'value2', source='test')
        
        # List and verify
        all_keys = dao.list_keys()
        self.assertGreaterEqual(len(all_keys), 2)
        
        # Check that our keys are present
        keys = [item['key'] for item in all_keys]
        self.assertIn('key1', keys)
        self.assertIn('key2', keys)
    
    def test_kv_tombstone_delete(self):
        """Test tombstone deletion of keys."""
        # Set and delete a key
        dao.set_key('temp_key', 'temp_value', source='test')
        dao.delete_key('temp_key')
        
        # Verify key still exists but has empty value (tombstone)
        result = dao.get_key('temp_key')
        self.assertIsNotNone(result)
        self.assertEqual(result.value, '')
    
    def test_episodic_logging(self):
        """Test episodic event logging."""
        # Add an event
        payload = {'key': 'test_key', 'value': 'test_value', 'source': 'test'}
        result = dao.add_event('test_actor', 'test_action', payload)
        
        self.assertIsNotNone(result['id'])
        self.assertIsNotNone(result['ts'])
        
        # List events and verify our event is there
        events = dao.list_events(limit=10)
        self.assertGreater(len(events), 0)
        
        # Should have our event plus any from KV operations
        found_event = False
        for event in events:
            if (event.actor == 'test_actor' and 
                event.action == 'test_action'):
                found_event = True
                break
        
        self.assertTrue(found_event, "Added event not found in episodic log")
    
    def test_kv_operations_create_episodic_events(self):
        """Test that KV operations automatically create episodic events."""
        initial_event_count = len(dao.list_events())
        
        # Set a key (should create episodic event)
        dao.set_key('episodic_test', 'test_value', source='test')
        
        # Check that event count increased
        final_event_count = len(dao.list_events())
        self.assertGreater(final_event_count, initial_event_count)
        
        # Verify the event details
        events = dao.list_events(limit=5)
        kv_set_event = None
        for event in events:
            if event.action == 'kv_set':
                kv_set_event = event
                break
        
        self.assertIsNotNone(kv_set_event)
        self.assertEqual(kv_set_event.actor, 'memory_manager')
    
    def test_kv_count(self):
        """Test KV count functionality."""
        initial_count = dao.get_kv_count()
        
        # Add some keys
        dao.set_key('count_test_1', 'value1', source='test')
        dao.set_key('count_test_2', 'value2', source='test')
        
        # Verify count increased
        new_count = dao.get_kv_count()
        self.assertEqual(new_count, initial_count + 2)
        
        # Delete one (tombstone) - should still count
        dao.delete_key('count_test_1')
        tombstone_count = dao.get_kv_count()
        
        # Tombstones have empty value, so count should decrease
        self.assertEqual(tombstone_count, initial_count + 1)

if __name__ == '__main__':
    pytest.main([__file__, '-v'])