# Stage 1 Bot-Swarm Memory System

## Project Goal
Multi-agent memory system where FAISS (vector DB) will be long-term memory and SQLite is canonical "shadow memory" to correct drift.

## Stage 1 Scope
- SQLite KV + episodic store with DAO
- FastAPI service with minimal endpoints
- Smoke tests and human validation gates
- **NO vector DB, embeddings, schedulers, or agent orchestration yet**

## Quick Start (1 minute)
```bash
# Setup
cp .env.example .env
pip install -r requirements.txt

# Run server
make dev

# Test endpoints (see docs/API_QUICKSTART.md)
curl -X PUT http://localhost:8000/kv -H "Content-Type: application/json" -d '{"key":"displayName","value":"Mark","source":"user"}'
curl http://localhost:8000/kv/displayName
curl http://localhost:8000/health

# Run tests
make smoke
```

## Architecture Concept
- **SQLite shadow memory is canonical** for identity, preferences, corrections
- FAISS will be non-canonical long-term memory in Stage 2+ for semantic search
- KV store preserves exact casing and tracks source/sensitivity
- Episodic log tracks all operations for audit/debugging

## Stage Gates
See `docs/STAGE_CHECKS.md` for human validation checklists. **Stage 1 gate must pass before any Stage 2 work.**

## File Structure
```
src/api/          # FastAPI routes and schemas
src/core/         # Database, DAO, config
tests/            # Smoke tests
docs/             # Architecture and checklists
scripts/          # Development utilities
```

## Human-in-the-Loop Testing
Every stage requires manual validation and peer review. See stage checklists for specific test scenarios and approval requirements.