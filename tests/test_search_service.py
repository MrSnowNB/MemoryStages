"""
Stage 2 scope only. Do not implement beyond this file's responsibilities.
Vector memory overlay - non-canonical, advisory layer over SQLite canonical truth.
"""

import pytest
from unittest.mock import MagicMock
from src.core.search_service import semantic_search
from src.core.dao import set_key, get_key, delete_key, list_keys
from src.core.db import init_db
import os


@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment for search service."""
    # Set vector features enabled
    os.environ["VECTOR_ENABLED"] = "true"
    os.environ["VECTOR_PROVIDER"] = "memory"
    os.environ["EMBED_PROVIDER"] = "hash"
    os.environ["DEBUG"] = "false"

    # Initialize database
    init_db()

    # Clear any existing data
    existing_keys = list_keys()
    for kv in existing_keys:
        delete_key(kv.key)


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    store = MagicMock()
    # Simulate search returning results for known keys
    store.search.return_value = [
        MagicMock(id="hello", score=0.9, metadata={}),
        MagicMock(id="foo", score=0.8, metadata={}),
        MagicMock(id="tombstoned", score=0.7, metadata={}),
    ]
    return store


@pytest.fixture
def mock_embedding_provider():
    """Mock embedding provider for testing."""
    embedder = MagicMock()
    # Return a mock embedding vector
    embedder.embed_text.return_value = [0.1] * 384  # 384-dim for hash
    return embedder


def test_semantic_search_basic():
    """Test basic semantic search functionality."""
    # Set up test data
    set_key("hello", "world", "test_source", "upper")
    set_key("foo", "bar", "test_source", "lower")

    # Mock providers
    vector_store = MagicMock()
    embedding_provider = MagicMock()

    embedding_provider.embed_text.return_value = [0.1] * 384
    vector_results = [
        MagicMock(id="hello", score=0.9, metadata={}),
        MagicMock(id="foo", score=0.8, metadata={}),
    ]
    vector_store.search.return_value = vector_results

    os.environ["VECTOR_ENABLED"] = "true"

    results = semantic_search("test query", top_k=5, _vector_store=vector_store, _embedding_provider=embedding_provider)

    assert len(results) == 2
    # Check first result
    hello_result = next(r for r in results if r["key"] == "hello")
    assert hello_result["value"] == "world"
    assert hello_result["score"] == 0.9
    foo_result = next(r for r in results if r["key"] == "foo")
    assert foo_result["value"] == "bar"
    assert foo_result["score"] == 0.8


def test_semantic_search_filters_tombstones():
    """Test that semantic search filters out tombstoned entries."""
    # Set up test data
    set_key("active", "value", "test_source", "upper")
    set_key("tombstoned", "value", "test_source", "upper")
    delete_key("tombstoned")  # Create tombstone

    # Mock providers
    vector_store = MagicMock()
    embedding_provider = MagicMock()

    embedding_provider.embed_text.return_value = [0.1] * 384
    # Return results including tombstoned key
    vector_results = [
        MagicMock(id="active", score=0.9, metadata={}),
        MagicMock(id="tombstoned", score=0.8, metadata={}),
    ]
    vector_store.search.return_value = vector_results

    os.environ["VECTOR_ENABLED"] = "true"

    results = semantic_search("test query", top_k=5, _vector_store=vector_store, _embedding_provider=embedding_provider)

    # Only active key should be included
    assert len(results) == 1
    assert results[0]["key"] == "active"
    assert results[0]["value"] == "value"


def test_semantic_search_redacts_sensitive():
    """Test that semantic search redacts sensitive data when DEBUG=false."""
    # Set up test data
    set_key("sensitive_key", "secret_value", "test_source", "upper", sensitive=True)
    set_key("normal_key", "normal_value", "test_source", "upper", sensitive=False)

    # Mock providers
    vector_store = MagicMock()
    embedding_provider = MagicMock()

    embedding_provider.embed_text.return_value = [0.1] * 384
    vector_results = [
        MagicMock(id="sensitive_key", score=0.9, metadata={}),
        MagicMock(id="normal_key", score=0.8, metadata={}),
    ]
    vector_store.search.return_value = vector_results

    os.environ["VECTOR_ENABLED"] = "true"

    results = semantic_search("test query", top_k=5, _vector_store=vector_store, _embedding_provider=embedding_provider)

    assert len(results) == 2

    # Sensitive should be redacted
    sensitive_result = next(r for r in results if r["key"] == "sensitive_key")
    assert sensitive_result["value"] == "***"

    # Normal should not be redacted
    normal_result = next(r for r in results if r["key"] == "normal_key")
    assert normal_result["value"] == "normal_value"


def test_semantic_search_disabled_features():
    """Test semantic search returns empty when vector features disabled."""
    os.environ["VECTOR_ENABLED"] = "false"

    results = semantic_search("test query")
    assert results == []


def test_semantic_search_no_providers():
    """Test semantic search returns empty when providers are None."""
    results = semantic_search("test query", _vector_store=None)
    assert results == []
