# Stage 2 - Complete ✅
**Status:** Complete (2025-10-11) - Full semantic memory implementation with FAISS vectors, provenance tracking, and swarm orchestration support.

## Stage 3 - Bot Swarm Orchestration ✅
**Status:** Active - Implementing multi-agent swarm with planning, tool use, provenance tracking, and safety guardrails.

## Stage 3 Implementation Plan

### 1. Define and Implement Multi-Agent Swarm Components
**Status:** Planned - Need to implement 5 core agents
- [ ] `src/agents/orchestrator.py` - Main entry point, coordinates swarm execution
- [ ] `src/agents/manager.py` - Planning logic, step-by-step reasoning
- [ ] `src/agents/memory_agent.py` - Semantic/KV retrieval + conflict resolution
- [ ] `src/agents/reasoner.py` - Answer synthesis with citation handling
- [ ] `src/agents/safety.py` - Prompt injection and safety validation checks

### 2. Design Agent Action Protocol and ToolRouter
**Status:** Planned - Centralized tool coordination
- [ ] `src/agents/tools.py` - Tool registry implementation
- [ ] ToolRouter service with semantic.query, kv.get/kv.set, math.eval
- [ ] Comprehensive tool call/result logging to DAO
- [ ] KV write guardrails (orchestrator permission required)

### 3. Expand Shadow Ledger for Swarm Provenance
**Status:** Planned - Event logging for auditability
- [ ] Extend `src/core/dao.py` with conversation-scoping
- [ ] Add swarm event types: swarm_plan, tool_call, tool_result, reconciliation, safety_blocked, finalize_response
- [ ] Conversation ID and turn ID tracking for all events

### 4. Implement Working Memory Scratchpad
**Status:** Planned - Request-scoped memory
- [ ] `src/core/working_memory.py` - Temporary storage for current turn
- [ ] Agent intermediate result storage
- [ ] Automatic flushing after response composition

### 5. Hard-code Guardrails and Policies
**Status:** Planned - Safety and consistency enforcement
- [ ] `src/core/reconcile.py` - KV-wins enforcement implementation
- [ ] `src/agents/policy.py` - Policy definitions and enforcement
- [ ] Conflict detection and recording
- [ ] Sensitive data redaction and injection blocking

### 6. Integrate with Backend API
**Status:** Planned - Connect orchestrator to chat endpoint
- [ ] Update `src/api/main.py` - Connect orchestrator to POST /chat
- [ ] `src/api/schemas.py` - Add swarm response/ledger/event schemas
- [ ] Populate responses with answer, provenance, and swarm timeline

### 7. Update UI for Swarm Status, Timeline, and Badges
**Status:** Planned - Enhanced UI components
- [ ] Swarm plan and agent action timeline display
- [ ] Provenance and conflict badges
- [ ] Safety status indicators
- [ ] Real-time swarm execution visualization

### 8. Implement and Run Test Suite
**Status:** Planned - Comprehensive testing
- [ ] `tests/test_chat_swarm_end_to_end.py` - Full integration tests
- [ ] `tests/test_tools_router.py` - Tool coordination testing
- [ ] `tests/test_working_memory.py` - Scratchpad validation
- [ ] `tests/test_safety_agent.py` - Security testing
- [ ] `tests/test_conflict_logging.py` - Audit trail validation

### 9. Health Monitoring
**Status:** Planned - Swarm component monitoring
- [ ] Extend /health with swarm component status
- [ ] Update UI to show swarm and semantic health
- [ ] Component availability indicators

## Stage 3 Exit Criteria
- [ ] Manual test: "What is my name, favorite color, and how do I feel about blue?" shows full swarm orchestration
- [ ] Response shows provenance, KV-wins enforcement, conflict notifications
- [ ] Backend ledger shows: plan → tool calls → reconciliation → safety → finalize_response
- [ ] UI displays timeline and all badges/indicators
- [ ] All agents/actions/ provenance are auditable
- [ ] Safety/privacy guardrails strictly enforced
- [ ] System shows "Stage 3 Complete" in health status

## Stage 4 - Completion & Enhancement Plan

**Status:** Active - Building on Stages 1-3 foundation with privacy/audit controls merged early

## Overview
Enhance system with heartbeat/sync/consistency, monitoring/telemetry, robust backup/restore, episodic memory foundation, resilience/qa, and comprehensive documentation to prepare for Stage 5 advanced memory.

## Implementation Areas

### 1. Heartbeat, Sync, and Consistency Layer
**Goal:** Ensure KV and FAISS stores always remain in sync through automated background processes

- [x] Create `scripts/heartbeat.py` - Background service that checks and maintains KV-FAISS consistency (exists from Stage 3)
- [x] Implement heartbeat data walker that identifies missing/outdated vectors (drift_rules.py enhanced with vector audit)
- [x] Enhanced vector stores to store metadata (updated_at) for proper drift detection
- [x] Implemented proper vector audit functionality in drift_rules.py
- [x] Create admin API endpoints for vector re-indexing (POST /admin/reindex_vectors) and health (GET /memory/health)
- [x] Configure heartbeat interval and report destinations via environment variables (using existing config)
- [ ] Add on-startup vector sync health checks

