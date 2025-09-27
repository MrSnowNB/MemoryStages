# STAGE 3 LOCKDOWN: Heartbeat, Drift Detection, and Correction

**⚠️ STAGE 3 SCOPE ONLY - DO NOT IMPLEMENT BEYOND THIS BOUNDARY ⚠️**

## Prerequisites

- Stage 1 is **COMPLETE** and **HUMAN-APPROVED**
- Stage 2 is **COMPLETE** and **HUMAN-APPROVED**
- All Stage 1/2 tests pass with vector features enabled/disabled
- Stage 2 gate documented in `docs/STAGE_CHECKS.md`
- Python 3.10 environment

## Stage 3 Objectives (LOCKED SCOPE)

Implement **minimal, feature-flagged maintenance loop** that audits canonical SQLite KV vs. vector overlay and enforces consistency rules:

✅ **IN SCOPE**:
- Heartbeat loop with task registry (cooperative, no threads)
- Drift detection rules comparing SQLite KV to vector store
- Correction proposal system with typed actions
- Reversible correction application engine
- Comprehensive episodic logging for all operations
- Manual verification and safety controls

🚫 **OUT OF SCOPE** (FUTURE STAGES):
- Agent orchestration or LLM-based corrections
- Cron/systemd integration or external schedulers
- UI/TUI dashboards or monitoring interfaces
- Schema changes to Stage 1 KV/episodic tables (beyond episodic payload usage)
- Cloud services or external dependencies
- Threading or async frameworks beyond cooperative scheduling
- Advanced ML-based drift detection
- Complex correction strategies beyond basic sync

## Critical Constraints (ANTI-DRIFT SAFEGUARDS)

### Behavioral Constraints
- **Default flags keep Stage 1/2 behavior identical** when heartbeat disabled
- **SQLite remains canonical source of truth** - corrections sync vector to SQLite, never reverse
- **No schema changes to Stage 1 tables** - only use existing episodic logging
- **Sensitive data never processed** in drift detection or corrections
- **Tombstones respected** - orphaned vectors removed, never restored
- **Reversible actions only** - corrections can be undone where feasible

### Implementation Constraints
- **Python 3.10 compatibility required**
- **No threading or external schedulers** - cooperative loop only
- **Feature flags control all behavior** - dark by default
- **Local-first operation** - no network dependencies
- **Minimal dependencies** - use existing libraries only

## Environment and Configuration Flags

### Required Configuration Variables (.env)
```bash
# Heartbeat system controls (default: disabled)
HEARTBEAT_ENABLED=false           # Master switch for heartbeat loop
HEARTBEAT_INTERVAL_SEC=60         # Default task interval in seconds
CORRECTION_MODE=propose           # off|propose|apply (propose for safety)
DRIFT_RULESET=strict             # strict|lenient (strict for safety)

# Existing Stage 1/2 flags (unchanged)
VECTOR_ENABLED=false
SEARCH_API_ENABLED=false
VECTOR_PROVIDER=memory
EMBED_PROVIDER=hash
DB_PATH=./data/memory.db
DEBUG=true
```

### Flag Behavior Matrix
| HEARTBEAT_ENABLED | CORRECTION_MODE | Behavior |
|-------------------|-----------------|----------|
| false | * | **Stage 1/2 identical** - no heartbeat operations |
| true | off | Heartbeat runs, detects drift, logs only |
| true | propose | Heartbeat detects drift, proposes corrections, no changes |
| true | apply | **Full Stage 3** - detects and applies corrections |

### Correction Mode Details
- **off**: Drift detection runs, findings logged, no correction proposals
- **propose**: Generate correction plans, log episodic events, no database changes  
- **apply**: Execute correction plans against vector store, log all actions

## File Touch Policy (STRICT)

### Allowed Files for Stage 3 ONLY
```
src/core/config.py              (modify - add heartbeat flags)
src/core/heartbeat.py           (create - heartbeat loop and task registry)
src/core/drift_rules.py         (create - drift detection and correction planning)
src/core/corrections.py         (create - correction application and reversal)
src/util/logging.py             (modify - add heartbeat/drift/correction logs)
scripts/run_heartbeat.py        (create - heartbeat entrypoint script)
tests/test_heartbeat.py         (create - heartbeat loop tests)
tests/test_drift_rules.py       (create - drift detection tests)
tests/test_corrections.py       (create - correction engine tests)
docs/STAGE_CHECKS.md            (modify - add Stage 3 gate checklist)
docs/HEARTBEAT.md               (create - heartbeat documentation)
```

