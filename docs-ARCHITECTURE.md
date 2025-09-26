# Bot-Swarm Memory System Architecture

## Overview

This system implements a multi-layered memory architecture designed for educational AI agents with strong context preservation, privacy, and FERPA compliance.

## Core Concept: Shadow Memory + Vector Memory

### The Problem
- Vector databases (FAISS, Chroma) excel at semantic search but suffer from "drift" - imprecise recall of exact facts
- Identity, preferences, and critical facts need deterministic, exact retrieval
- Educational environments require audit trails and human oversight

### The Solution: Multi-Layer Memory
1. **SQLite Shadow Memory** (canonical truth)
   - KV store for identity, preferences, corrections
   - Episodic log for audit trail
   - Always authoritative for scalar facts

2. **Vector Database** (semantic context - Stage 2+)
   - FAISS or ChromaDB for document chunks and semantic search
   - RAG (Retrieval Augmented Generation) for complex queries
   - Subordinate to shadow memory for conflicts

3. **Correction System** (Stage 3+)
   - Scheduled heartbeat to sync vector DB with canonical facts
   - Deprecation/correction of conflicting vector chunks
   - Human-in-the-loop approval for critical updates

## Stage 1 Architecture (Current)

```
┌─────────────────────┐    ┌──────────────────────┐
│     FastAPI         │    │      SQLite          │
│   ┌─────────────┐   │    │  ┌─────────────────┐ │
│   │  /health    │   │    │  │  kv table       │ │
│   │  /kv/*      │───┼────┼──│  - key (PK)     │ │
│   │  /episodic  │   │    │  │  - value        │ │
│   │  /debug     │   │    │  │  - casing       │ │
│   └─────────────┘   │    │  │  - source       │ │
└─────────────────────┘    │  │  - updated_at   │ │
                           │  │  - sensitive    │ │
                           │  └─────────────────┘ │
                           │                      │
                           │  ┌─────────────────┐ │
                           │  │ episodic table  │ │
                           │  │  - id (PK)      │ │
                           │  │  - ts           │ │
                           │  │  - actor        │ │
                           │  │  - action       │ │
                           │  │  - payload      │ │
                           │  └─────────────────┘ │
                           └──────────────────────┘
```

### Data Flow (Stage 1)
1. Client makes KV request → FastAPI validates with Pydantic
2. DAO layer executes SQLite operation with exact casing preservation
3. Episodic event automatically logged for audit
4. Response returns typed result with structured logging

## Future Architecture (Stages 2-7)

```
┌─────────────────────────────────────────────────────────┐
│                     FastAPI Service                     │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐    │
│  │/health  │ │  /kv/*  │ │/vector/*│ │  /debug     │    │
│  └─────────┘ └─────────┘ └─────────┘ └─────────────┘    │
└──────────┬────────────┬────────────┬───────────────────┘
           │            │            │
           ▼            ▼            ▼
┌─────────────────────────────────────────────────────────┐
│                  Memory Manager                         │
│  ┌─────────────────┐  ┌─────────────────────────────┐   │
│  │  KV Operations  │  │     RAG + Overlay Logic     │   │
│  │  - Canonical    │  │  - Vector search            │   │
│  │  - Exact match  │  │  - KV override injection    │   │
│  │  - Identity     │  │  - Conflict resolution      │   │
│  └─────────────────┘  └─────────────────────────────┘   │
└──────────┬────────────────────────────┬─────────────────┘
           │                            │
           ▼                            ▼
┌──────────────────────┐    ┌──────────────────────────────┐
│   SQLite (Shadow)    │    │     Vector DB (Semantic)     │
│ ┌──────────────────┐ │    │  ┌─────────────────────────┐ │
│ │ kv (canonical)   │ │    │  │ Embeddings + Metadata   │ │
│ │ episodic (audit) │ │    │  │ - user_id, source, ts   │ │
│ │ corrections (Q)  │ │    │  │ - reliability score     │ │
│ └──────────────────┘ │    │  │ - deprecation flags     │ │
└──────────────────────┘    │  └─────────────────────────┘ │
           ▲                │        ChromaDB/FAISS        │
           │                └──────────────────────────────┘
           │                             ▲
           └─────────────────────────────┘
                    Heartbeat/Corrections
                  ┌─────────────────────┐
                  │   APScheduler       │
                  │  - Sync conflicts   │
                  │  - Deprecate chunks │
                  │  - Maintenance      │
                  └─────────────────────┘
```