### 2. Monitoring, Health, and System Telemetry
**Goal:** Expose operational status for admin confidence, transparency, and troubleshooting

- [x] Extend memory health dashboard (web interface) showing KV/vector counts and last heartbeat
- [x] Add vector status display - loaded model, FAISS index status, embedding provider
- [x] Create API status endpoints (`/health`, `/memory/health`) returning operational JSON
- [ ] Enhance TUI with access & audit logs panel for admins to review system events
- [ ] Add out-of-sync alerting in dashboard when vector/KV counts drift

### 3. Automated & Manual Backup/Restore
**Goal:** Bulletproof, privacy-compliant backup/restore system with scheduled capabilities

- [ ] Extend `scripts/backup.py` and `scripts/restore.py` CLI with vector data backup/restore
- [x] Ensure privacy redaction applied to backups containing sensitive KV data (already implemented)
- [ ] Add scheduled export capabilities for regular (daily/weekly) vector + SQLite backups
- [ ] Implement restore verification process with automatic vector re-embedding after restore
- [ ] Add email/alert integration points for backup completion/failure notifications

### 4. Episodic & Summary Memory (Begin Stage 5 Integration)
**Goal:** Start building temporal memory foundation for advanced memory capabilities

- [ ] Extend episodic table logging to capture chat interactions (query/response pairs)
- [ ] Implement "summarize my past interactions" functionality returning recent session transcripts
- [ ] Create API endpoints (`/episodic/recent?limit=50`) for session-level memory review/QA
- [ ] Add temporal correlation between KV entries and episodic interaction history
- [ ] Ensure episodic events include proper timestamps for temporal memory queries

### 5. Resilience, Migration & Human-in-the-Loop QA
**Goal:** Ensure system is robust across upgrades, errors, and admin workflows

- [ ] Create migration infrastructure (Alembic or manual SQL) for future schema changes
- [ ] Update README/CHANGELOG with safe upgrade procedures and data migration instructions
- [ ] Extend smoke tests to include sync consistency, backup-restore, and privacy scenarios
- [ ] Add automated nightly test target (GitHub Action or local cron) for regression testing
- [ ] Implement dry-run and staged deployment capabilities for admin safety

### 6. Documentation, Tutorials, and Teaching Aids
**Goal:** Complete, reproducible classroom/teacher materials and audit resources

- [ ] Update `STAGE_CHECKS.md` with comprehensive checklists for heartbeat, sync, health, backup features
- [ ] Create "how it works" diagrams and flowcharts for memory sync processes and troubleshooting
- [ ] Add "debugging memory sync" guides for students/teachers diagnosing consistency issues
- [ ] Update classroom teaching materials with heartbeat monitoring and backup procedures
- [ ] Create teacher onboarding materials covering system health monitoring and maintenance

## Exit Criteria (Stage 4 Readiness for Advanced Memory)

### Automation & Consistency
- [ ] All KV-FAISS sync, heartbeat, and repair tools work reliably
- [ ] Automated nightly testing prevents regressions
- [ ] Backup/restore operates without data loss or sync issues

### Monitoring & Observability
- [ ] GUI and API fully expose sync/health status for admin confidence
- [ ] System alerts admins to inconsistencies or failures
- [ ] Health endpoints provide operational insights for dashboards/scripts

### Privacy & Compliance
- [ ] All backup operations respect privacy redaction rules
- [ ] Audit trails maintain compliance across new heartbeat/sync operations
- [ ] Sensitive data protections extend to new backup and monitoring features

### Memory Foundation
- [ ] Episodic logging captures interaction history for Stage 5 memory building
- [ ] Recent interaction summary capability demonstrated
- [ ] Temporal memory query foundation established

### Documentation & Teaching
- [ ] Developer documentation covers all heartbeat/sync/monitoring features
- [ ] Teacher guides include system health monitoring and troubleshooting
- [ ] Classroom materials demonstrate vector consistency and backup procedures

### Quality Assurance
- [ ] All tests remain green after stress/migration/restore scenarios
- [ ] Performance acceptable with automated consistency checking
- [ ] Human-in-the-loop QA procedures documented and verified

## Success Metrics

**Reliability:** Zero data inconsistency events in monitored operation
**Monitoring:** Full visibility into vector health, sync status, backup completion
**Maintenance:** Automated processes prevent manual intervention for sync/backup
**Memory Foundation:** Episodic data collection ready for advanced memory features
**Education:** Complete teacher/dev materials for operational confidence

---

**Stage 4 Complete → Ready for Stage 5 Advanced Memory & LLM Integration**
