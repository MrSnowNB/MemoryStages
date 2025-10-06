"""
Stage 2 scope only. Do not implement beyond this file's responsibilities.
Vector memory overlay - non-canonical, advisory layer over SQLite canonical truth.
"""

from typing import List, Dict, Any, Optional
from .config import get_vector_store, get_embedding_provider, are_vector_features_enabled, debug_enabled, PRIVACY_ENFORCEMENT_ENABLED
from .dao import get_key

# Import privacy enforcement for provenance reporting (Stage 6)
try:
    from .privacy import validate_sensitive_access
except ImportError:
    def validate_sensitive_access(accessor, data_type, reason):
        return True


def semantic_search(query: str, top_k: int = 5, _vector_store=None, _embedding_provider=None) -> List[Dict[str, Any]]:
    """
    Perform semantic search using vector similarity, joining results back to SQLite KV.

    Respects tombstones (filters out deleted entries) and applies redaction rules.

    Args:
        query: The search query string
        top_k: Maximum number of results to return
        _vector_store: Optional vector store for testing
        _embedding_provider: Optional embedding provider for testing

    Returns:
        List of dicts with keys: 'key', 'value', 'score', 'casing', 'source', 'updated_at'
    """
    if not are_vector_features_enabled():
        return []

    vector_store = _vector_store if _vector_store is not None else get_vector_store()
    embedding_provider = _embedding_provider if _embedding_provider is not None else get_embedding_provider()

    if not vector_store or not embedding_provider:
        return []

    # Embed the query
    query_embedding = embedding_provider.embed_text(query)

    # Search vector store for top_k similar vectors
    vector_results = vector_store.search(query_embedding, top_k)

    # Join back to SQLite KV and apply filters/redaction
    results = []
    for result in vector_results:
        key = result.id
        kv_pair = get_key(key)

        if not kv_pair:
            # Key not found in SQLite (shouldn't happen but safety check)
            continue

        # Skip tombstones (empty values)
        if not kv_pair.value:
            continue

        # Apply redaction rule
        redacted_value = kv_pair.value
        if kv_pair.sensitive and not debug_enabled():
            redacted_value = "***"

        # Build result dict (excluding sensitive flag from response)
        result_dict = {
            "key": kv_pair.key,
            "value": redacted_value,
            "score": result.score,
            "casing": kv_pair.casing,
            "source": kv_pair.source,
            "updated_at": kv_pair.updated_at,
        }

        # Stage 6: Add provenance metadata when privacy enforcement is enabled
        if PRIVACY_ENFORCEMENT_ENABLED:
            result_dict["provenance"] = {
                "key": kv_pair.key,
                "source": kv_pair.source,
                "sensitive_level": "high" if kv_pair.sensitive else "low",
                "access_validated": not kv_pair.sensitive or validate_sensitive_access(
                    accessor="semantic_search",
                    data_type="vector_search_result",
                    reason=f"Access to semantic search result with key {kv_pair.key}"
                ),
                "redacted": kv_pair.sensitive and not debug_enabled(),
                "storage_mechanism": "vector_indexed_kv",
                "retrieval_method": "semantic_similarity"
            }

        results.append(result_dict)

    return results
