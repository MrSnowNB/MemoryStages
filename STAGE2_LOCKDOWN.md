# STAGE 2 LOCKDOWN: Vector Memory Overlay Implementation

**⚠️ STAGE 2 SCOPE ONLY - DO NOT IMPLEMENT BEYOND THIS BOUNDARY ⚠️**

## Prerequisites

- Stage 1 is **COMPLETE** and **HUMAN-APPROVED**
- All Stage 1 smoke tests pass
- Stage 1 gate documented in `docs/STAGE_CHECKS.md`
- Python 3.10 environment

## Stage 2 Objectives (LOCKED SCOPE)

Add **non-canonical vector memory overlay** while keeping SQLite as canonical "shadow memory":

✅ **IN SCOPE**:
- Vector store abstraction with in-memory and optional FAISS implementations
- Embedding provider interface with deterministic hash for testing
- Feature-flagged ingestion hooks on KV operations
- Internal search service joining vector results to SQLite KV
- Beta search endpoint (feature-flagged, default OFF)
- Index rebuild utility and maintenance procedures

🚫 **OUT OF SCOPE** (FUTURE STAGES):
- Agent orchestration or bot swarm logic
- LLM integration or prompts
- Schedulers, cron jobs, or heartbeat systems
- RAG pipelines or complex retrieval workflows
- Browser automation or external APIs
- Cloud services or network dependencies
- UI/TUI dashboards
- Security hardening beyond existing redaction
- Backup/retention policies beyond rebuild utility

## Critical Constraints (ANTI-DRIFT SAFEGUARDS)

### Behavioral Constraints
- **Default flags keep Stage 1 behavior identical** when vector features disabled
- **SQLite remains canonical source of truth** - vector layer is advisory only
- **No changes to Stage 1 KV/episodic schemas** except feature-flag wiring
- **Sensitive data never embedded or indexed** - respect sensitive flag always
- **Tombstones respected across all vector operations** - no zombie data

### Implementation Constraints
- **Python 3.10 compatibility required**
- **No breaking changes to Stage 1 API** when flags are off
- **Optional dependencies only** - system works without FAISS
- **Feature flags control all new behavior** - dark by default

## Environment and Configuration Flags

### Required Configuration Variables (.env)
```bash
# Vector system controls (default: disabled)
VECTOR_ENABLED=false              # Master switch for vector features
VECTOR_PROVIDER=memory            # memory|faiss (if VECTOR_ENABLED=true)
EMBED_PROVIDER=hash               # hash|custom (hash for testing)
SEARCH_API_ENABLED=false          # Beta search endpoint toggle

# Existing Stage 1 flags (unchanged)
DB_PATH=./data/memory.db
DEBUG=true
```

### Flag Behavior Matrix
| VECTOR_ENABLED | SEARCH_API_ENABLED | Behavior |
|----------------|-------------------|----------|
| false | false | **Stage 1 identical** - no vector operations |
| true | false | Ingestion active, no search endpoint |
| true | true | Full Stage 2 features enabled |
| false | true | **INVALID** - search requires vector system |

## File Touch Policy (STRICT)

### Allowed Modifications Per Slice
Each slice lists **exactly** which files may be created or modified. 

**VIOLATION POLICY**: Editing files outside the slice's allowed list is **SCOPE CREEP** and requires rollback.

### File Header Requirement
All new files must include:
```python
"""
Stage 2 scope only. Do not implement beyond this file's responsibilities.
Vector memory overlay - non-canonical, advisory layer over SQLite canonical truth.
"""
```

## Stage 2 Slice Implementation Plan

### Slice 2.1: Vector Interface and In-Memory Store (Dark)

**Purpose**: Introduce vector store abstraction with simple in-memory implementation. No API integration.

**Allowed Files**:
- `src/vector/__init__.py` (new directory)
- `src/vector/index.py` (IVectorStore interface, SimpleInMemoryVectorStore)
- `src/vector/types.py` (VectorRecord, QueryResult dataclasses)
- `tests/test_vector_mock.py` (unit tests for mock implementation)
- `docs/VECTOR_OVERVIEW.md` (overlay concept documentation)

**Deliverables**:
- `IVectorStore` abstract interface: `add()`, `batch_add()`, `search()`, `delete()`, `clear()`
- `SimpleInMemoryVectorStore` implementation using normalized vectors and cosine similarity
- `VectorRecord` dataclass: id, vector, metadata dict
- `QueryResult` dataclass: id, score, metadata
- Unit tests covering add, search top_k, delete, tombstone awareness
- Documentation explaining non-canonical overlay concept

