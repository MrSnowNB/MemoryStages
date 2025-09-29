# Stage 4 - Completion & Enhancement Plan

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
