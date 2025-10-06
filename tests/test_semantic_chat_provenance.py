"""
Stage 6: Semantic Chat Provenance Tests
Tests for semantic search provenance reporting in chat responses.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestSemanticChatProvenance:
    """Test semantic search provenance in chat responses."""

    def setup_method(self):
        """Setup before each test."""
        import src.core.config as config
        config.PRIVACY_ENFORCEMENT_ENABLED = True
        from src.core.privacy import configure_privacy_enforcement
        configure_privacy_enforcement(enabled=True)

    def teardown_method(self):
        """Cleanup after each test."""
        import src.core.config as config
        config.PRIVACY_ENFORCEMENT_ENABLED = False
        from src.core.privacy import configure_privacy_enforcement
        configure_privacy_enforcement(enabled=False)

    @pytest.mark.parametrize("enabled,sensitive_value,expected_prov", [
        (True, False, True),   # Privacy enabled, non-sensitive -> include provenance
        (True, True, True),    # Privacy enabled, sensitive -> include provenance
        (False, False, False), # Privacy disabled, non-sensitive -> no provenance
        (False, True, False),  # Privacy disabled, sensitive -> no provenance
    ])
    def test_vector_search_provenance_reporting(self, enabled, sensitive_value, expected_prov):
        """Test that semantic search includes provenance when privacy enforcement is enabled."""
        from src.core.search_service import semantic_search
        from src.core.dao import set_key

        # Set privacy configuration
        import src.core.config as config
        original_enabled = config.PRIVACY_ENFORCEMENT_ENABLED

        try:
            config.PRIVACY_ENFORCEMENT_ENABLED = enabled

            # Set up test data
            test_user = "test_user"
            test_key = "test_memory_key"
            test_value = "This is a test memory about hiking in the mountains."

            # Store test KV (non-sensitive for this test) - use external set_key to avoid normalization
            set_key(test_user, test_key, test_value, "test", "preserve", sensitive=sensitive_value)

            # Mock vector store and embedding provider
            mock_vector_store = MagicMock()
            mock_embedding_provider = MagicMock()
            mock_result = MagicMock()
            mock_result.id = test_key
            mock_result.score = 0.95
            mock_vector_store.search.return_value = [mock_result]
            mock_embedding_provider.embed_text.return_value = [0.1, 0.2, 0.3]

            # Perform search
            results = semantic_search(
                query="hiking mountains",
                top_k=5,
                _vector_store=mock_vector_store,
                _embedding_provider=mock_embedding_provider
            )

            if expected_prov:
                assert len(results) == 1
                assert "provenance" in results[0]
                provenance = results[0]["provenance"]
                assert "key" in provenance
                assert "source" in provenance
                assert "sensitive_level" in provenance
                assert "access_validated" in provenance
                assert "redacted" in provenance
                assert provenance["redacted"] == sensitive_value  # True if sensitive and not debug
            else:
                # No provenance should be included
                assert len(results) == 1
                assert "provenance" not in results[0]

        finally:
            config.PRIVACY_ENFORCEMENT_ENABLED = original_enabled

    @patch('src.core.privacy.validate_sensitive_access')
    def test_vector_search_provenance_access_validation(self, mock_validate):
        """Test vector search provenance includes access validation results."""
        from src.core.search_service import semantic_search
        from src.core.dao import set_key

        # Enable privacy enforcement
        import src.core.config as config
        original_enabled = config.PRIVACY_ENFORCEMENT_ENABLED

        try:
            config.PRIVACY_ENFORCEMENT_ENABLED = True

            # Mock access validation to return False (access denied)
            mock_validate.return_value = False

            # Set up test data with sensitive content
            test_user = "test_user"
            test_key = "sensitive_memory"
            test_value = "This contains sensitive API key information."

            set_key(test_user, test_key, test_value, "test", "preserve", sensitive=True)

            # Mock search components
            mock_vector_store = MagicMock()
            mock_embedding_provider = MagicMock()
            mock_result = MagicMock()
            mock_result.id = test_key
            mock_result.score = 0.85
            mock_vector_store.search.return_value = [mock_result]
            mock_embedding_provider.embed_text.return_value = [0.4, 0.5, 0.6]

            # Perform search
            results = semantic_search(
                query="API key",
                top_k=5,
                _vector_store=mock_vector_store,
                _embedding_provider=mock_embedding_provider
            )

            # Should have provenance with access validation
            assert len(results) == 1
            assert "provenance" in results[0]
            provenance = results[0]["provenance"]
            assert provenance["sensitive_level"] == "high"
            assert provenance["access_validated"] is False  # Our mock returned False

            # Verify validate_sensitive_access was called
            mock_validate.assert_called_with(
                accessor="semantic_search",
                data_type="vector_search_result",
                reason=f"Access to semantic search result with key {test_key}"
            )

        finally:
            config.PRIVACY_ENFORCEMENT_ENABLED = original_enabled

    def test_semantic_search_without_privacy_no_provenance(self):
        """Test that semantic search without privacy doesn't include provenance."""
        from src.core.search_service import semantic_search
        from src.core.dao import set_key

        # Ensure privacy is disabled
        import src.core.config as config
        original_enabled = config.PRIVACY_ENFORCEMENT_ENABLED

        try:
            config.PRIVACY_ENFORCEMENT_ENABLED = False

            # Set up test data
            test_user = "test_user"
            test_key = "test_memory_key"
            test_value = "This is a test memory about hiking."

            set_key(test_user, test_key, test_value, "test", "preserve", sensitive=False)

            # Mock search components
            mock_vector_store = MagicMock()
            mock_embedding_provider = MagicMock()
            mock_result = MagicMock()
            mock_result.id = test_key
            mock_result.score = 0.85
            mock_vector_store.search.return_value = [mock_result]
            mock_embedding_provider.embed_text.return_value = [0.1, 0.2, 0.3]

            # Perform search
            results = semantic_search(
                query="hiking",
                top_k=5,
                _vector_store=mock_vector_store,
                _embedding_provider=mock_embedding_provider
            )

            # Should not have provenance
            assert len(results) == 1
            assert "provenance" not in results[0]

        finally:
            config.PRIVACY_ENFORCEMENT_ENABLED = original_enabled

    def test_semantic_search_provenance_metadata_structure(self):
        """Test the structure of provenance metadata in semantic search."""
        from src.core.search_service import semantic_search
        from src.core.dao import set_key

        # Enable privacy
        import src.core.config as config
        original_enabled = config.PRIVACY_ENFORCEMENT_ENABLED

        try:
            config.PRIVACY_ENFORCEMENT_ENABLED = True

            # Set up test data
            test_key = "test_key"
            test_value = "Test value"
            set_key("test_user", test_key, test_value, "test", "preserve", sensitive=False)

            # Mock search
            mock_vector_store = MagicMock()
            mock_embedding_provider = MagicMock()
            mock_result = MagicMock()
            mock_result.id = test_key
            mock_result.score = 0.9
            mock_vector_store.search.return_value = [mock_result]
            mock_embedding_provider.embed_text.return_value = [0.1, 0.2, 0.3]

            results = semantic_search(
                query="test",
                top_k=5,
                _vector_store=mock_vector_store,
                _embedding_provider=mock_embedding_provider
            )

            # Verify provenance structure
            assert len(results) == 1
            assert "provenance" in results[0]
            prov = results[0]["provenance"]

            required_fields = ["key", "source", "sensitive_level", "access_validated", "redacted", "storage_mechanism", "retrieval_method"]
            for field in required_fields:
                assert field in prov

            assert prov["storage_mechanism"] == "vector_indexed_kv"
            assert prov["retrieval_method"] == "semantic_similarity"
            assert prov["access_validated"] is True  # Non-sensitive data

        finally:
            config.PRIVACY_ENFORCEMENT_ENABLED = original_enabled