**Test Plan**:
```bash
pytest tests/test_vector_mock.py -v
```

**Hard Gate Criteria**:
- [ ] All vector mock tests pass
- [ ] No imports into `src/core/` or `src/api/`
- [ ] No external dependencies added
- [ ] Documentation explains SQLite remains canonical

**Rollback Guidance**: Delete `src/vector/` directory and `tests/test_vector_mock.py`

---

### Slice 2.2: Embedding Provider Interface

**Purpose**: Define embedding abstraction without external model dependencies.

**Allowed Files**:
- `src/vector/embeddings.py` (IEmbeddingProvider, DeterministicHashEmbedding)
- `tests/test_embeddings.py` (determinism and stability tests)

**Deliverables**:
- `IEmbeddingProvider` abstract interface: `embed_text()`, `get_dimension()`
- `DeterministicHashEmbedding` implementation for testing (consistent hash-based vectors)
- Tests verifying deterministic output across runs
- Fixed dimension output (e.g., 384) for consistency

**Test Plan**:
```bash
pytest tests/test_embeddings.py -v
```

**Hard Gate Criteria**:
- [ ] Embedding tests pass with deterministic results
- [ ] Same input produces identical vectors across runs
- [ ] Still no API or DAO integration
- [ ] No external model dependencies

**Rollback Guidance**: Delete `src/vector/embeddings.py` and `tests/test_embeddings.py`

---

### Slice 2.3: Optional FAISS Implementation (Dark)

**Purpose**: Provide FAISS-backed store behind interface as optional dependency.

**Allowed Files**:
- `src/vector/faiss_store.py` (FaissVectorStore implementing IVectorStore)
- `tests/test_faiss_store.py` (FAISS-specific tests with skip decorator)
- `docs/FAISS_NOTES.md` (implementation details and tradeoffs)
- `requirements.txt` (add faiss-cpu with comment)

**Deliverables**:
- `FaissVectorStore` using normalized inner product metric
- Tests that skip gracefully if faiss-cpu not installed
- Documentation covering index type, rebuild procedures, Python 3.10 compatibility
- Optional dependency added to requirements with clear comment

**Test Plan**:
```bash
# If FAISS installed
pytest tests/test_faiss_store.py -v

# If FAISS not installed
pytest tests/test_faiss_store.py -v  # Should skip all tests
```

**Hard Gate Criteria**:
- [ ] If FAISS installed: all FAISS tests pass
- [ ] If FAISS not installed: tests skip cleanly without errors
- [ ] No integration with API or DAO yet
- [ ] Documentation covers rebuild scenarios

**Rollback Guidance**: Remove FAISS files and revert requirements.txt

---

### Slice 2.4: Feature-Flagged Ingestion Wiring

**Purpose**: On KV upsert (non-sensitive), embed and add/update vector. On tombstone, remove vector entry. No new endpoints.

**Allowed Files**:
- `src/core/dao.py` (modify existing - add vector provider injection)
- `src/core/config.py` (modify existing - add vector flags)
- `src/util/logging.py` (modify existing - add vector operation logs)
- `tests/test_ingestion_vectorized.py` (integration tests with mocking)

**Deliverables**:
- Config flags: `VECTOR_ENABLED`, `VECTOR_PROVIDER`, `EMBED_PROVIDER`
- Modified `set_key()` to conditionally embed and store in vector index
- Modified `delete_key()` to remove from vector index on tombstone
- Respect sensitive flag - never embed sensitive data
- Structured logging for vector operations
- Integration tests with dependency injection/mocking

**Test Plan**:
```bash
# Stage 1 behavior preserved
VECTOR_ENABLED=false pytest tests/test_smoke.py -v

# Vector ingestion active
VECTOR_ENABLED=true VECTOR_PROVIDER=memory EMBED_PROVIDER=hash \
    pytest tests/test_ingestion_vectorized.py -v
```

**Hard Gate Criteria**:
- [ ] With `VECTOR_ENABLED=false`: all Stage 1 smoke tests pass unchanged
- [ ] With `VECTOR_ENABLED=true`: ingestion tests pass
- [ ] Sensitive keys excluded from vector operations
- [ ] Tombstones remove vector entries
- [ ] Structured logs show vector operations when enabled

**Rollback Guidance**: Revert changes to dao.py, config.py, logging.py using git

---

### Slice 2.5: Internal Search Service (No API)

**Purpose**: Create `semantic_search()` function joining vector hits back to SQLite KV, respecting tombstones and redaction.