### VIOLATION POLICY
**Editing any other files is SCOPE CREEP** and requires immediate rollback.

### File Header Requirement
All new files must include:
```python
"""
Stage 3 scope only. Do not implement beyond this file's responsibilities.
Heartbeat and drift correction - maintains vector overlay consistency with canonical SQLite.
"""
```

## Stage 3 Implementation Plan

### Core Deliverable 1: Heartbeat Loop System

**Files**:
- `src/core/heartbeat.py` (create)
- `scripts/run_heartbeat.py` (create)
- `tests/test_heartbeat.py` (create)

**Heartbeat Loop Requirements**:
```python
# src/core/heartbeat.py interface
def register_task(name: str, interval_sec: int, func: Callable) -> None
def start() -> None  # Cooperative loop using time.monotonic()
def stop() -> None   # Clean shutdown
```

**Implementation Specifications**:
- **Cooperative scheduling only** - no threads or async frameworks
- **Feature flag respect** - no-op if `HEARTBEAT_ENABLED=false`
- **Graceful shutdown** on stop() call or KeyboardInterrupt
- **Structured logging** for each task execution with timing and status
- **Task registry** allowing multiple tasks with different intervals
- **Error isolation** - one task failure doesn't stop loop

**Script Requirements**:
- `scripts/run_heartbeat.py` starts loop if `HEARTBEAT_ENABLED=true`
- Registers core "drift_audit" task with `HEARTBEAT_INTERVAL_SEC` interval
- Handles KeyboardInterrupt gracefully
- Provides basic status logging

### Core Deliverable 2: Drift Detection Rules

**Files**:
- `src/core/drift_rules.py` (create)
- `tests/test_drift_rules.py` (create)

**Data Structures**:
```python
@dataclass
class DriftFinding:
    id: str
    type: str  # 'missing_vector', 'stale_vector', 'orphaned_vector'
    severity: str  # 'low', 'medium', 'high'
    kv_key: str
    details: dict

@dataclass
class CorrectionAction:
    type: str  # 'ADD_VECTOR', 'UPDATE_VECTOR', 'REMOVE_VECTOR'
    key: str
    metadata: dict

@dataclass
class CorrectionPlan:
    id: str
    finding_id: str
    actions: list[CorrectionAction]
    preview: dict
```

**Detection Rules**:
1. **MissingVectorForNonSensitiveKV**: 
   - KV exists, non-sensitive, non-tombstoned, but no vector entry
   - Action: `ADD_VECTOR`

2. **StaleVectorEmbedding**:
   - KV `updated_at` > vector `updated_at` (any difference)
   - Action: `UPDATE_VECTOR` (re-embed and update)

3. **OrphanedVectorEntry**:
   - Vector entry exists but KV is tombstoned or missing
   - Action: `REMOVE_VECTOR`

**Ruleset Severity**:
- **strict**: All findings = high severity
- **lenient**: Missing/Stale = medium, Orphaned = low

### Core Deliverable 3: Corrections Engine

**Files**:
- `src/core/corrections.py` (create)
- `tests/test_corrections.py` (create)

**Correction Application**:
```python
def apply_corrections(plans: list[CorrectionPlan], mode: str) -> list[dict]:
    # mode: 'off' | 'propose' | 'apply'
    
def revert_correction(plan_id: str) -> dict:
    # Best-effort reversal with limitations documented
```

**Correction Mode Behavior**:
- **off**: No-ops, log preview information only
- **propose**: Write episodic events with correction plans, no database changes
- **apply**: Execute corrections against vector store, log all actions

**Episodic Event Integration**:
- Use existing Stage 1 episodic logging (no schema changes)
- Event types: `drift_detected`, `correction_proposed`, `correction_applied`, `correction_reverted`
- Comprehensive payload with plan IDs, action summaries, and metadata

### Core Deliverable 4: Integration and Configuration

**Files**:
- `src/core/config.py` (modify - add flags)
- `src/util/logging.py` (modify - add structured logging)