## Design Principles

### 1. Canonical Truth (Shadow Memory First)
- SQLite KV is always authoritative for identity, preferences, rules
- Vector search results are **suggestions** that get overridden by KV facts
- Example: Vector says "favorite color: blue" but KV says "purple" → Answer is purple

### 2. Exact Casing Preservation
- Store both normalized key and original casing
- Responses use exact original casing: "displayName" not "displayname"
- Critical for proper names, technical terms, classroom examples

### 3. Audit Trail (Episodic Memory)
- Every operation logged with actor, action, payload, timestamp
- Human-readable audit trail for FERPA compliance
- Debug visibility without compromising privacy

### 4. Human-in-the-Loop Gates
- Critical corrections require approval
- Stage gates prevent premature advancement
- Classroom transparency and learning opportunities

### 5. Privacy by Design
- Sensitive flag for PII redaction
- DEBUG controls exposure of internal state
- Air-gapped operation (no external calls required)
- Local-first data storage

## Memory Operation Types

### Identity & Preferences (Canonical - KV Only)
```python
# Always authoritative, never guessed
kv.set("displayName", "Mark Snow", source="user")
kv.set("pronouns", "he/him", source="user") 
kv.set("accommodation", "large_font", source="system")
```

### Documents & Context (Semantic - Vector + KV Overlay)
```python
# Store in vector for semantic search
vector.add_chunks(document_text, metadata={user_id, source, reliability})

# Query: "What did I say about Python?"
vector_results = vector.search("Python discussion")
kv_overrides = kv.get_relevant_keys(vector_results)
final_answer = apply_overlay(vector_results, kv_overrides)
```

### Corrections (Sync Layer)
```python
# When KV contradicts vector memory
if kv.get("favorite_color") == "purple" and vector_suggests("blue"):
    corrections.enqueue("deprecate_conflicting_chunks", 
                       query="favorite color blue", 
                       replace_with="favorite color purple")
```

## Deployment Characteristics

### Educational/Classroom Optimized
- Easy setup: `cp .env.example .env && make dev`
- Interactive documentation (Swagger/Redoc)
- Structured logging for learning
- Human-readable audit trails

### Privacy & Compliance
- FERPA-friendly audit logs
- Sensitive data redaction controls
- Air-gapped operation capability
- Local SQLite storage

### Low-Resource Friendly
- SQLite requires minimal resources
- Vector operations tunable by "metabolism"
- Graceful degradation on weak hardware
- CPU-only operation (no GPU required)

## Next Stage Previews

### Stage 2: Vector Integration
- ChromaDB or FAISS persistence
- Local embedding models (E5-small, SentenceTransformers)
- Basic semantic search with metadata

### Stage 3: Heartbeat System
- APScheduler for periodic corrections
- Conflict detection and resolution
- Vector hygiene (deprecation, compaction)

### Stage 4: RAG + Overlay
- Multi-layer read logic
- KV overrides vector results
- Executor post-checks for accuracy

### Stage 5-7: Advanced Features
- Human approval workflows
- TUI dashboard
- Backup/restore, maintenance automation

## Why This Architecture Works

1. **Eliminates Context Drift**: Canonical facts cannot be corrupted by semantic approximation
2. **Maintains Flexibility**: Vector search provides rich context while KV ensures accuracy
3. **Educational Transparency**: Every operation audited and explainable
4. **Privacy Compliant**: Local-first with granular redaction controls
5. **Collaborative Friendly**: Human gates ensure quality and learning opportunities

This architecture provides the foundation for reliable, private, educational AI memory systems that can scale from proof-of-concept to production classroom deployment.