"""
Stage 2 scope only. Do not implement beyond this file's responsibilities.
Vector memory overlay - non-canonical, advisory layer over SQLite canonical truth.
"""

from typing import List, Dict, Any, Optional
from .config import get_vector_store, get_embedding_provider, are_vector_features_enabled, debug_enabled
from .dao import get_key

# Import config module to access PRIVACY_ENFORCEMENT_ENABLED dynamically
from . import config as config_module

# Import privacy enforcement for provenance reporting (Stage 6)
try:
    from .privacy import validate_sensitive_access
except ImportError:
    def validate_sensitive_access(accessor, data_type, reason):
        return True


def apply_privacy_redaction(item: dict, kv_pair) -> dict:
    """
    Apply privacy redaction rules and provenance reporting when enabled.
    Adds provenance metadata to the item when PRIVACY_ENFORCEMENT_ENABLED is True.
    """
    if not config_module.PRIVACY_ENFORCEMENT_ENABLED:
        return item

    # Add provenance metadata for Stage 6 privacy enforcement
    from .privacy import PrivacyEnforcer
    enf = PrivacyEnforcer()

    # Validate access to this specific vector search result
    access_validated = validate_sensitive_access(
        accessor="semantic_search",
        data_type="vector_search_result",
        reason=f"Access to semantic search result with key {item['key']}"
    )

    sensitive_level = "high" if kv_pair.sensitive else "low"

    # Add provenance dictionary
    item["provenance"] = {
        "key": item["key"],
        "source": "vector_search_result",
        "sensitive_level": sensitive_level,
        "access_validated": access_validated,
        "redacted": kv_pair.sensitive,
        "storage_mechanism": "vector_indexed_kv",
        "retrieval_method": "semantic_similarity"
    }

    # If access not validated or should be redacted, apply redaction
    if not access_validated or (kv_pair.sensitive and not debug_enabled()):
        item["value"] = "***"

    return item

def semantic_search(query: str, top_k: int = 5, user_id: str = "default", _vector_store=None, _embedding_provider=None) -> List[Dict[str, Any]]:
    """
    Perform semantic search using vector similarity, returning provenance-ready results.

    Returns results formatted as MemoryProvenance objects for UI integration.
    Respects tombstones and applies redaction rules.

    Args:
        query: The search query string
        top_k: Maximum number of results to return
        _vector_store: Optional vector store for testing
        _embedding_provider: Optional embedding provider for testing

    Returns:
        List of dicts with provenance metadata: 'type', 'key', 'value', 'score', 'explanation'
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
        vector_key = result.id

        # Parse user_id:key from vector key format (added in Stage 6 user scoping)
        if ":" in vector_key:
            stored_user_id, key = vector_key.split(":", 1)
        else:
            # Fallback for older format/compatibility
            stored_user_id = user_id
            key = vector_key

        kv_pair = get_key(stored_user_id, key)

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

        # Build provenance-ready result dict for UI Memory Results
        result_dict = {
            "type": "semantic",
            "key": kv_pair.key,
            "value": redacted_value,
            "score": float(result.score),
            "explanation": f"Matched via semantic vector similarity at {result.score:.2f} (from stored: {query[:30]}...)".replace("'", "").replace('"', ''),
        }

        # Stage 6: Privacy redaction when enabled
        if config_module.PRIVACY_ENFORCEMENT_ENABLED:
            result_dict = apply_privacy_redaction(result_dict, kv_pair)

        results.append(result_dict)

    return results
