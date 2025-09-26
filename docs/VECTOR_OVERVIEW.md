# Vector Memory Overlay Overview

This document explains the vector memory overlay implementation introduced in Stage 2 of the MemoryStages project.

## Canonical Truth vs Advisory Layer

The vector memory system operates as a **non-canonical, advisory layer** over the SQLite canonical truth:

- **SQLite remains the source of truth** for all key-value pairs and episodic events
- **Vector memory is an overlay** that provides semantic search capabilities  
- **Vector operations are optional** and controlled by feature flags (`VECTOR_ENABLED`)
- **All vector operations respect sensitive data flags** - sensitive entries are never embedded or indexed

## Architecture

The system follows a layered architecture pattern:

1. **SQLite Canonical Store**: The primary source of truth for all data
2. **Vector Memory Overlay**: Optional semantic search layer that enhances discovery  
3. **Feature Flag Control**: All vector operations are gated by configuration flags

### Interface Design

All vector stores implement the `IVectorStore` interface which defines:
- `add()`: Add a single vector record 
- `batch_add()`: Add multiple records efficiently
- `search()`: Find similar vectors using semantic similarity
- `delete()`: Remove individual records
- `clear()`: Clear entire store

### Implementation Options  

Two implementations are provided:
1. **SimpleInMemoryVectorStore**: In-memory implementation for development/testing
2. **FaissVectorStore**: FAISS-backed implementation for production use (optional dependency)

## Key Principles

### 1. Non-Canonical Operation
The vector memory is never used as a source of truth. All operations that modify data still go through the canonical SQLite layer.

### 2. Feature Flag Control  
All new vector functionality is controlled by:
- `VECTOR_ENABLED`: Master switch for all vector features 
- `VECTOR_PROVIDER`: Which implementation to use (memory/faiss)
- `EMBED_PROVIDER`: How text is converted to vectors

### 3. Tombstone Respect
Vector operations properly respect tombstoned entries in SQLite - deleted KV pairs are removed from the vector index.

### 4. Sensitive Data Protection  
Sensitive data is never embedded or indexed, regardless of feature flags. The sensitive flag on KV entries prevents any vector processing.

## Operational Flow

1. **KV Upsert**: When a non-sensitive key-value pair is set, its content is embedded and added to the vector store
2. **KV Delete**: When a key is tombstoned (deleted), the corresponding vector entry is removed from the index  
3. **Semantic Search**: The `semantic_search()` function uses embeddings to find relevant vectors, then joins with SQLite KV for current values

## Design Rationale

This overlay approach ensures:
- No breaking changes to Stage 1 behavior when flags are disabled
- Gradual rollout of vector features through configuration 
- Clear separation between canonical truth and advisory layers
- Backwards compatibility with existing systems
