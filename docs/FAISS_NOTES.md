# FAISS Implementation Notes

This document provides implementation details and operational guidance for the FAISS vector store.

## Overview

The `FaissVectorStore` is an optional vector storage implementation that leverages Facebook AI Similarity Search (FAISS) for efficient similarity search operations. It implements the `IVectorStore` interface and uses a flat index with inner product metric to enable cosine similarity searches.

## Implementation Details

### Index Type
- Uses `faiss.IndexFlatIP(dimension)` - a flat index with inner product metric
- This provides cosine similarity through normalized vector dot products 
- Supports both single and batch operations

### Vector Handling
- All vectors are normalized before being added to the FAISS index (required for accurate cosine similarity)
- Vectors are stored as `float32` type as required by FAISS
- Record ID mapping is maintained in-memory to correlate results back to original records

### Limitations and Tradeoffs

#### Deletion Support
FAISS does not support efficient direct deletions. For this implementation:
- The `delete()` method raises NotImplementedError 
- This limitation is documented in the interface contract
- In production, index rebuilding would be required for true deletion operations

#### Memory Usage
- FAISS stores vectors in memory during runtime
- Large vector collections may require significant RAM
- Consider using more advanced FAISS indices (IVF, HNSW) for production systems

## Operational Procedures

### Installation Requirements
The `faiss-cpu` package is an optional dependency that must be installed separately:

```bash
pip install faiss-cpu==1.7.2
```

If the library is not available at runtime, the implementation gracefully fails with ImportError.

### Rebuild Operations
Since FAISS doesn't support efficient deletion:
- The rebuild utility (`scripts/rebuild_index.py`) should be used to refresh indexes 
- This process reads all non-sensitive, non-tombstoned entries from SQLite
- All vectors are re-embedded and added to a fresh FAISS index

## Python 3.10 Compatibility

This implementation is designed for Python 3.10 compatibility:
- Uses standard library features only  
- Properly handles type annotations
- Follows existing code style conventions
