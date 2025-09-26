# Stage Validation Checklists

This document contains human validation checklists for each stage of the bot-swarm memory project. **Each stage gate must pass before proceeding to the next stage.**

## Stage 1 Gate: Foundation (REQUIRED - HARD GATE)

### Automated Tests ✅
- [ ] All smoke tests pass: `make smoke`
- [ ] Database health check passes
- [ ] KV set/get with exact casing preservation works
- [ ] KV update increments timestamps correctly
- [ ] Sensitive flag handling works
- [ ] Episodic logging captures KV operations
- [ ] Tombstone deletion works (empty value, not hard delete)

### Manual API Tests ✅
Use `docs/API_QUICKSTART.md` curl examples:
- [ ] Health endpoint returns OK status with KV count
- [ ] Set displayName='Mark' via PUT /kv, get it back exactly
- [ ] List KV pairs shows all non-tombstone entries
- [ ] Sensitive values redacted unless DEBUG=true
- [ ] Debug endpoint works only when DEBUG=true (403 otherwise)
- [ ] Episodic events logged for all KV operations

### Code Review ✅
- [ ] SQLite schema matches spec (kv + episodic tables)
- [ ] DAO functions return typed results as specified
- [ ] FastAPI endpoints use Pydantic schemas for validation
- [ ] Exact casing preservation in KV operations
- [ ] Structured logging with timestamps and operation details
- [ ] Error handling for invalid requests (400/404/500)

### Environment & Setup ✅
- [ ] Quick start works in clean environment
- [ ] .env.example copied and modified
- [ ] Database directory created automatically
- [ ] Server starts and Swagger docs available in debug mode

---

## Stage 2 Gate: Vector Memory Integration (TODO - NOT IMPLEMENTED)

**🚫 NO CODE FOR STAGE 2+ IN THIS SCAFFOLD**

### Requirements Checklist (Future Implementation)
- [ ] ChromaDB or FAISS-CPU integrated with persistence
- [ ] SentenceTransformers or E5-small embeddings working
- [ ] /vector/add and /vector/search endpoints
- [ ] Basic semantic search with metadata (user_id, source, timestamp)
- [ ] Vector operations logged to episodic
- [ ] Embedding cache for hot context
- [ ] Error handling for embedding failures

### Manual Tests (Future)
- [ ] Index sample documents via API
- [ ] Search for similar content returns relevant results
- [ ] Metadata preserved in vector storage
- [ ] Restart preserves vector index (disk persistence)

---

## Stage 3 Gate: Heartbeat & Corrections (TODO - NOT IMPLEMENTED)

### Requirements Checklist (Future Implementation)
- [ ] APScheduler or async heartbeat loop configured
- [ ] Correction queue in SQLite (corrections table)
- [ ] Periodic processing of correction queue (limit per beat)
- [ ] Health metrics: heartbeat frequency, queue depth
- [ ] Metabolism controls (tunable cadence)
- [ ] Vector hygiene: deprecate old/conflicting chunks

### Manual Tests (Future)
- [ ] Heartbeat fires on schedule (observable in logs)
- [ ] Enqueue correction, observe processing within N beats
- [ ] Health endpoint shows heartbeat and queue status
- [ ] Metabolism adjustment changes heartbeat frequency

---

## Stage 4 Gate: Memory Overlay & RAG (TODO - NOT IMPLEMENTED)

### Requirements Checklist (Future Implementation)
- [ ] Multi-layer read logic: KV overrides vector results
- [ ] Identity/preferences always read from KV (canonical)
- [ ] General questions use vector + KV overlay
- [ ] Executor post-check enforces exact KV values in responses
- [ ] Conflict detection and correction queuing
- [ ] RAG responses cite sources and overlays applied

### Manual Tests (Future)
- [ ] Set identity in KV, ask identity question → exact KV value returned
- [ ] Update preference, vector search should reflect override
- [ ] Complex question uses both vector context and KV facts
- [ ] Response includes "profile overrides applied" when relevant

---

## Stage 5 Gate: Approval Workflow & Schema Validation (TODO)

### Requirements Checklist (Future Implementation)
- [ ] Pydantic validators for all schemas
- [ ] Human approval required for critical operations
- [ ] Invalid request validation (400 errors with details)
- [ ] Approval queue for corrections and updates
- [ ] Audit log for approvals and rejections

---

## Stage 6 Gate: TUI/Ops Dashboard (TODO)

### Requirements Checklist (Future Implementation)
- [ ] textual or rich dashboard for live status
- [ ] KV browser and editor
- [ ] Episodic event viewer
- [ ] Correction queue monitor
- [ ] Health metrics display
- [ ] Classroom-friendly demo mode

---

## Stage 7 Gate: Privacy & Maintenance (TODO)

### Requirements Checklist (Future Implementation)
- [ ] FERPA-compliant data handling
- [ ] Backup and restore scripts
- [ ] Data export with PII redaction
- [ ] Log rotation and cleanup
- [ ] Air-gapped operation verified
- [ ] Security audit checklist

---

## Validation Process

1. **Automated**: Run `make smoke` - all tests must pass
2. **Manual**: Follow API quickstart guide end-to-end
3. **Code Review**: Use VSCode/peer review for logic and schema
4. **Documentation**: Verify README quick start works
5. **Approval**: Get sign-off before proceeding to next stage

## Stage Gate Enforcement

**🔒 HARD GATE RULE: No Stage 2+ code allowed until Stage 1 gate passes completely.**

Each stage builds on the previous foundation. Skipping validation leads to integration problems and context drift - exactly what this memory system is designed to prevent.