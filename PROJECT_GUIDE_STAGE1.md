# PROJECT GUIDE: Stage 1 Implementation for Grok

**⚠️ STAGE 1 SCOPE ONLY - DO NOT IMPLEMENT BEYOND THIS BOUNDARY ⚠️**

## Project Purpose

Build a **local-first, multi-agent memory scaffold** with SQLite as "shadow/canonical" memory. This is Stage 1 foundation work only—no vector databases, embeddings, agent orchestration, or advanced features.

## Critical Constraints

### ✅ STAGE 1 SCOPE (Implement These)
- SQLite database with KV store and episodic logging
- FastAPI service with specific endpoints
- Data Access Object (DAO) layer with typed returns
- Pytest smoke tests for core functionality
- Documentation and human validation checklists
- Development scripts and environment setup

### 🚫 OUT OF SCOPE (DO NOT IMPLEMENT)
- **NO vector databases** (FAISS, ChromaDB, etc.)
- **NO embeddings** or semantic search
- **NO agent orchestration** or bot swarm logic
- **NO heartbeat/scheduling** systems (APScheduler, etc.)
- **NO RAG** or retrieval augmented generation
- **NO external database connections** (PostgreSQL, etc.)
- **NO advanced memory layers** beyond basic KV + episodic
- **NO future stage implementation** - only documentation stubs

## Stage 1 Deliverables

### File Structure to Create
```
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI application
│   │   └── schemas.py       # Pydantic models
│   └── core/
│       ├── __init__.py
│       ├── config.py        # Environment configuration
│       ├── db.py           # SQLite connection management
│       └── dao.py          # Data access layer
├── tests/
│   ├── __init__.py
│   └── test_smoke.py       # Smoke tests
├── docs/
│   ├── STAGE_CHECKS.md     # Validation checklists
│   ├── API_QUICKSTART.md   # Manual testing guide
│   └── ARCHITECTURE.md     # System design (Stage 1 only)
├── scripts/
│   ├── make_dev.sh         # Development server
│   └── make_smoke.sh       # Test runner
├── util/
│   └── logging.py          # Structured logging
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
├── .gitignore             # Git ignore rules
├── Makefile               # Development commands
└── README.md              # Project overview
```

### 1. Core Database Layer (src/core/)

#### config.py
**Purpose**: Environment variable management
**Content**:
- DB_PATH configuration (default: `./data/memory.db`)
- DEBUG flag (default: true)
- VERSION string ("1.0.0-stage1")
- Directory creation utility for database path

#### db.py
**Purpose**: SQLite connection and schema initialization
**Content**:
- SQLite connection management with context manager
- Database initialization function with pragma settings
- Schema creation for two tables only:
  - `kv` table: key, value, casing, source, updated_at, sensitive
  - `episodic` table: id, ts, actor, action, payload
- Health check function
- **NO OTHER TABLES** in Stage 1

#### dao.py
**Purpose**: Data access layer with typed returns
**Content**:
- `get_key(key)` → typed result or None
- `set_key(key, value, source, casing, sensitive)` → operation result
- `list_keys()` → list of all KV pairs
- `delete_key(key)` → tombstone delete (set value='')
- `add_event(actor, action, payload)` → episodic logging
- `list_events(limit)` → recent events
- `get_kv_count()` → count of non-tombstone entries
- All functions include error handling and logging

### 2. API Layer (src/api/)

#### schemas.py
**Purpose**: Pydantic models for request/response validation
**Content**:
- KVSetRequest, KVResponse, KVGetResponse, KVListResponse
- EpisodicRequest, EpisodicResponse, EpisodicListResponse  
- HealthResponse, DebugResponse
- All with proper field validation and descriptions

#### main.py
**Purpose**: FastAPI application with exact endpoints
**Content**:
- **GET /health** → system status, version, db health, kv count
- **PUT /kv** → set key-value pair with validation
- **GET /kv/{key}** → get single key (404 if not found)
- **GET /kv/list** → list all non-tombstone KV pairs
- **POST /episodic** → add custom episodic event
- **GET /debug** → debug info (DEBUG mode only, 403 otherwise)
- Automatic database initialization on startup
- Global exception handler with structured errors
- **NO OTHER ENDPOINTS** in Stage 1

### 3. Testing Layer (tests/)

#### test_smoke.py
**Purpose**: Comprehensive smoke tests for Stage 1 functionality
**Content**:
- Database health verification
- KV set/get with exact casing preservation
- KV update with timestamp increment verification
- Sensitive flag handling and redaction
- KV listing and tombstone deletion
- Episodic event creation and retrieval
- KV operations automatically creating episodic events
- KV count functionality with tombstone handling
- All tests use temporary database for isolation

### 4. Documentation Layer (docs/)

#### STAGE_CHECKS.md
**Purpose**: Human validation checklists and hard gates
**Content**:
- **Stage 1 Gate (REQUIRED)**: Complete checklist for automated tests, manual API tests, code review, environment setup
- **Stage 2+ Gates (TODO ONLY)**: Checklist stubs with "NOT IMPLEMENTED" warnings
- Explicit validation process and approval requirements
- **Hard gate enforcement**: No Stage 2+ code until Stage 1 approved

#### API_QUICKSTART.md  
**Purpose**: Manual testing guide with curl examples
**Content**:
- Curl commands for every endpoint
- Expected request/response formats
- Error case testing scenarios
- One-liner smoke test sequence
- Behavior verification scripts (casing, timestamps, redaction)