**Configuration Integration**:
- Add heartbeat flags to existing config system
- Validate flag combinations (e.g., correction requires vector enabled)
- Provide sensible defaults for educational/development use

**Logging Extensions**:
- Structured logs for heartbeat task execution
- Drift detection findings with severity and details  
- Correction proposals and applications with timing
- Error handling and task failure isolation

### Core Deliverable 5: Documentation and Verification

**Files**:
- `docs/HEARTBEAT.md` (create)
- `docs/STAGE_CHECKS.md` (modify - add Stage 3 section)

**Documentation Requirements**:
- Heartbeat loop explanation and operational guidance
- Drift detection rules and severity mappings
- Correction modes and safety guarantees
- Manual verification procedures
- Flag interaction matrix and troubleshooting

## Testing Strategy

### Unit Testing Requirements

**test_heartbeat.py**:
```python
def test_heartbeat_disabled_when_flag_off():
    # Verify no execution when HEARTBEAT_ENABLED=false

def test_task_registration_and_execution():
    # Mock time, register dummy task, verify call counts

def test_graceful_shutdown():
    # Verify clean stop() behavior and KeyboardInterrupt handling
```

**test_drift_rules.py**:
```python
def test_detect_missing_vector_drift():
    # KV exists, non-sensitive, no vector -> MissingVector finding

def test_detect_stale_vector_drift():
    # KV updated_at > vector updated_at -> StaleVector finding

def test_detect_orphaned_vector_drift():
    # Vector exists, KV tombstoned -> OrphanedVector finding

def test_drift_ruleset_severity():
    # Verify strict vs lenient severity assignments
```

**test_corrections.py**:
```python
def test_correction_mode_off():
    # Verify no database changes, only logging

def test_correction_mode_propose():
    # Verify episodic events written, no vector changes

def test_correction_mode_apply():
    # Verify vector operations executed, events logged

def test_correction_reversal():
    # Test revert_correction() where feasible
```

### Integration Testing

**Stage 1/2 Regression**:
```bash
# Must pass with heartbeat disabled
HEARTBEAT_ENABLED=false pytest tests/test_smoke.py -v
HEARTBEAT_ENABLED=false VECTOR_ENABLED=true pytest tests/test_search_service.py -v
```

**Stage 3 Feature Testing**:
```bash
# Heartbeat loop functionality
HEARTBEAT_ENABLED=true pytest tests/test_heartbeat.py -v

# Drift detection with different rulesets
DRIFT_RULESET=strict pytest tests/test_drift_rules.py -v
DRIFT_RULESET=lenient pytest tests/test_drift_rules.py -v

# Correction modes
CORRECTION_MODE=off pytest tests/test_corrections.py -v
CORRECTION_MODE=propose pytest tests/test_corrections.py -v
CORRECTION_MODE=apply pytest tests/test_corrections.py -v
```

## Manual Verification Procedure

### Setup Test Data
```bash
# Enable vector system with test data
VECTOR_ENABLED=true VECTOR_PROVIDER=memory EMBED_PROVIDER=hash make dev

# Create test KV entries
curl -X PUT http://localhost:8000/kv -d '{"key":"test1","value":"hello","source":"user"}'
curl -X PUT http://localhost:8000/kv -d '{"key":"test2","value":"world","source":"user"}'

# Simulate drift by manual vector removal/modification
# (Implementation-specific based on vector store interface)
```

### Verification Steps
```bash
# Step 1: Propose mode
HEARTBEAT_ENABLED=true CORRECTION_MODE=propose DRIFT_RULESET=strict \
    python scripts/run_heartbeat.py

# Verify: episodic events show drift_detected and correction_proposed
# Verify: no actual changes to vector store

# Step 2: Apply mode  
HEARTBEAT_ENABLED=true CORRECTION_MODE=apply DRIFT_RULESET=strict \
    python scripts/run_heartbeat.py

# Verify: correction_applied events logged
# Verify: vector store synchronized with SQLite KV state

# Step 3: Disable and verify Stage 1/2 behavior
HEARTBEAT_ENABLED=false make dev
# Follow original Stage 1/2 API quickstart - should work identically
```

## Safety and Privacy Guarantees

