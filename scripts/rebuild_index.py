#!/usr/bin/env python3
"""
Stage 2 scope only. Do not implement beyond this file's responsibilities.
Vector memory overlay - non-canonical, advisory layer over SQLite canonical truth.

Index Rebuild Utility
Rebuilds vector index from canonical SQLite KV state after data corruption/lost vectors.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.dao import list_keys
from src.core.config import get_vector_store, get_embedding_provider, are_vector_features_enabled
from src.core.db import init_db

def main():
    """Rebuild vector index from SQLite KV store."""
    if not are_vector_features_enabled():
        print("ERROR: Vector features disabled. Set VECTOR_ENABLED=true")
        sys.exit(1)

    # Initialize database
    init_db()

    print("Starting vector index rebuild...")

    # Get vector store and embedding provider
    vector_store = get_vector_store()
    embedding_provider = get_embedding_provider()

    if not vector_store or not embedding_provider:
        print("ERROR: Vector store or embedding provider not available")
        sys.exit(1)

    # Clear existing index
    try:
        vector_store.clear()
        print("✓ Cleared existing vector index")
    except Exception as e:
        print(f"WARNING: Failed to clear existing index: {e}")

    # Get all active KV pairs
    kv_pairs = list_keys('default')
    print(f"Found {len(kv_pairs)} KV pairs in canonical store")

    # Filter out sensitive keys (re-embedding policy)
    non_sensitive_pairs = [kv for kv in kv_pairs if not kv.sensitive]
    print(f"Re-embedding {len(non_sensitive_pairs)} non-sensitive KV pairs")

    if not non_sensitive_pairs:
        print("No entries to rebuild. Exiting.")
        return

    # Rebuild index
    embedded_count = 0

    for kv in non_sensitive_pairs:
        try:
            # Create content to embed (key:value format)
            content_to_embed = f"{kv.key}: {kv.value}"

            # Generate embedding
            embedding = embedding_provider.embed_text(content_to_embed)

            # Create vector record
            vector_record = type('VectorRecord', (), {
                'id': kv.key,
                'vector': embedding,
                'metadata': {
                    'source': kv.source,
                    'casing': kv.casing,
                    'updated_at': kv.updated_at.isoformat() if hasattr(kv.updated_at, 'isoformat') else str(kv.updated_at)
                }
            })()

            # Add to vector store
            vector_store.add(vector_record)
            embedded_count += 1

            if embedded_count % 10 == 0:
                print(f"  ... embedded {embedded_count}/{len(non_sensitive_pairs)} entries")

        except Exception as e:
            print(f"ERROR: Failed to embed KV pair {kv.key}: {e}")
            continue

    print(f"✓ Successfully rebuilt index with {embedded_count} vectors")

    # Verify index
    try:
        # Quick smoke test - search for something
        if non_sensitive_pairs:
            test_query = "test"
            test_embedding = embedding_provider.embed_text(test_query)
            results = vector_store.search(test_embedding, k=min(3, embedded_count))
            print(f"✓ Verification search returned {len(results)} results")
        else:
            print("✓ No entries to verify (empty index)")
    except Exception as e:
        print(f"WARNING: Verification search failed: {e}")

    print("Index rebuild complete!")

if __name__ == "__main__":
    main()