**Allowed Files**:
- `src/core/search_service.py` (new file - internal search logic)
- `tests/test_search_service.py` (search functionality tests)

**Deliverables**:
- `semantic_search(query, top_k)` function using embedding + vector providers
- Join vector results back to SQLite KV for current values
- Filter out tombstones (empty values)
- Apply redaction rules for sensitive data unless DEBUG=true
- Return ranked results with scores and metadata

**Test Plan**:
```bash
VECTOR_ENABLED=true VECTOR_PROVIDER=memory EMBED_PROVIDER=hash \
    pytest tests/test_search_service.py -v
```

**Hard Gate Criteria**:
- [ ] Search returns ranked results by vector similarity
- [ ] Tombstoned KV entries filtered out of results
- [ ] Sensitive data redacted unless DEBUG=true
- [ ] No public endpoints yet - internal function only
- [ ] Results joined with current SQLite KV values

**Rollback Guidance**: Delete `src/core/search_service.py` and `tests/test_search_service.py`

---

### Slice 2.6: Feature-Flagged Beta Search Endpoint

**Purpose**: Add `GET /search?query=&k=` endpoint gated by `SEARCH_API_ENABLED=true`, default off.

**Allowed Files**:
- `src/api/main.py` (modify existing - add search endpoint with flag guard)
- `src/api/schemas.py` (modify existing - add search response models)
- `docs/API_QUICKSTART.md` (modify existing - add beta search section)
- `docs/STAGE_CHECKS.md` (modify existing - update Stage 2 gate checklist)

**Deliverables**:
- `GET /search` endpoint with query parameter validation
- Flag guard: returns 404 if `SEARCH_API_ENABLED=false`
- Pydantic response models for search results
- Updated API documentation with curl examples
- Stage 2 gate checklist in STAGE_CHECKS.md

**Test Plan**:
```bash
# Default behavior (endpoint disabled)
SEARCH_API_ENABLED=false make dev
curl http://localhost:8000/search?query=test  # Should return 404

# Beta behavior (endpoint enabled)  
VECTOR_ENABLED=true SEARCH_API_ENABLED=true make dev
curl "http://localhost:8000/search?query=test&k=5"  # Should return results
```

**Hard Gate Criteria**:
- [ ] With default flags: Stage 1 behavior identical, search endpoint returns 404
- [ ] With flags enabled: search endpoint returns ranked results
- [ ] Results apply redaction rules appropriately
- [ ] API documentation updated with beta warning
- [ ] Stage 2 gate checklist complete

**Rollback Guidance**: Revert API changes, remove search endpoint and schemas

---

### Slice 2.7: Index Rebuild Utility and Ops Documentation

**Purpose**: Provide utility to rebuild vector index from canonical SQLite KV state.

**Allowed Files**:
- `scripts/rebuild_index.py` (new script - rebuild from SQLite)
- `tests/test_rebuild_index.py` (rebuild functionality tests)
- `docs/MAINTENANCE.md` (new file - operational procedures)

**Deliverables**:
- Rebuild script reading all non-sensitive, non-tombstoned KV entries
- Re-embed and rebuild vector index from scratch
- Handle both memory and FAISS providers
- Comprehensive maintenance documentation
- Tests verifying rebuild accuracy and completeness

**Test Plan**:
```bash
# Test rebuild functionality
VECTOR_ENABLED=true pytest tests/test_rebuild_index.py -v

# Manual rebuild test
python scripts/rebuild_index.py --dry-run
```

**Hard Gate Criteria**:
- [ ] Rebuild script works with both memory and FAISS providers
- [ ] Tests verify correct counts and search results after rebuild
- [ ] Documentation provides step-by-step operational guidance
- [ ] Dry-run mode available for verification
- [ ] Script respects sensitive and tombstone flags

**Rollback Guidance**: Delete rebuild script, tests, and maintenance docs

## Global Test and Verification Matrix

### Automated Testing Strategy

**Per-Slice Testing** (minimize token usage):
```bash
# Run only relevant tests per slice to avoid full regression
pytest tests/test_vector_mock.py -v          # Slice 2.1
pytest tests/test_embeddings.py -v          # Slice 2.2  
pytest tests/test_faiss_store.py -v         # Slice 2.3
pytest tests/test_ingestion_vectorized.py -v # Slice 2.4
pytest tests/test_search_service.py -v      # Slice 2.5
pytest tests/test_rebuild_index.py -v       # Slice 2.7
```

**Stage 1 Regression Testing**:
```bash
# Must pass with vector features disabled
VECTOR_ENABLED=false SEARCH_API_ENABLED=false pytest tests/test_smoke.py -v
```