### Data Protection
- **Sensitive data never processed**: Drift detection skips sensitive=1 keys
- **Tombstone respect**: Orphaned vectors removed, tombstoned KV never restored
- **Canonical authority**: SQLite KV values never changed by corrections
- **Redaction compliance**: Correction logs respect DEBUG flag for sensitive info

### Operational Safety
- **Reversible actions**: Corrections can be undone where technically feasible
- **Comprehensive logging**: All operations logged to episodic events
- **Feature flag safety**: Default configuration prevents unintended activation
- **Error isolation**: Task failures don't crash the heartbeat loop

### Development Safety
- **No schema changes**: Uses existing episodic logging only
- **Minimal dependencies**: No new external libraries required
- **Cooperative scheduling**: No threading complexity or race conditions
- **Clean shutdown**: Graceful stop on interruption

## Hard Gate Criteria (COMPLETION REQUIREMENTS)

### Automated Test Gates
- [ ] **All Stage 1/2 regression tests pass** with `HEARTBEAT_ENABLED=false`
- [ ] **All Stage 3 unit tests pass** for heartbeat, drift rules, and corrections
- [ ] **Flag combination tests pass** for all correction modes and rulesets
- [ ] **Privacy tests pass** - sensitive data never processed in drift detection

### Manual Verification Gates
- [ ] **Heartbeat loop runs** when enabled, stops cleanly on interruption
- [ ] **Drift detection works** - finds missing, stale, and orphaned entries
- [ ] **Correction modes behave correctly** - off/propose/apply as specified
- [ ] **Episodic logging comprehensive** - all operations produce audit events
- [ ] **Stage 1/2 behavior preserved** when heartbeat disabled

### Documentation Gates
- [ ] **HEARTBEAT.md complete** - operational guidance and safety guarantees
- [ ] **Stage 3 section in STAGE_CHECKS.md** - comprehensive gate checklist
- [ ] **Manual verification procedure** documented and tested
- [ ] **Flag interaction matrix** documented with examples

### Code Review Gates
- [ ] **File touch policy respected** - only allowed files modified/created
- [ ] **Scope banners present** - all new files include Stage 3 scope warning
- [ ] **Feature flag guards** - all new behavior controlled by configuration
- [ ] **Error handling robust** - failures don't crash heartbeat loop
- [ ] **Logging structured** - consistent format for operations and errors

## Rollback and Recovery

### Rollback Procedure
If any gate fails:
1. **Stop development immediately**
2. **Revert all changes** to files in allowed modification list
3. **Verify Stage 1/2 tests still pass**
4. **Fix issues within Stage 3 scope only**
5. **Re-test all gates before proceeding**

### Recovery Scenarios
- **Heartbeat loop crashes**: Logs show error, manual restart required
- **Correction failures**: Revert operations logged, manual investigation needed
- **Drift detection errors**: Skip problematic entries, log warnings
- **Configuration conflicts**: Validate and document flag dependencies

## Stage 3 Success Metrics

### Functional Success
- ✅ **Heartbeat loop operates reliably** with configurable task scheduling
- ✅ **Drift detection identifies inconsistencies** between SQLite and vector store
- ✅ **Correction system maintains consistency** without overriding canonical data
- ✅ **Comprehensive logging enables audit** of all maintenance operations

### Safety Success  
- ✅ **Default configuration preserves existing behavior** (dark by default)
- ✅ **Sensitive data protection maintained** throughout all operations
- ✅ **Reversible operations where feasible** with documented limitations
- ✅ **Error isolation prevents system disruption** from task failures

### Integration Success
- ✅ **Stage 1/2 functionality unchanged** when heartbeat disabled
- ✅ **Vector overlay consistency improved** through automatic maintenance
- ✅ **Educational transparency maintained** through comprehensive logging
- ✅ **Operational simplicity preserved** with feature flag controls

---

**⚠️ STAGE 3 LOCKDOWN COMPLETE - NO IMPLEMENTATION BEYOND THIS SCOPE ⚠️**

This document defines the complete, gated execution plan for Stage 3. Any implementation beyond these specifications constitutes scope creep and requires document revision and re-approval. Upon successful completion of all gates, Stage 3 will provide automated maintenance capabilities while preserving the safety, privacy, and educational value of the foundational stages.