#### ARCHITECTURE.md
**Purpose**: System design documentation (Stage 1 scope only)
**Content**:
- Shadow memory concept explanation
- SQLite schema and data flow diagrams
- **Future stage previews** (description only, no implementation guidance)
- Design principles and deployment characteristics
- **Clear Stage 1 boundary statements**

### 5. Development Tools

#### requirements.txt
**Purpose**: Python dependencies for Stage 1 only
**Content**:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-dotenv==1.0.0
sqlite-utils==3.35.2
pytest==7.4.3
requests==2.31.0
rich==13.7.0
```
**NO vector database libraries** (faiss, chromadb, sentence-transformers, etc.)

#### Makefile
**Purpose**: Development command shortcuts
**Content**:
- `make dev` → start development server
- `make test` → run all tests
- `make smoke` → run smoke tests only
- `make format` → code formatting (optional)
- `make clean` → cleanup temporary files

#### Scripts (scripts/)
- `make_dev.sh`: Development server with auto-reload and environment checks
- `make_smoke.sh`: Smoke test runner with success/failure reporting

### 6. Utilities (util/)

#### logging.py
**Purpose**: Structured logging for operations
**Content**:
- StructuredLogger class with consistent formatting
- Operation logging with status, duration, details
- KV-specific and episodic-specific log methods
- **NO complex logging frameworks** - keep simple for Stage 1

## Implementation Rules

### Anti-Drift Safeguards

1. **File Headers**: Add to every Python file:
   ```python
   """
   Stage 1 Implementation - SQLite Foundation Only
   DO NOT IMPLEMENT BEYOND STAGE 1 SCOPE
   """
   ```

2. **Comment Boundaries**: Flag any mention of future stages:
   ```python
   # TODO Stage 2+: Vector integration will go here
   # NOT IMPLEMENTED: Heartbeat scheduling
   ```

3. **Scope Validation**: Before any commit, verify:
   - No imports of vector libraries
   - No embedding or ML-related code
   - No scheduler or async task code beyond FastAPI
   - No references to agents, RAG, or retrieval

### Hard Gate Strategy

#### Stage 1 Completion Criteria
1. **Automated Tests Pass**: All smoke tests in `test_smoke.py` pass
2. **Manual API Tests Pass**: All curl examples in `API_QUICKSTART.md` work
3. **Code Review Complete**: Human review of all deliverables against this guide
4. **Environment Setup Verified**: Quick start instructions work in clean environment
5. **Documentation Complete**: All required docs exist and are accurate

#### Gate Enforcement
- **No Stage 2 work** until explicit human approval documented
- **No vector/embedding libraries** added to requirements.txt
- **No implementation** of future stage checklists, only documentation stubs
- **Review against this guide** before marking Stage 1 complete

## Testing Strategy

### Automated Testing (Required)
```bash
make smoke  # Must pass 100%
```
Tests must cover:
- Database schema and health
- All KV operations with edge cases
- Episodic logging integration
- API endpoint responses and error cases
- Sensitive data redaction
- Exact casing preservation

### Manual Testing (Required)
```bash
# Follow docs/API_QUICKSTART.md completely
make dev
# Run all curl examples
# Verify expected responses
```

### Code Review Checklist
- [ ] All files match deliverables list
- [ ] No out-of-scope imports or references
- [ ] SQLite schema matches specification exactly
- [ ] API endpoints match specification exactly
- [ ] Error handling covers expected cases
- [ ] Logging is structured and informative
- [ ] Documentation is complete and accurate

## Stage 1 Success Criteria

### Must Exist and Work:
- ✅ SQLite database with kv and episodic tables
- ✅ FastAPI service with 6 specified endpoints
- ✅ DAO layer with typed returns and error handling
- ✅ Pytest smoke tests covering all core functionality
- ✅ Manual testing guide with working curl examples
- ✅ Development environment setup and scripts
- ✅ Human validation checklists for Stage 1 gate

### Must NOT Exist:
- 🚫 Any vector database code or libraries
- 🚫 Embedding or ML-related functionality
- 🚫 Agent orchestration or swarm logic  
- 🚫 Heartbeat or scheduling systems
- 🚫 RAG or semantic search features
- 🚫 Implementation of Stage 2+ features

### Validation Process:
1. Run `make smoke` → all tests pass
2. Follow `docs/API_QUICKSTART.md` → all examples work  
3. Complete `docs/STAGE_CHECKS.md` Stage 1 checklist → human approval
4. Code review against this guide → no scope violations
5. Document approval → ready for Stage 2 planning (not implementation)

## Summary

**Stage 1 Objective**: Create a solid SQLite foundation with FastAPI service, comprehensive testing, and human validation gates. This provides the "shadow memory" layer that will be canonical truth for future stages.

**Key Success Measure**: A working KV store with episodic logging that preserves exact casing, handles sensitive data appropriately, and provides audit transparency through structured logging and comprehensive testing.

**Hard Boundary**: No code beyond basic SQLite + FastAPI + testing infrastructure. All future functionality exists only as documentation stubs for later implementation.

**Next Step After Stage 1**: Human approval and planning (not implementation) of Stage 2 vector integration.

---

**⚠️ REMINDER: This guide defines Stage 1 scope exactly. Any implementation beyond these deliverables violates the project constraints and should be flagged as out-of-scope. ⚠️**