"""
Stage 2 scope only. Do not implement beyond this file's responsibilities.
Vector memory overlay - non-canonical, advisory layer over SQLite canonical truth.
"""

import pytest
from unittest.mock import MagicMock, patch
from scripts.rebuild_index import main
import os
import sys


@pytest.fixture
def mock_deps():
    """Mock dependencies for rebuild index testing."""
    with patch('scripts.rebuild_index.are_vector_features_enabled') as mock_enabled, \
         patch('scripts.rebuild_index.list_keys') as mock_list_keys, \
         patch('scripts.rebuild_index.get_vector_store') as mock_get_store, \
         patch('scripts.rebuild_index.get_embedding_provider') as mock_get_embed, \
         patch('scripts.rebuild_index.init_db') as mock_init_db:

        # Mock enabled
        mock_enabled.return_value = True

        # Mock KV pairs (some sensitive, some not)
        mock_kv_pairs = [
            MagicMock(key="normal_key", value="normal_value", source="test", casing="lower",
                     sensitive=False, updated_at=MagicMock(isoformat=lambda: "2025-01-26")),
            MagicMock(key="sensitive_key", value="secret_value", source="test", casing="upper",
                     sensitive=True, updated_at=MagicMock(isoformat=lambda: "2025-01-26")),
        ]
        mock_list_keys.return_value = mock_kv_pairs

        # Mock providers
        mock_vector_store = MagicMock()
        mock_embedding_provider = MagicMock()

        mock_get_store.return_value = mock_vector_store
        mock_get_embed.return_value = mock_embedding_provider

        # Mock embedding
        mock_embedding_provider.embed_text.return_value = [0.1] * 384

        yield {
            'vector_store': mock_vector_store,
            'embedding_provider': mock_embedding_provider,
            'kv_pairs': mock_kv_pairs,
        }


def test_rebuild_index_successful(capfd, mock_deps):
    """Test successful index rebuild."""
    # Run rebuild
    main()

    # Verify output
    captured = capfd.readouterr()
    assert "Starting vector index rebuild..." in captured.out
    assert "✓ Cleared existing vector index" in captured.out
    assert "Found 2 KV pairs in canonical store" in captured.out
    assert "Re-embedding 1 non-sensitive KV pairs" in captured.out
    assert "✓ Successfully rebuilt index with 1 vectors" in captured.out
    assert "✓ Verification search returned" in captured.out
    assert "Index rebuild complete!" in captured.out

    # Verify interactions
    mock_deps['vector_store'].clear.assert_called_once()

    # Should embed for content and verification
    assert mock_deps['embedding_provider'].embed_text.call_count == 2

    # First call: content embedding
    calls = mock_deps['embedding_provider'].embed_text.call_args_list
    assert "normal_key: normal_value" == calls[0][0][0]
    # Second call: verification
    assert "test" == calls[1][0][0]

    # Verify add called once
    mock_deps['vector_store'].add.assert_called_once()

    # Verify verification search
    mock_deps['vector_store'].search.assert_called_once_with([0.1] * 384, k=1)


def test_rebuild_index_no_vector_features(capfd):
    """Test rebuild exits early when vector features disabled."""
    with patch('scripts.rebuild_index.are_vector_features_enabled', return_value=False):
        with pytest.raises(SystemExit, match="1"):
            main()

        captured = capfd.readouterr()
        assert "ERROR: Vector features disabled" in captured.out


def test_rebuild_index_no_providers(capfd):
    """Test rebuild exits when providers unavailable."""
    with patch('scripts.rebuild_index.are_vector_features_enabled', return_value=True), \
         patch('scripts.rebuild_index.list_keys', return_value=[]), \
         patch('scripts.rebuild_index.get_vector_store', return_value=None), \
         patch('scripts.rebuild_index.get_embedding_provider', return_value=None):

        with pytest.raises(SystemExit, match="1"):
            main()

        captured = capfd.readouterr()
        assert "ERROR: Vector store or embedding provider not available" in captured.out


def test_rebuild_index_clear_failure(capfd, mock_deps):
    """Test rebuild continues despite clear failure."""
    mock_deps['vector_store'].clear.side_effect = Exception("Clear failed")

    # Should not raise
    main()

    captured = capfd.readouterr()
    assert "WARNING: Failed to clear existing index: Clear failed" in captured.out
    assert "✓ Successfully rebuilt index with 1 vectors" in captured.out


def test_rebuild_index_empty_kv(capfd):
    """Test rebuild with empty KV store."""
    with patch('scripts.rebuild_index.are_vector_features_enabled', return_value=True), \
         patch('scripts.rebuild_index.list_keys', return_value=[]), \
         patch('scripts.rebuild_index.get_vector_store') as mock_get_store, \
         patch('scripts.rebuild_index.get_embedding_provider') as mock_get_embed:

        mock_vector_store = MagicMock()
        mock_embedding_provider = MagicMock()
        mock_get_store.return_value = mock_vector_store
        mock_get_embed.return_value = mock_embedding_provider

        main()

        captured = capfd.readouterr()
        assert "Found 0 KV pairs in canonical store" in captured.out
        assert "No entries to rebuild. Exiting." in captured.out


def test_rebuild_index_embed_failure(capfd, mock_deps):
    """Test rebuild continues despite embedding failure."""
    # Make embedding fail on first call
    mock_deps['embedding_provider'].embed_text.side_effect = [Exception("Embed failed"), [0.1] * 384]

    main()

    captured = capfd.readouterr()
    assert "ERROR: Failed to embed KV pair normal_key: Embed failed" in captured.out
    # Should still succeed with 0 entries (since processing fails)
    assert "✓ Successfully rebuilt index with 0 vectors" in captured.out


def test_rebuild_index_verification_failure(capfd, mock_deps):
    """Test rebuild completes despite verification failure."""
    mock_deps['vector_store'].search.side_effect = Exception("Search failed")

    main()

    captured = capfd.readouterr()
    assert "✓ Successfully rebuilt index with 1 vectors" in captured.out
    assert "WARNING: Verification search failed: Search failed" in captured.out
