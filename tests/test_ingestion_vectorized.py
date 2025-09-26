"""
Stage 2 scope only. Do not implement beyond this file's responsibilities.
Vector memory overlay - non-canonical, advisory layer over SQLite canonical truth.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.core.dao import set_key, delete_key, get_key
from src.core.config import get_vector_store, get_embedding_provider


class TestVectorIngestionIntegration:
    """Integration tests for vector ingestion wiring in DAO operations."""

    def test_stage_1_behavior_preserved_when_vectors_disabled(self):
        """Stage 1 smoke tests should pass unchanged with VECTOR_ENABLED=false."""
        # Disable vector features to ensure Stage 1 behavior is preserved
        with patch('src.core.config.are_vector_features_enabled', return_value=False):
            # Set up test data (these operations should work as in Stage 1)
            test_key = "stage1_test_key"
            test_value = "stage1_test_value"

            # Should work without any vector operations
            success = set_key(test_key, test_value, "test", "lowercase")
            assert success == True

            result = get_key(test_key)
            assert result is not None
            assert result.key == test_key
            assert result.value == test_value
            assert result.source == "test"
            assert result.casing == "lowercase"

            # Clean up
            delete_key(test_key)
            cleaned = get_key(test_key)
            assert cleaned is not None
            assert cleaned.value == ""  # Tombstone

    @patch('src.core.dao.get_vector_store')
    @patch('src.core.dao.get_embedding_provider')
    def test_vector_ingestion_enabled_non_sensitive_key(self, mock_embedding_provider, mock_vector_store):
        """When vector features enabled, non-sensitive keys should be stored in vector index."""
        # Mock the vector provider to return a working store
        mock_store = MagicMock()
        mock_provider = MagicMock()

        mock_vector_store.return_value = mock_store
        mock_embedding_provider.return_value = mock_provider

        # Mock embedding generation
        test_embedding = [0.1, 0.2, 0.3, 0.4]  # Simple test embedding
        mock_provider.embed_text.return_value = test_embedding

        # Test setting a non-sensitive key
        test_key = "vector_test_key"
        test_value = "vector test value"

        result = set_key(test_key, test_value, "test_source", "lowercase", sensitive=False)

        assert result == True

        # Verify vector operations were called
        mock_vector_store.assert_called_once()
        mock_embedding_provider.assert_called_once()

        # Verify the content to embed includes key and value
        expected_content = f"{test_key}: {test_value}"
        mock_provider.embed_text.assert_called_once_with(expected_content)

        # Verify vector record was created and added
        mock_store.add.assert_called_once()

        # Check the vector record passed to add method
        vector_record_call = mock_store.add.call_args[0][0]
        assert vector_record_call.id == test_key
        assert vector_record_call.vector == test_embedding
        assert vector_record_call.metadata["source"] == "test_source"
        assert vector_record_call.metadata["casing"] == "lowercase"

        # Clean up
        delete_key(test_key)

    @patch('src.core.dao.get_vector_store')
    @patch('src.core.dao.get_embedding_provider')
    def test_vector_ingestion_skipped_for_sensitive_keys(self, mock_embedding_provider, mock_vector_store):
        """Sensitive keys should never be embedded or stored in vector index."""
        # Set up mocks (but they should not be called)
        mock_store = MagicMock()
        mock_provider = MagicMock()

        mock_vector_store.return_value = mock_store
        mock_embedding_provider.return_value = mock_provider

        # Test setting a sensitive key
        test_key = "sensitive_test_key"
        test_value = "sensitive test value"

        result = set_key(test_key, test_value, "test_source", "lowercase", sensitive=True)

        assert result == True

        # Verify vector operations were NOT called
        mock_vector_store.assert_not_called()
        mock_embedding_provider.assert_not_called()
        mock_store.add.assert_not_called()

        # Clean up
        delete_key(test_key)

    @patch('src.core.dao.get_vector_store')
    def test_vector_deletion_on_tombstone(self, mock_vector_store):
        """When keys are tombstoned, they should be removed from vector index."""
        # First, create a key with vector operations enabled
        mock_store = MagicMock()
        mock_provider = MagicMock()
        test_embedding = [0.1, 0.2, 0.3, 0.4]

        with patch('src.core.dao.get_embedding_provider', return_value=mock_provider):
            with patch('src.core.dao.get_vector_store', return_value=mock_store):
                mock_provider.embed_text.return_value = test_embedding

                # Set up the key
                test_key = "delete_test_key"
                test_value = "delete test value"
                set_key(test_key, test_value, "test_source", "lowercase", sensitive=False)

                # Clear mocks to check delete behavior
                mock_store.reset_mock()

                # Delete the key (tombstone)
                result = delete_key(test_key)
                assert result == True

                # Verify the key exists but with empty value (tombstone)
                tombstone = get_key(test_key)
                assert tombstone is not None
                assert tombstone.value == ""

                # Verify vector deletion was attempted
                mock_vector_store.assert_called()
                mock_store.delete.assert_called_once_with(test_key)

    @patch('src.core.dao.get_vector_store')
    def test_vector_update_operations(self, mock_vector_store):
        """Updating existing keys should handle vector index updates correctly."""
        # Mock the vector store and embedding provider
        mock_store = MagicMock()
        mock_provider = MagicMock()
        test_embedding = [0.1, 0.2, 0.3, 0.4]
        updated_embedding = [0.5, 0.6, 0.7, 0.8]

        with patch('src.core.dao.get_embedding_provider', return_value=mock_provider):
            with patch('src.core.dao.get_vector_store', return_value=mock_store):

                # Initial embedding
                mock_provider.embed_text.return_value = test_embedding

                test_key = "update_test_key"
                # Create initial key
                set_key(test_key, "initial value", "test_source", "lowercase", sensitive=False)

                # Verify initial add
                assert mock_store.add.call_count == 1

                # Clear mocks and set up for update
                mock_store.reset_mock()
                mock_store.delete.side_effect = None  # Allow deletion calls
                mock_provider.embed_text.return_value = updated_embedding

                # Update the key
                set_key(test_key, "updated value", "test_source", "lowercase", sensitive=False)

                # Verify delete was attempted for update (FAISS doesn't support updates)
                assert mock_store.delete.call_count == 1
                mock_store.delete.assert_called_with(test_key)

                # Verify add was called again for the update
                assert mock_store.add.call_count == 1

                # Clean up
                delete_key(test_key)

    @patch('src.core.dao.get_vector_store')
    def test_vector_operations_isolated_from_sqlite_failures(self, mock_vector_store):
        """Vector operations failing should never break SQLite functionality."""
        # Mock vector store to always raise an exception
        mock_store = MagicMock()
        mock_provider = MagicMock()
        test_embedding = [0.1, 0.2, 0.3, 0.4]

        with patch('src.core.dao.get_embedding_provider', return_value=mock_provider):
            with patch('src.core.dao.get_vector_store', return_value=mock_store):
                mock_provider.embed_text.return_value = test_embedding
                mock_store.delete.side_effect = Exception("Vector store error")
                mock_store.add.side_effect = Exception("Vector store error")

                # Operations should still succeed despite vector failures
                test_key = "isolation_test_key"
                result = set_key(test_key, "test value", "test_source", "lowercase", sensitive=False)
                assert result == True  # SQLite should succeed

                # Verify key was still set
                check = get_key(test_key)
                assert check is not None
                assert check.value == "test value"

                # Clean up should also succeed
                delete_result = delete_key(test_key)
                assert delete_result == True

                # Verify tombstone
                tombstone = get_key(test_key)
                assert tombstone is not None
                assert tombstone.value == ""


if __name__ == "__main__":
    pytest.main([__file__])
