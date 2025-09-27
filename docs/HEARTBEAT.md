# MemoryStages Heartbeat System Documentation

**Stage 3 Feature Only - Operates with VECTOR_ENABLED=true**

The Heartbeat system implements automated maintenance for MemoryStages vector overlay consistency. It audits the canonical SQLite KV store against the vector index and enforces configurable correction policies.

## Architecture Overview

The heartbeat system consists of three main components:

1. **Heartbeat Loop**: Cooperative scheduling framework for periodic tasks
2. **Drift Detection Rules**: Automated scanning for SQLite/vectors inconsistencies
3. **Correction Engine**: Reversible application of synchronization actions

## Heartbeat Loop System

### Task Registry

Tasks are registered by name with configurable intervals:

```python
from src.core.heartbeat import register_task

register_task("drift_audit", 60, drift_audit_task_function)
```

### Cooperative Scheduling

- Uses `time.monotonic()` for reliable timing
- Sleeps 100ms between task checks (cooperative scheduling)
- Runs until `stop()` called or KeyboardInterrupt received
- Error isolation prevents single task failures from crashing the loop

### Task Execution

```bash
# Start heartbeat with registered tasks
HEARTBEAT_ENABLED=true python scripts/run_heartbeat.py
```

### Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `HEARTBEAT_ENABLED` | `false` | Master switch for heartbeat operations |
| `HEARTBEAT_INTERVAL_SEC` | `60` | Default task interval in seconds |

## Drift Detection Rules

Drift detection compares SQLite KV entries to vector store contents, identifying three types of inconsistencies:

### 1. MissingVectorForNonSensitiveKV
- **Condition**: KV exists, non-sensitive, non-tombstoned, but no vector entry
- **Reason**: Vector creation failed or was skipped
- **Severity**: High (critical data missing)
- **Action**: `ADD_VECTOR` (re-embed and store)

### 2. StaleVectorEmbedding
- **Condition**: KV `updated_at` > vector `updated_at`
- **Reason**: KV updated after vector creation
- **Severity**: Variable (any difference triggers)
- **Action**: `UPDATE_VECTOR` (re-embed and update)

### 3. OrphanedVectorEntry
- **Condition**: Vector exists but KV is tombstoned or missing
- **Reason**: KV deleted but vector not cleaned up
- **Severity**: Low (garbage collection opportunity)
- **Action**: `REMOVE_VECTOR` (delete orphaned vector)

### Ruleset Severity

- **strict**: All findings = high severity
- **lenient**: Missing/Stale = medium, Orphaned = low

### Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `DRIFT_RULESET` | `strict` | `strict` or `lenient` severity assignment |

## Correction Engine

### Correction Modes

| Mode | Behavior | Safety Level |
|------|----------|-------------|
| `off` | Detect and log drift, no corrections | Highest |
| `propose` | Generate correction plans, write episodic events, no changes | High |
| `apply` | Execute correction plans against vector store | Medium |

### Correction Actions

1. **ADD_VECTOR**: Create missing vector entry
   - Embeds KV content → generates vector → stores in index
   - Reversible: `REMOVE_VECTOR` can undo

2. **UPDATE_VECTOR**: Refresh stale vector entry
   - Re-embeds KV content → updates existing vector → removes old
   - Reversible: Restore previous vector (stored in plan)

3. **REMOVE_VECTOR**: Delete orphaned vector entry
   - Removes vector from index
   - Reversible: Restore vector data (requires plan backup)

### Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `CORRECTION_MODE` | `propose` | `off`, `propose`, or `apply` |

## Safety and Privacy Guarantees

### Data Protection
- **Sensitive data never processed**: Skip `sensitive=1` keys entirely
- **Tombstones respected**: Never restore tombstoned KV entries
- **Canonical authority**: SQLite KV values are never modified
- **Privacy preservation**: DEBUG flag controls log detail levels

### Operational Safety
- **Reversible actions**: All corrections can be undone
- **Comprehensive logging**: All operations logged to episodic events
- **Error isolation**: Task failures don't crash heartbeat loop
- **Feature flags**: Default configuration preserves Stage 1/2 behavior

### Reversal Capabilities
- **Best-effort reversal**: Technical limits exist for some actions
- **Plan-based recovery**: Reversal uses stored plan metadata
- **Audit trail**: All reversals logged for traceability

