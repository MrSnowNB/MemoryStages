"""
Stage 2: FAISS Vector Store Agent
Semantic memory search using FAISS for fuzzy/semantic recall.
"""

import os
import pickle
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from .agent import BaseAgent, AgentMessage, AgentResponse
from ..core.config import debug_enabled, get_vector_store
from datetime import datetime

# Try to import sentence-transformers, fallback gracefully
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("DEBUG: sentence-transformers not available, using random embeddings for testing")


class FaissRetriever(BaseAgent):
    """
    FAISS-based vector retrieval agent for semantic search on ingested memories.

    Provides fuzzy/semantic recall by:
    - Converting text chunks to vector embeddings
    - Storing vectors in FAISS index for fast similarity search
    - Retrieving top-k most similar chunks for user queries
    - Maintaining metadata association for retrieved results
    """

    def __init__(self, agent_id: str = "faiss_retriever", embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize FAISS retriever with embedding model.

        Args:
            agent_id: Unique agent identifier
            embedding_model: SentenceTransformers model name for embeddings
        """
        super().__init__(agent_id, model_name=f"faiss-{embedding_model}")

        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer(embedding_model)
            self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
            print(f"DEBUG: FAISS embedding model loaded: {embedding_model} (dim: {self.embedding_dim})")
        except Exception as e:
            print(f"DEBUG: Failed to load embedding model {embedding_model}: {e}")
            # Fallback to basic implementation for testing
            self.embedding_model = None
            self.embedding_dim = 384  # Default for all-MiniLM-L6-v2

        # Initialize FAISS index (lazy load)
        self.index = None
        self.index_file = os.path.join(os.path.dirname(__file__), "../../data/faiss_index.idx")

        # Metadata storage
        self.metadata_store = []
        self.metadata_file = os.path.join(os.path.dirname(__file__), "../../data/faiss_metadata.pkl")

        # Load existing index if available
        self._load_index()

    def _ensure_index(self):
        """Lazy initialization of FAISS index."""
        if self.index is None:
            try:
                import faiss
                self.index = faiss.IndexFlatL2(self.embedding_dim)
                print(f"DEBUG: Initialized FAISS index with dimension {self.embedding_dim}")
            except ImportError:
                raise RuntimeError("FAISS not installed. Run: pip install faiss-cpu")

    def _load_index(self):
        """Load existing FAISS index and metadata from disk."""
        try:
            if os.path.exists(self.index_file):
                import faiss
                self.index = faiss.read_index(self.index_file)
                print(f"DEBUG: Loaded FAISS index with {self.index.ntotal} vectors")
            else:
                print("DEBUG: No existing FAISS index found, will create new one")

            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'rb') as f:
                    self.metadata_store = pickle.load(f)
                print(f"DEBUG: Loaded {len(self.metadata_store)} metadata entries")
            else:
                print("DEBUG: No existing metadata found")

        except Exception as e:
            print(f"DEBUG: Failed to load existing index: {e}")
            self.index = None
            self.metadata_store = []

    def _save_index(self):
        """Save FAISS index and metadata to disk."""
        try:
            os.makedirs(os.path.dirname(self.index_file), exist_ok=True)

            if self.index is not None:
                import faiss
                faiss.write_index(self.index, self.index_file)
                print(f"DEBUG: Saved FAISS index with {self.index.ntotal} vectors")

            if self.metadata_store:
                with open(self.metadata_file, 'wb') as f:
                    pickle.dump(self.metadata_store, f)
                print(f"DEBUG: Saved {len(self.metadata_store)} metadata entries")

        except Exception as e:
            print(f"DEBUG: Failed to save index: {e}")

    def ingest_chunk(self, text: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Convert text chunk to vector and add to FAISS index.

        Args:
            text: Text content to ingest
            metadata: Associated metadata (source, timestamp, user_id, etc.)

        Returns:
            True if successfully ingested, False otherwise
        """
        try:
            if not text or not text.strip():
                return False

            # Ensure index is initialized
            self._ensure_index()

            # Generate embedding
            if self.embedding_model:
                vector = self.embedding_model.encode(text, convert_to_numpy=True)
            else:
                # Fallback for testing - random vector
                vector = np.random.randn(self.embedding_dim).astype(np.float32)

            # Add to FAISS index
            vector_reshaped = vector.reshape(1, -1)
            self.index.add(vector_reshaped)

            # Store metadata
            chunk_metadata = metadata or {}
            chunk_metadata.update({
                'text': text,
                'ingested_at': datetime.now().isoformat(),
                'vector_norm': float(np.linalg.norm(vector)),
                'text_length': len(text)
            })
            self.metadata_store.append(chunk_metadata)

            # Save periodically (every 100 chunks)
            if len(self.metadata_store) % 100 == 0:
                self._save_index()

            if debug_enabled():
                print(f"DEBUG: Ingested chunk: '{text[:50]}...' (vector shape: {vector.shape})")

            return True

        except Exception as e:
            print(f"DEBUG: Failed to ingest chunk: {e}")
            return False

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for most similar text chunks to the query.

        Args:
            query: Search query string
            top_k: Number of top results to return

        Returns:
            List of dicts with 'text', 'metadata', 'score', 'index' keys
        """
        try:
            if not query or not query.strip():
                return []

            if not self.index or self.index.ntotal == 0:
                print("DEBUG: FAISS index empty or not initialized")
                return []

            # Generate query embedding
            if self.embedding_model:
                query_vector = self.embedding_model.encode(query, convert_to_numpy=True)
            else:
                # Fallback for testing - random vector
                query_vector = np.random.randn(self.embedding_dim).astype(np.float32)

            # Search FAISS index
            query_reshaped = query_vector.reshape(1, -1)
            distances, indices = self.index.search(query_reshaped, min(top_k, self.index.ntotal))

            # Convert to cosine similarity scores (lower distance = higher similarity)
            # distances are L2 squared distances, convert to similarity scores
            max_distance = np.max(distances) if distances.size > 0 else 1.0
            similarities = 1.0 - (distances / (max_distance + 1e-6))  # Normalize to [0, 1]

            results = []
            for i, (distance, similarity, idx) in enumerate(zip(distances[0], similarities[0], indices[0])):
                if idx < len(self.metadata_store):
                    metadata = self.metadata_store[idx].copy()
                    text = metadata.pop('text', '')

                    result = {
                        'text': text,
                        'metadata': metadata,
                        'score': float(similarity),
                        'distance': float(distance),
                        'index': int(idx),
                        'rank': i + 1
                    }
                    results.append(result)

            if debug_enabled():
                print(f"DEBUG: Search query '{query[:30]}...' returned {len(results)} results")

            return results

        except Exception as e:
            print(f"DEBUG: Search failed: {e}")
            return []

    def process_message(self, message: AgentMessage, context: List[AgentMessage]) -> AgentResponse:
        """
        Process a message by searching for semantically similar memories.

        Args:
            message: User message containing search query
            context: Previous conversation context (not used by FAISS)

        Returns:
            AgentResponse with search results
        """
        start_time = datetime.now()

        try:
            query = message.content.strip()

            # Perform semantic search
            search_results = self.search(query, top_k=5)

            # Format response
            if not search_results:
                response_text = f"No semantic memories found for query: '{query}'"
                confidence = 0.1
            else:
                # Construct response with top matches
                response_lines = [f"Semantic search results for: '{query}'"]
                total_score = 0.0

                for result in search_results[:3]:  # Top 3 results
                    score_pct = int(result['score'] * 100)
                    text_preview = result['text'][:100] + "..." if len(result['text']) > 100 else result['text']
                    response_lines.append(f"• {score_pct}% match: {text_preview}")
                    total_score += result['score']

                response_text = "\n".join(response_lines)
                confidence = min(total_score / len(search_results), 0.9)  # Average confidence

            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return AgentResponse(
                content=response_text,
                model_used=self.model_name,
                confidence=confidence,
                tool_calls=[],
                processing_time_ms=processing_time,
                metadata={
                    'agent_type': 'faiss_retriever',
                    'agent_id': self.agent_id,
                    'results_count': len(search_results),
                    'query': query
                },
                audit_info={
                    'search_type': 'semantic',
                    'top_k_requested': 5,
                    'results_returned': len(search_results),
                    'query_length': len(query)
                }
            )

        except Exception as e:
            error_msg = f"FAISS search error: {str(e)}"
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return AgentResponse(
                content=error_msg,
                model_used=self.model_name,
                confidence=0.0,
                tool_calls=[],
                processing_time_ms=processing_time,
                metadata={'error': str(e), 'agent_type': 'faiss_retriever'},
                audit_info={'error_occurred': True}
            )

    def get_status(self) -> Dict[str, Any]:
        """Get current status with FAISS-specific information."""
        status = super().get_status()
        status.update({
            'vector_count': self.index.ntotal if self.index else 0,
            'embedding_dimension': self.embedding_dim,
            'embedding_model': 'sentence-transformers',
            'metadata_entries': len(self.metadata_store),
            'index_size_mb': self._get_index_size_mb(),
            'stage': 'stage_2_semantic_memory'
        })
        return status

    def _get_index_size_mb(self) -> float:
        """Get approximate size of FAISS index in MB."""
        try:
            if self.index and os.path.exists(self.index_file):
                size_bytes = os.path.getsize(self.index_file)
                return round(size_bytes / (1024 * 1024), 2)
        except Exception:
            pass
        return 0.0

    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get detailed statistics about the current FAISS index.

        Returns:
            Dict with comprehensive index statistics
        """
        return {
            'implementation_status': 'active',
            'stage': 'stage_2_complete',
            'vector_count': self.index.ntotal if self.index else 0,
            'dimensions': self.embedding_dim,
            'embedding_model': 'sentence-transformers',
            'metadata_entries': len(self.metadata_store),
            'index_file_exists': os.path.exists(self.index_file),
            'metadata_file_exists': os.path.exists(self.metadata_file),
            'index_size_mb': self._get_index_size_mb(),
            'is_metric_l2': hasattr(self.index, 'metric_type') if self.index else False,
            'supports_deletion': False,  # FAISS IndexFlatL2 doesn't support deletion
            'last_ingested': self.metadata_store[-1].get('ingested_at') if self.metadata_store else None
        }

    def rebuild_index(self) -> bool:
        """
        Rebuild FAISS index from current metadata store.
        Useful for maintenance or after corruption.

        Returns:
            True if rebuild successful, False otherwise
        """
        try:
            print(f"DEBUG: Rebuilding FAISS index from {len(self.metadata_store)} chunks...")

            # Create new index
            self._ensure_index()
            new_index = type(self.index)()  # Create same type of index

            # Re-ingest all chunks
            successful_ingests = 0
            for metadata in self.metadata_store:
                text = metadata.get('text', '')
                if text and self.ingest_chunk(text, metadata):
                    successful_ingests += 1

            # Save rebuilt index
            self._save_index()

            print(f"DEBUG: Index rebuild complete: {successful_ingests}/{len(self.metadata_store)} chunks")
            return successful_ingests == len(self.metadata_store)

        except Exception as e:
            print(f"DEBUG: Index rebuild failed: {e}")
            return False

    def __del__(self):
        """Save index on destruction."""
        try:
            self._save_index()
        except Exception:
            pass  # Silent cleanup
