"""
Stage 2: Test FAISS Vector Store Agent
Tests for semantic memory search using FAISS vector database.
"""

import pytest
import os
import tempfile
import numpy as np
from unittest.mock import MagicMock, patch
from src.agents.faiss_adapter import FaissRetriever
from src.agents.agent import AgentMessage


class TestFaissAdapter:
    """Test suite for FAISS vector retrieval agent."""

    def setup_method(self):
        """Setup before each test."""
        # Use temporary directory for tests
        self.temp_dir = tempfile.mkdtemp()
        self.index_file = os.path.join(self.temp_dir, "test_index.idx")
        self.metadata_file = os.path.join(self.temp_dir, "test_metadata.pkl")

    def teardown_method(self):
        """Cleanup after each test."""
        # Clean up test files
        for f in [self.index_file, self.metadata_file]:
            if os.path.exists(f):
                os.remove(f)
        os.rmdir(self.temp_dir)

    def test_faiss_initialization_without_embedding_model(self):
        """Test FAISS initialization with embedding model fallback."""
        # Mock the embedding model to test fallback behavior
        with patch('src.agents.faiss_adapter.SentenceTransformer') as mock_model:
            mock_model.side_effect = Exception("Model load failed")

            retriever = FaissRetriever("test_agent")
            assert retriever.embedding_model is None
            assert retriever.embedding_dim == 384  # Default dimension

    def test_ingest_chunk_basic(self):
        """Test basic chunk ingestion functionality."""
        retriever = FaissRetriever("test_agent")

        # Test successful ingestion
        success = retriever.ingest_chunk(
            text="This is a test memory chunk",
            metadata={"source": "test", "user_id": "test_user"}
        )

        assert success is True
        assert len(retriever.metadata_store) == 1
        assert retriever.metadata_store[0]["text"] == "This is a test memory chunk"

    def test_ingest_empty_chunk(self):
        """Test ingestion of empty or whitespace-only chunks."""
        retriever = FaissRetriever("test_agent")

        # Test empty string
        success = retriever.ingest_chunk("")
        assert success is False

        # Test whitespace only
        success = retriever.ingest_chunk("   ")
        assert success is False

        # Verify no chunks were added
        assert len(retriever.metadata_store) == 0

    def test_search_empty_index(self):
        """Test search on empty FAISS index."""
        retriever = FaissRetriever("test_agent")

        results = retriever.search("test query")
        assert results == []

    def test_search_with_ingested_data(self):
        """Test search after ingesting some data."""
        retriever = FaissRetriever("test_agent")

        # Create FAISS index mock
        mock_index = MagicMock()
        mock_index.ntotal = 1
        mock_index.search.return_value = (
            np.array([[0.5]]),  # distances
            np.array([[0]])    # indices
        )
        retriever.index = mock_index

        # Ingest a chunk
        retriever.ingest_chunk("The weather is nice today")

        # Mock numpy for the test
        with patch('src.agents.faiss_adapter.np') as mock_np:
            mock_np.random.randn.return_value = np.array([0.1] * 384, dtype=np.float32)
            mock_np.max.return_value = 1.0
            mock_np.linalg.norm.return_value = 1.0

            # Mock distances and similarities for controlled testing
            mock_np.array.side_effect = lambda x: np.array(x)
            mock_np.max.return_value = 1.0

            results = retriever.search("beautiful weather")

            # Verify search returns results
            assert len(results) == 1
            assert 'text' in results[0]
            assert 'score' in results[0]
            assert results[0]['text'] == "The weather is nice today"

    def test_process_message_integration(self):
        """Test full message processing flow."""
        retriever = FaissRetriever("test_agent")

        # Create mock agent message
        message = AgentMessage(
            content="What is machine learning?",
            role="user",
            timestamp="2024-01-01T12:00:00Z"
        )

        # Process the message
        response = retriever.process_message(message, [])

        # Verify response structure
        assert response.content is not None
        assert response.model_used.startswith("faiss-")
        assert isinstance(response.confidence, float)
        assert response.processing_time_ms >= 0
        assert response.metadata['agent_type'] == 'faiss_retriever'

    def test_get_status(self):
        """Test status reporting functionality."""
        retriever = FaissRetriever("test_agent")

        status = retriever.get_status()

        assert status['agent_type'] == 'faiss_retriever'
        assert 'vector_count' in status
        assert 'embedding_dimension' in status
        assert status['stage'] == 'stage_2_semantic_memory'

    def test_index_stats(self):
        """Test detailed index statistics."""
        retriever = FaissRetriever("test_agent")

        stats = retriever.get_index_stats()

        assert stats['implementation_status'] == 'active'
        assert stats['stage'] == 'stage_2_complete'
        assert 'vector_count' in stats
        assert 'dimensions' in stats
        assert stats['embedding_model'] == 'sentence-transformers'

    def test_rebuild_index(self):
        """Test index rebuild functionality."""
        retriever = FaissRetriever("test_agent")

        # Add some test data
        retriever.ingest_chunk("Test memory 1", {"id": 1})
        retriever.ingest_chunk("Test memory 2", {"id": 2})

        # Rebuild should succeed
        success = retriever.rebuild_index()
        assert success is True

    def test_error_handling(self):
        """Test error handling in various operations."""
        retriever = FaissRetriever("test_agent")

        # Test search with no index
        results = retriever.search("test query")
        assert results == []

        # Test ingest with None metadata (should handle gracefully)
        success = retriever.ingest_chunk("test text", None)
        assert success is True

        # Verify chunk was added despite None metadata
        assert len(retriever.metadata_store) == 1


class TestFaissAdapterIntegration:
    """Integration tests for FAISS adapter with actual dependencies."""

    @pytest.mark.skipif(not os.environ.get('RUN_INTEGRATION_TESTS'),
                       reason="Integration tests require RUN_INTEGRATION_TESTS=1")
    def test_with_real_embeddings(self):
        """Test with actual sentence-transformer embeddings (requires network)."""
        # This test is skipped by default to avoid network dependencies
        # Enable with RUN_INTEGRATION_TESTS=1 for full testing
        retriever = FaissRetriever("integration_test_agent")

        # Should load real embedding model
        assert retriever.embedding_model is not None
        assert retriever.embedding_dim > 0

        # Test real ingestion
        success = retriever.ingest_chunk("This is a real embedding test")
        assert success is True

        # Test real search
        results = retriever.search("embedding test")
        assert len(results) == 1

    @pytest.mark.skipif(not os.environ.get('RUN_FAISS_TESTS'),
                       reason="FAISS tests require RUN_FAISS_TESTS=1")
    def test_memory_operations(self):
        """Test memory operations and persistence."""
        # This would test saving/loading indexes
        # Enable with RUN_FAISS_TESTS=1
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