### Manual Verification Procedures

**Flag Combination Testing**:
```bash
# Test 1: Stage 1 behavior (default)
cp .env.example .env  # Default flags off
make dev
# Follow original Stage 1 API_QUICKSTART.md - should work identically

# Test 2: Vector ingestion only
echo "VECTOR_ENABLED=true" >> .env
echo "VECTOR_PROVIDER=memory" >> .env  
echo "EMBED_PROVIDER=hash" >> .env
make dev
# Set some KV values, check logs for vector operations

# Test 3: Full Stage 2 features
echo "SEARCH_API_ENABLED=true" >> .env
make dev
curl "http://localhost:8000/search?query=test&k=3"
```

### Security and Privacy Verification

**Sensitive Data Protection**:
- [ ] Sensitive KV entries never appear in vector index
- [ ] Search results redact sensitive values unless DEBUG=true
- [ ] Logs do not expose sensitive content in vector operations

**Tombstone Respect**:
- [ ] Deleted (tombstoned) KV entries removed from vector index
- [ ] Search results exclude tombstoned entries
- [ ] Rebuild script skips tombstoned entries

### Performance Guidelines (Lightweight)

**Development Parameters** (avoid scope creep):
- Default `k=5` for search results
- Hash embedding dimension: 384
- In-memory store for development/testing
- FAISS index: simple flat index, no complex optimizations

## Gatekeeping Rules (ENFORCEMENT)

### Slice Progression Policy
- **Proceed to next slice ONLY after current slice Gate criteria met**
- **Human approval documented** in `docs/STAGE_CHECKS.md` Stage 2 section
- **No parallel slice work** - complete current slice fully before next

### Gate Failure Protocol
1. **Stop development immediately**
2. **Rollback per slice's rollback guidance**
3. **Fix issues within current slice scope only**
4. **Do not expand scope to "fix" gate failures**
5. **Re-test and get approval before proceeding**

### Code Review Requirements
- **All new code includes Stage 2 scope banner**
- **Flag guards properly implemented and tested**
- **No Stage 1 behavioral changes when flags disabled**
- **Documentation updated appropriately**

## Release and Flags Policy

### Default Configuration (Safe)
```bash
# Default .env keeps vector features dark
VECTOR_ENABLED=false
SEARCH_API_ENABLED=false
VECTOR_PROVIDER=memory
EMBED_PROVIDER=hash
```

### Beta Feature Policy
- **All Stage 2 features opt-in only**
- **Reversible by configuration without code changes**
- **Clear beta warnings in documentation**
- **Gradual rollout capability via flags**

### Deployment Safety
- **Stage 1 users unaffected by Stage 2 deployment**
- **Feature flags documented in .env.example**
- **Migration path documented if needed**

## Final Stage 2 Gate (COMPLETION CRITERIA)

### Automated Verification
- [ ] **All Stage 2 slice tests pass**
- [ ] **Stage 1 regression tests pass with flags disabled**
- [ ] **FAISS tests pass if library installed, skip if not**

### Manual Verification Checklist
- [ ] **Flags off**: Identical behavior to Stage 1 (API, logging, database)
- [ ] **Flags on (memory/hash)**: Ingestion and search work as specified
- [ ] **FAISS provider**: Works if installed, degrades gracefully if not
- [ ] **Rebuild script**: Successfully rebuilds index from SQLite state

### Documentation Completeness
- [ ] **VECTOR_OVERVIEW.md**: Explains overlay concept and canonical truth
- [ ] **FAISS_NOTES.md**: Implementation details and operational guidance
- [ ] **API_QUICKSTART.md**: Beta search section with warnings and examples
- [ ] **MAINTENANCE.md**: Step-by-step operational procedures
- [ ] **STAGE_CHECKS.md**: Stage 2 gate fully documented

### Human Approval Requirements
- [ ] **Code review**: All deliverables reviewed against this lockdown document
- [ ] **Security review**: Sensitive data and tombstone protections verified
- [ ] **Performance review**: Lightweight parameters confirmed
- [ ] **Documentation review**: All docs accurate and complete
- [ ] **Gate approval**: Signed off in STAGE_CHECKS.md before Stage 3 planning

---

**⚠️ STAGE 2 LOCKDOWN COMPLETE - NO IMPLEMENTATION BEYOND THIS SCOPE ⚠️**

This document defines the complete, gated execution plan for Stage 2. Any implementation beyond these specifications constitutes scope creep and requires document revision and re-approval.