## Operational Procedures

### Manual Verification Testing

1. **Setup test data**:
   ```bash
   VECTOR_ENABLED=true make dev

   # Create test KV entries
   curl -X PUT http://localhost:8000/kv -d '{"key":"test1","value":"hello"}'
   curl -X PUT http://localhost:8000/kv -d '{"key":"test2","value":"world"}'
   ```

2. **Test propose mode**:
   ```bash
   HEARTBEAT_ENABLED=true CORRECTION_MODE=propose python scripts/run_heartbeat.py
   ```

3. **Verify episodic log**:
   - `drift_detected` events show findings
   - `correction_proposed` events show plans
   - No vector store changes

4. **Test apply mode**:
   ```bash
   HEARTBEAT_ENABLED=true CORRECTION_MODE=apply python scripts/run_heartbeat.py
   ```

5. **Verify corrections**:
   - `correction_applied` events logged
   - Vector store synchronized with SQLite

### Monitoring and Health Checks

#### Heartbeat Status
```python
from src.core.heartbeat import get_status

status = get_status()
# Returns: {"status": "running|stopped|disabled", "tasks": {...}}
```

#### Episodic Event Monitoring
- `drift_detected`: New drift findings identified
- `correction_proposed`: Correction plans generated
- `correction_applied`: Corrections executed successfully
- `correction_reverted`: Corrections reversed

#### Common Issues
1. **No heartbeat execution**: Check `HEARTBEAT_ENABLED=true`
2. **Vector operations failing**: Verify `VECTOR_ENABLED=true`
3. **Sensitive data processed**: Check KV entries for `sensitive=0`
4. **Tasks not registering**: Verify heartbeat config validation passes

## Integration with Other Stages

### Stage 1/2 Compatibility
- **Default disabled**: `HEARTBEAT_ENABLED=false` preserves Stage 1/2 behavior
- **Feature additive**: Only extends vector functionality
- **Vector dependency**: Requires `VECTOR_ENABLED=true` for meaningful operation

### Database Schema
- **No schema changes**: Uses existing episodic logging
- **Event types**: `drift_detected`, `correction_proposed`, `correction_applied`, `correction_reverted`
- **Payload structure**: JSON-serialized metadata with plan IDs and action summaries

## Troubleshooting Guide

### Configuration Issues
```bash
# Check heartbeat configuration
python -c "from src.core.config import validate_heartbeat_config; print(validate_heartbeat_config())"
```

### Flag Dependency Matrix
| VECTOR_ENABLED | HEARTBEAT_ENABLED | CORRECTION_MODE | Result |
|----------------|-------------------|-----------------|--------|
| false | false | * | Stage 1 behavior |
| true | false | * | Stage 2 behavior |
| true | true | off | Heartbeat runs, logs findings |
| true | true | propose | Heartbeat generates plans |
| true | true | apply | Full Stage 3 corrections |

### Error Recovery
1. **Heartbeat crashes**: Restart manually, check for configuration errors
2. **Correction failures**: Revert failed plans, investigate vector store issues
3. **Drift detection errors**: Skip problematic entries, log warnings for investigation

## Performance Considerations

### Resource Usage
- **Memory impact**: Minimal (drift detection scans KV once per cycle)
- **CPU impact**: Embedding operations during correction application
- **Disk I/O**: Episodic logging writes for all operations

### Optimization Settings
- **Interval tuning**: Longer intervals reduce resource usage
- **Ruleset selection**: `lenient` ruleset reduces false positives
- **Correction mode**: `propose` mode avoids vector operations during audit

### Monitoring Metrics
- Heartbeat task completion rates
- Drift finding counts by type
- Correction success rates
- Episodic event volume

## Emergency Procedures

### Rollback Steps
1. Set `HEARTBEAT_ENABLED=false`
2. Verify Stage 1/2 behavior resumes
3. Review episodic logs for any applied corrections needing reversal

### Data Loss Recovery
1. Restore database backup if vector corruption suspected
2. Run vector rebuild: `python scripts/rebuild_index.py`
3. Re-enable heartbeat after verification

### Incident Response
- All operations logged to episodic events for audit
- Correction reversals available for most actions
- No permanent data loss from heartbeat operations
