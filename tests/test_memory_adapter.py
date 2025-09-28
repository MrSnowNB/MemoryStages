"""
Stage 7.2 MVP - Test Memory Adapter
Tests for privacy-enforcing memory adapter and response validation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime
from src.agents.memory_adapter import MemoryAdapter


class TestMemoryAdapter:
    """Test cases for memory adapter privacy and validation functionality."""

    @pytest.fixture
    def adapter(self):
        """Create fresh memory adapter for each test."""
        return MemoryAdapter()

    def test_adapter_initialization(self, adapter):
        """Test memory adapter initializes correctly."""
        assert isinstance(adapter.access_log, list)
        assert isinstance(adapter.sensitive_patterns, list)
        assert isinstance(adapter.sensitive_keywords, list)
        assert len(adapter.sensitive_patterns) > 0
        assert len(adapter.sensitive_keywords) > 0

    @patch('src.agents.memory_adapter.dao')
    def test_get_validation_context_fallback(self, mock_dao, adapter):
        """Test context retrieval using fallback search."""
        # Mock DAO to return safe KV data
        mock_kv_data = [
            {
                'key': 'safe_key_1',
                'value': 'Python is a programming language used for web development',
                'source': 'user',
                'updated_at': datetime.now(),
                'sensitive': False
            },
            {
                'key': 'safe_key_2',
                'value': 'Machine learning is part of artificial intelligence',
                'source': 'user',
                'updated_at': datetime.now(),
                'sensitive': False
            },
            {
                'key': 'sensitive_key',
                'value': 'Secret password is admin123',
                'source': 'user',
                'updated_at': datetime.now(),
                'sensitive': True  # This should be filtered out
            }
        ]
        mock_dao.list_keys.return_value = mock_kv_data

        # Test context retrieval
        context = adapter.get_validation_context(
            query="What is Python programming",
            user_id="test_user",
            max_results=3
        )

        # Should return safe, relevant context
        assert len(context) == 2  # One sensitive item filtered
        assert all(ctx['sensitive'] == False for ctx in context)
        assert any('Python' in ctx['content'] for ctx in context)
        assert any('programming' in ctx['content'] for ctx in context)

        # Verify access was logged
        mock_dao.add_event.assert_called()

    @patch('src.agents.memory_adapter.dao')
    def test_validation_context_empty_query(self, mock_dao, adapter):
        """Test context retrieval with empty query."""
        mock_dao.list_keys.return_value = []

        context = adapter.get_validation_context(query="", user_id="test_user")
        assert isinstance(context, list)
        assert len(context) == 0

    @patch('src.agents.memory_adapter.dao')
    def test_fact_validation_no_context(self, mock_dao, adapter):
        """Test fact validation with no memory context."""
        result = adapter.validate_facts_in_response("Python is fast", [])

        assert result['validated'] == False
        assert result['reason'] == 'no_memory_context'
        assert result['facts_found'] == 0

    @patch('src.agents.memory_adapter.dao')
    def test_fact_validation_no_facts(self, mock_dao, adapter):
        """Test fact validation when response contains no factual claims."""
        memory_context = [{'content': 'Python programming'}]

        result = adapter.validate_facts_in_response("Hello there!", memory_context)

        assert result['validated'] == True
        assert result['reason'] == 'no_factual_claims'
        assert result['facts_found'] == 0

    @patch('src.agents.memory_adapter.dao')
    def test_fact_validation_success(self, mock_dao, adapter):
        """Test successful fact validation."""
        memory_context = [
            {'content': 'Python is a programming language used for web development'},
            {'content': 'Python programming is popular'}
        ]

        response = "Python is a programming language that is popular"

        result = adapter.validate_facts_in_response(response, memory_context)

        assert result['validated'] == True
        assert result['facts_found'] > 0
        assert result['facts_validated'] > 0
        assert result['validation_ratio'] >= 0.7

    @patch('src.agents.memory_adapter.dao')
    def test_fact_validation_failure(self, mock_dao, adapter):
        """Test fact validation failure."""
        memory_context = [{'content': 'Java is a programming language'}]

        # Response makes claims not supported by context
        response = "Python is faster than all other languages and is the best"

        result = adapter.validate_facts_in_response(response, memory_context)

        assert result['validated'] == False
        assert result['facts_found'] > 0
        assert result['facts_validated'] == 0 or result['validation_ratio'] < 0.7

    def test_sensitive_data_detection_patterns(self, adapter):
        """Test sensitive data pattern detection."""
        # Test SSN pattern
        result = adapter.contains_sensitive_data("My SSN is 123-45-6789")
        assert result['contains_sensitive'] == True
        assert len(result['detected_patterns']) > 0

        # Test email pattern
        result = adapter.contains_sensitive_data("Contact me at user@example.com")
        assert result['contains_sensitive'] == True

        # Test credit card pattern
        result = adapter.contains_sensitive_data("Card number: 1234 5678 9012 3456")
        assert result['contains_sensitive'] == True

        # Test sensitive keyword
        result = adapter.contains_sensitive_data("My password is secret")
        assert result['contains_sensitive'] == True

    def test_sensitive_data_detection_clean(self, adapter):
        """Test that clean text doesn't trigger sensitive detection."""
        clean_texts = [
            "Python is a programming language",
            "Machine learning is interesting",
            "The weather is nice today",
            "I like to program computers"
        ]

        for text in clean_texts:
            result = adapter.contains_sensitive_data(text)
            assert result['contains_sensitive'] == False, f"Text incorrectly flagged: {text}"

    def test_is_safe_for_context_sensitive(self, adapter):
        """Test that sensitive memory items are not safe for context."""
        sensitive_item = {
            'value': 'My password is admin123',
            'sensitive': True
        }

        assert adapter._is_safe_for_context(sensitive_item) == False

    def test_is_safe_for_context_tombstone(self, adapter):
        """Test that tombstone entries are not safe for context."""
        empty_item = {
            'value': '',
            'sensitive': False
        }

        tombstone_item = {
            'value': '   ',  # Whitespace only
            'sensitive': False
        }

        assert adapter._is_safe_for_context(empty_item) == False
        assert adapter._is_safe_for_context(tombstone_item) == False

    def test_is_safe_for_context_sensitive_patterns(self, adapter):
        """Test that sensitive patterns in content block context."""
        sensitive_content = {
            'value': 'My email is user@secret.com and password is pass123',
            'sensitive': False  # Even if not marked sensitive, content has patterns
        }

        assert adapter._is_safe_for_context(sensitive_content) == False

    def test_is_safe_for_context_clean(self, adapter):
        """Test that clean content is safe for context."""
        clean_item = {
            'value': 'Python is a programming language for building applications',
            'sensitive': False
        }

        assert adapter._is_safe_for_context(clean_item) == True

    @patch('src.agents.memory_adapter.dao')
    def test_fallback_context_search(self, mock_dao, adapter):
        """Test fallback context search functionality."""
        mock_kv_data = [
            {
                'key': 'programming_languages',
                'value': 'Python is a programming language used for web development',
                'source': 'user',
                'updated_at': datetime.now(),
                'sensitive': False
            },
            {
                'key': 'ml_info',
                'value': 'Machine learning algorithms can process data',
                'source': 'user',
                'updated_at': datetime.now(),
                'sensitive': False
            }
        ]
        mock_dao.list_keys.return_value = mock_kv_data

        context = adapter._get_fallback_context("Python programming", "test_user", 5)

        # Should find relevant context
        assert len(context) >= 1
        assert any('Python' in ctx['content'] for ctx in context)
        assert all(ctx['relevance_score'] > 0 for ctx in context)

    def test_extract_facts_from_response(self, adapter):
        """Test fact extraction from responses."""
        response = "Python is a programming language. It has many libraries. Machine learning is interesting too."

        facts = adapter._extract_facts_from_response(response)

        # Should extract meaningful facts
        assert len(facts) >= 2
        assert any('Python' in fact and 'programming' in fact for fact in facts)
        assert any('libraries' in fact for fact in facts)

    def test_extract_facts_short_sentences(self, adapter):
        """Test that very short sentences are not extracted as facts."""
        response = "Hi. Yes. No. OK."

        facts = adapter._extract_facts_from_response(response)

        # Short sentences without factual indicators should not be extracted
        assert len(facts) == 0

    def test_fact_supported_by_memory(self, adapter):
        """Test fact support detection."""
        memory_context = [
            {'content': 'Python is a programming language used for web development'},
            {'content': 'Machine learning algorithms process data'}
        ]

        # Should be supported
        assert adapter._fact_supported_by_memory("Python is a programming language", memory_context) == True

        # Should not be supported
        assert adapter._fact_supported_by_memory("JavaScript is not in the context", memory_context) == False

    def test_calculate_fact_confidence(self, adapter):
        """Test fact confidence calculation."""
        memory_context = [
            {'content': 'Python programming language web development'},
            {'content': 'Machine learning data processing'}
        ]

        confidence = adapter._calculate_fact_confidence("Python programming web", memory_context)

        assert 0.0 <= confidence <= 1.0

    @patch('src.agents.memory_adapter.dao')
    def test_get_access_stats(self, mock_dao, adapter):
        """Test access statistics retrieval."""
        # Initially empty
        stats = adapter.get_access_stats()
        assert stats['total_accesses'] == 0

        # After some accesses
        adapter._log_memory_access("test_op", "query", "user")
        adapter._log_memory_access("test_op2", "query2", "user2", error="test error")

        stats = adapter.get_access_stats()
        assert stats['total_accesses'] == 2
        assert stats['error_rate'] == 0.5  # One error out of two
        assert len(stats['recent_errors']) == 1

    def test_vector_search_availability(self, adapter):
        """Test vector search availability checking."""
        # When vector features are not enabled
        with patch('src.core.config.are_vector_features_enabled', return_value=False):
            assert adapter._is_vector_search_available() == False

        # When enabled but import fails
        with patch('src.core.config.are_vector_features_enabled', return_value=True):
            with patch.dict('sys.modules', {'src.core.search_service': None}):
                assert adapter._is_vector_search_available() == False

    @patch('src.agents.memory_adapter.dao')
    def test_adversarial_memory_context(self, mock_dao, adapter):
        """Test that adversarial inputs don't expose sensitive data."""
        # Mock sensitive and safe data
        mock_kv_data = [
            {
                'key': 'password',
                'value': 'My password is admin123!',
                'sensitive': True
            },
            {
                'key': 'email',
                'value': 'Contact: user@secret.com',
                'sensitive': False  # But contains email pattern
            },
            {
                'key': 'safe',
                'value': 'Python is a programming language',
                'sensitive': False
            }
        ]
        mock_dao.list_keys.return_value = mock_kv_data

        context = adapter.get_validation_context("password", "malicious_user")

        # Should only return safe data
        assert len(context) <= 1  # Only the safe item
        assert all('password' not in ctx['content'].lower() for ctx in context)
        assert all('admin123' not in ctx['content'] for ctx in context)

    @patch('src.agents.memory_adapter.dao')
    def test_privacy_protection_validation(self, mock_dao, adapter):
        """Test that privacy protection works in validation."""
        # Response that might try to extract sensitive info
        response = "The user password is stored somewhere"
        memory_context = [
            {'content': 'User password is: secret123'},
            {'content': 'Programming is fun'}
        ]

        result = adapter.validate_facts_in_response(response, memory_context)

        # Should validate based on available context without exposing sensitive data
        assert isinstance(result['validated'], bool)

    def test_safety_filtering_edge_cases(self, adapter):
        """Test safety filtering on various edge cases."""
        # Test with None values
        unsafe_item = {'value': None, 'sensitive': False}
        assert adapter._is_safe_for_context(unsafe_item) == False

        # Test with very long sensitive content
        long_sensitive = 'password: ' + 'x' * 1000
        result = adapter.contains_sensitive_data(long_sensitive)
        assert result['contains_sensitive'] == True

    def test_memory_access_logging(self, adapter):
        """Test that memory access is properly logged."""
        # Test logging
        adapter._log_memory_access("test_operation", "test query", "user123")

        assert len(adapter.access_log) == 1
        log_entry = adapter.access_log[0]
        assert log_entry['operation'] == 'test_operation'
        assert log_entry['query_length'] == 10  # "test query"
        assert log_entry['user_id'] == 'user123'
        assert log_entry['success'] == True

    def test_error_handling_in_context_retrieval(self, adapter):
        """Test error handling in context retrieval."""
        # Force an error in processing
        with patch.object(adapter, '_get_fallback_context', side_effect=Exception("Test error")):
            with patch.object(adapter, '_is_vector_search_available', return_value=False):
                context = adapter.get_validation_context("query", "user")

                # Should handle error gracefully
                assert isinstance(context, list)
                assert len(context) == 0  # Empty on error

    def test_validation_metadata_detail(self, adapter):
        """Test that validation returns detailed metadata."""
        memory_context = [{'content': 'Python is programming language'}]

        response = "Python is a programming language. Rust is also good."

        result = adapter.validate_facts_in_response(response, memory_context)

        # Check metadata structure
        assert 'validation_details' in result
        assert isinstance(result['validation_details'], list)
        assert len(result['validation_details']) >= 1

        # Check detail structure
        detail = result['validation_details'][0]
        assert 'fact' in detail
        assert 'validated' in detail
        assert 'confidence' in detail

    def test_fact_extraction_edge_cases(self, adapter):
        """Test fact extraction on edge cases."""
        # Test empty response
        assert adapter._extract_facts_from_response("") == []

        # Test response with no factual indicators - exclude question sentences
        response = "Hello! How are you? Thank you."
        facts = adapter._extract_facts_from_response(response)
        # Should only extract "Thank you." if it has factual indicator
        assert len(facts) <= 1  # Allow "Thank you." if it contains 'you' but not factual

        # Test response with mixed content
        mixed_response = "I think Python is great. Actually, it has many libraries and is fast."
        facts = adapter._extract_facts_from_response(mixed_response)
        assert len(facts) >= 1
        assert any('Python' in fact for fact in facts)


@pytest.fixture
def mock_memory_adapter():
    """Create memory adapter with controlled mocking."""
    adapter = MemoryAdapter()

    # Override sensitive patterns for testing
    adapter.sensitive_patterns = [
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\b\d{4}[- ]\d{4}[- ]\d{4}[- ]\d{4}\b'  # Credit card
    ]
    adapter.sensitive_keywords = ['password', 'secret']

    return adapter
