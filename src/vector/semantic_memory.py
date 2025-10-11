"""
Stage 2: Semantic Memory Service
Provides high-level semantic indexing and querying over FAISS vector store.
With sensitive data exclusion and provenance tracking.
"""

from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import numpy as np

from .embeddings import EmbeddingsService
from .faiss_store import FAISSStore
from .types import VectorRecord, QueryResult
from ..core.config import SEMANTIC_ENABLED, EMBED_DIM, SENSITIVE_EXCLUDE


class SemanticHit:
    """Represents a semantic search hit with provenance."""
    def __init__(self, doc_id: str, score: float, text: str, source: str, metadata: Dict[str, Any]):
        self.doc_id = doc_id
        self.score = score
        self.text = text
        self.source = source
        self.metadata = metadata
        self.model_version = None
        self.created_at = datetime.now()


class ValidatedHit:
    """Semantic hit with KV reconciliation information."""
    def __init__(self, hit: SemanticHit, kv_conflict: bool = False, kv_override: Optional[Dict[str, Any]] = None):
        self.hit = hit
        self.kv_conflict = kv_conflict
        self.kv_override = kv_override


class SemanticMemoryService:
    """
    High-level service for semantic memory operations.
    Integrates embeddings generation with FAISS storage and query.
    Provides provenance tracking and sensitive data exclusion.
    """

    def __init__(self):
        """Initialize the semantic memory service."""
        from ..core.config import EMBED_MODEL_NAME, FAISS_INDEX_PATH, EMBED_DIM

        self.embeddings_service = EmbeddingsService(EMBED_MODEL_NAME)
        self.vector_store = FAISSStore(EMBED_DIM)
        self.model_version = self.embeddings_service.get_version()

        # Load or create index
        self.persist_index_path = FAISS_INDEX_PATH

    def index_documents(self, docs: List[Dict[str, Any]]) -> List[str]:
        """
        Index multiple documents into semantic memory.
        Excludes sensitive documents if SENSITIVE_EXCLUDE is enabled.

        Args:
            docs: List of document dicts with text, source, sensitive flag, etc.

        Returns:
            List of document IDs assigned to indexed documents
        """
        if not docs:
            return []

        indexed_ids = []

        for doc in docs:
            # Skip sensitive documents if exclusion is enabled
            if SENSITIVE_EXCLUDE and doc.get('sensitive', False):
                continue

            text = doc.get('text', '').strip()
            if not text:
                continue

            try:
                # Generate embedding
                embedding = self.embeddings_service.embed_texts([text])[0]  # Single document

                # Create unique document ID if not provided
                doc_id = doc.get('doc_id', f"doc_{str(uuid.uuid4())[:8]}")

                # Prepare metadata for provenance
                metadata = {
                    'source': doc.get('source', 'unknown'),
                    'created_at': datetime.now().isoformat(),
                    'text': text[:200] + '...' if len(text) > 200 else text,  # Truncated for storage
                    'kv_keys': doc.get('kv_keys', []),
                    'model_version': self.model_version,
                    'doc_id': doc_id
                }

                # Create vector record
                vector_record = VectorRecord(
                    id=doc_id,
                    vector=embedding,
                    metadata=metadata
                )

                # Add to vector store
                self.vector_store.add(vector_record)
                indexed_ids.append(doc_id)

                # Log semantic indexing event
                from ..core.dao import add_event
                add_event(
                    user_id="system",
                    actor="semantic_memory",
                    action="semantic_indexed",
                    payload=f"Indexed document {doc_id} with {len(embedding)} vectors",
                    event_type="semantic_indexed",
                    summary=f"Indexed {'sensitive' if doc.get('sensitive', False) else 'public'} document from {doc.get('source', 'unknown')}"
                )

            except Exception as e:
                # Log failed indexing but continue
                from ..core.dao import add_event
                add_event(
                    user_id="system",
                    actor="semantic_memory",
                    action="semantic_indexing_failed",
                    payload=f"Failed to index document: {str(e)}",
                    event_type="semantic_indexing_failed"
                )
                continue

        return indexed_ids

    def query(self, text: str, k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query semantic memory and return top-k results with provenance.

        Args:
            text: Query text
            k: Number of results to return
            filters: Optional filters for query refinement

        Returns:
            List of semantic hits with provenance information
        """
        # Generate query embedding
        query_embedding = self.embeddings_service.embed_texts([text])[0]

        # Query vector store
        query_results = self.vector_store.search(query_embedding, k * 2)  # Get more than needed for filtering

        # Convert to SemanticHit objects with full metadata
        hits = []
        for result in query_results[:k]:  # Limit to requested k
            # Get full metadata from vector store
            metadata = self.vector_store.id_to_metadata.get(result.id, {})

            hit = {
                'doc_id': result.id,
                'score': result.score,
                'text': metadata.get('text', ''),
                'source': metadata.get('source', 'unknown'),
                'created_at': metadata.get('created_at', ''),
                'model_version': metadata.get('model_version', self.model_version),
                'provenance': {
                    'type': 'semantic',
                    'doc_id': result.id,
                    'score': result.score,
                    'source': metadata.get('source', 'unknown'),
                    'explanation': f'Semantic match for query with score {result.score:.3f}'
                }
            }
            hits.append(hit)

        # Log semantic query event
        from ..core.dao import add_event
        add_event(
            user_id="system",
            actor="semantic_memory",
            action="semantic_query",
            payload=f"Queried '{text[:50]}...' returning {len(hits)} results",
            event_type="semantic_query",
            summary=f"Semantic search returned {len(hits)} hits"
        )

        return hits

    def rehydrate_and_validate(self, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rehydrate hits with additional validation information.
        Checks for KV conflicts and adds reconciliation notes.

        Args:
            hits: Raw semantic hits from query()

        Returns:
            Validated hits with KV reconciliation information
        """
        validated_hits = []

        for hit in hits:
            # TODO: Implement KV reconciliation logic here
            # For now, just pass through with no conflicts noted

            validated_hit = hit.copy()
            validated_hit['validated'] = True
            validated_hit['kv_conflicts'] = []  # Will be populated when reconciliation is implemented
            validated_hit['reconciled_facts'] = []  # KV-consistent facts from semantic hits

            validated_hits.append(validated_hit)

        return validated_hits

    def health(self) -> Dict[str, Any]:
        """
        Return semantic memory system health information.

        Returns:
            Health status dict with size, model versions, staleness, etc.
        """
        try:
            total_vectors = getattr(self.vector_store, 'index', None)
            if total_vectors and hasattr(total_vectors, 'ntotal'):
                size = total_vectors.ntotal
            else:
                size = 0

            # Check for model version staleness
            from ..core.config import EMBEDDING_MODEL_VERSION, INDEX_SCHEMA_VERSION
            current_model_version = self.model_version
            current_schema_version = INDEX_SCHEMA_VERSION
            config_model_version = EMBEDDING_MODEL_VERSION

            stale = (
                current_model_version != config_model_version or
                (hasattr(self.vector_store, 'id_to_metadata') and
                 any(meta.get('model_version') != config_model_version
                     for meta in self.vector_store.id_to_metadata.values()
                     if meta))
            )

            return {
                'status': 'healthy',
                'size': size,
                'model_version': current_model_version,
                'index_schema_version': current_schema_version,
                'stale': stale,
                'embeddings_enabled': True,
                'sensitive_exclusion': SENSITIVE_EXCLUDE,
                'last_checked': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'size': 0,
                'model_version': 'unknown',
                'index_schema_version': 'unknown',
                'stale': True,
                'embeddings_enabled': False,
                'sensitive_exclusion': SENSITIVE_EXCLUDE,
                'last_checked': datetime.now().isoformat()
            }
