"""
Stage 2 scope only. Do not implement beyond this file's responsibilities.
Vector memory overlay - non-canonical, advisory layer over SQLite canonical truth.
"""

from typing import List, Dict, Any, Optional
from .config import get_vector_store, get_embedding_provider, are_vector_features_enabled, debug_enabled
from .dao import get_key


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

        results.append(result_dict)

    return results
