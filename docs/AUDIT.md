# Audit Trail Documentation

**Stage 4 scope only. Do not implement beyond this file's responsibilities.**

Audit trail documentation - ensures comprehensive logging and compliance for approval workflows and schema validation operations.

## Overview

The audit trail system provides comprehensive tracking and logging of all approval workflows, schema validation operations, and sensitive actions within the Memory Stages system. Audit logs enable compliance verification, troubleshooting, and operational monitoring while maintaining strict privacy controls for sensitive data.

## Audit Events

### Approval Workflow Events

**Approval Request Creation**
```json
{
  "event_type": "approval_request_created",
  "request_id": "uuid-string",
  "request_type": "correction|data_operation",
  "requester": "user_identifier",
  "timestamp": "2025-09-27T12:29:00Z",
  "sensitive_payload": false
}
```

**Approval Decision**
```json
{
  "event_type": "approval_decision",
  "request_id": "uuid-string",
  "decision": "approved|rejected|expired",
  "approver": "approver_identifier",
  "reason": "approval reason text",
  "timestamp": "2025-09-27T12:30:00Z"
}
```

**Approval Bypass**
```json
{
  "event_type": "approval_bypass",
  "request_id": "uuid-string",
  "reason": "system_config|fallback_policy",
  "timestamp": "2025-09-27T12:29:30Z"
}
```

### Schema Validation Events

**Validation Success**
```json
{
  "event_type": "schema_validation_success",
  "operation": "set_key|get_key|add_event",
  "target_identifier": "key_or_event_id",
  "validation_level": "strict|relaxed",
  "source": "api|internal",
  "timestamp": "2025-09-27T12:29:00Z"
}
```

**Validation Failure**
```json
{
  "event_type": "schema_validation_failure",
  "operation": "set_key|get_key|add_event",
  "target_identifier": "key_or_event_id (if available)",
  "error_type": "field_validation|type_mismatch|constraint_violation",
  "field_name": "affected_field_name",
  "error_details": "sanitized_error_description",
  "source": "api|internal",
  "timestamp": "2025-09-27T12:29:00Z"
}
```

**Validation Bypass**
```json
{
  "event_type": "validation_bypass",
  "operation": "set_key|get_key|add_event",
  "reason": "feature_disabled|legacy_data|admin_override",
  "target_identifier": "key_or_event_id",
  "timestamp": "2025-09-27T12:29:00Z"
}
```

### Correction Operation Events

**Correction Applied**
```json
{
  "event_type": "correction_applied",
  "correction_id": "uuid-string",
  "correction_type": "ADD_VECTOR|UPDATE_VECTOR|REMOVE_VECTOR",
  "target_key": "key_identifier",
  "drift_finding_id": "drift_finding_uuid",
  "success": true,
  "metadata": {"reason": "drift_detected", "severity": "high"},
  "timestamp": "2025-09-27T12:29:00Z"
}
```

**Correction Blocked**
```json
{
  "event_type": "correction_blocked",
  "correction_id": "uuid-string",
  "correction_type": "correction_type",
  "target_key": "key_identifier",
  "block_reason": "approval_pending|approval_denied|validation_failure",
  "approval_request_id": "approval_uuid (if applicable)",
  "timestamp": "2025-09-27T12:29:00Z"
}
```

## Audit Log Levels

### minimal
- Only error conditions and approval decisions
- No detailed operation logging
- Suitable for basic compliance requirements

### standard
- All approval workflow events
- Major validation failures and corrections
- Sensitive operation logging without payload details
- Balance between visibility and performance

### verbose
- Complete operation audit trail
- Detailed error information
- Request/response correlation IDs
- Maximum operational visibility

## Privacy Controls

### Sensitive Data Handling

**Payload Sanitization**
- Sensitive field values are never logged
- Key identifiers are safe if not marked sensitive
- Error messages use generic descriptions for sensitive fields

**Field-Level Privacy**
```python
# Example: KV record with sensitive field
sensitive_record = {
    "key": "user_ssn_123",
    "value": "941-55-1234",  # WON'T be logged
    "sensitive": true
}

# Audit log entry
{
  "event_type": "set_key_success",
  "key_identifier": "user_ssn_123",  # SAFE - identifier only
  "sensitive": true,
  "source": "encrypted_upload"  # SAFE - metadata only
}
```

**Log Field Categories**

Safe to log:
- Identifiers (keys, IDs, UUIDs)
- Metadata (timestamps, operation types, status values)
- Configuration flags (strict mode on/off, approval enabled/disabled)
- Generic error types (validation_failed, permission_denied)

Never log:
- Sensitive field values
- Full request payloads unless sanitized
- Personal identifiable information (PII)
- Cryptographic material (keys, tokens, secrets)

## Compliance Features

### Audit Log Integrity

**Tamper-Evident Logging**
- Each log entry includes cryptographic hash of previous entry
- Log file checksums verified on read
- Append-only log files prevent modification

**Log Sequence Verification**
```python
def verify_log_sequence(log_entries):
    """Verify no entries have been removed or modified."""
    previous_hash = None
    for entry in log_entries:
        calculated_hash = hash_entry(entry['data'])
        if entry['previous_hash'] != previous_hash:
            raise AuditIntegrityError("Log sequence broken")
        previous_hash = calculated_hash
```

### Retention Policies

**Standard Retention**
- Approval workflow logs: 3 years minimum
- Validation error logs: 2 years minimum
- General operation logs: 1 year minimum

**Compliance-Specific Retention**
- Sensitive operation logs: 5 years minimum
- Regulatory compliance logs: 7 years minimum (varies by regulation)

### Export and Analysis

**Log Export Formats**
- JSON Lines (.jsonl) for programmatic processing
- CSV for spreadsheet analysis
- PDF reports for compliance documentation

**Analysis Procedures**
```bash
# Find all approval rejections in last 30 days
grep "approval_decision.*rejected" audit.log \
  | jq '.timestamp | select(. > "2025-08-27")'

# Count validation failures by error type
grep "schema_validation_failure" audit.log \
  | jq -r '.error_type' | sort | uniq -c
```

## Operational Procedures

### Log Monitoring

**Alert Conditions**
- Audit log integrity failures
- Approval workflow bypass detections
- High frequency validation errors
- Log file size growth anomalies

**Monitoring Scripts**
```python
def check_audit_integrity():
    """Verify audit log chain of trust."""
    log_entries = read_audit_log()
    try:
        verify_log_sequence(log_entries)
        print("✅ Audit log integrity verified")
    except AuditIntegrityError as e:
        alert_admin(f"🚨 Audit integrity failure: {e}")

def check_approval_compliance():
    """Verify approval workflow compliance."""
    recent_approvals = find_recent_approvals(hours=24)
    if len(recent_approvals) < expected_minimum:
        alert_admin("⚠️ Approval activity below thresholds")
```

### Troubleshooting with Audit Logs

**Finding Root Causes**
```bash
# Find all operations for a specific key
grep '"target_key":"problematic_key"' audit.log | jq

# Trace approval workflow for a correction
grep '"correction_id":"correction-uuid"' audit.log | jq '.event_type'
```

**Performance Analysis**
```bash
# Identify slow validation operations
grep "validation_success" audit.log | jq '.operation, .duration_ms'
```

### Compliance Verification

**Regular Audits**
1. Pull quarterly audit log exports
2. Verify retention compliance
3. Review approval workflow usage
4. Check for security incidents evidence
5. Document compliance status

**Incident Response**
1. Isolate relevant audit logs for incident timeframe
2. Analyze sequence of events
3. Document findings for compliance reporting
4. Implement corrective actions
5. Update audit procedures based on lessons learned

## Security Considerations

### Log Access Controls
- Audit logs require elevated permissions
- Read-only access even for administrators
- Access attempts logged in security audit stream
- Multi-party authorization for log exports

### Storage Security
- Encrypted at-rest storage
- Tamper-evident storage mechanisms
- Backup verification procedures
- Offsite storage for compliance requirements

### Transport Security
- TLS-encrypted log transport
- End-to-end encryption for remote logging
- Message integrity verification
- Replay attack prevention

## Integration Examples

### Application Code
```python
from util.logging import audit_event, sanitize_payload

def set_key_with_audit(key_req: KVSetRequest):
    user_id = get_current_user()

    # Sanitize payload for audit
    safe_payload = sanitize_payload(key_req, reveal_sensitive=False)

    try:
        result = set_key(key_req)

        # Log success
        audit_event("set_key_success", {
            "user": user_id,
            "key": key_req.key,
            "sensitive": key_req.sensitive
        }, safe_payload)

        return result

    except ValidationError as e:
        # Log validation failure
        audit_event("validation_failure", {
            "user": user_id,
            "key": key_req.key,
            "error_type": "validation_error"
        }, {"field_errors": str(e.errors())})

        raise
```

### Configuration
```python
# Environment variables
AUDIT_LEVEL=standard              # minimal|standard|verbose
AUDIT_RETENTION_DAYS=365          # Minimum days to retain logs
AUDIT_ENCRYPTION_ENABLED=true     # Encrypt audit log files
AUDIT_REMOTE_ENABLED=false        # Send logs to remote service
```

## Testing and Verification

### Audit Log Tests
```python
def test_audit_trail_completeness():
    """Ensure all operations are properly logged."""
    # Perform series of operations
    operations = [create_kv, update_with_validation, apply_correction]
    start_time = time.time()

    for op in operations:
        op()

    # Verify audit logs captured all operations
    logs = get_audit_logs(since=start_time)
    assert len(logs) >= len(operations)

    # Verify log integrity
    verify_log_integrity(logs)
```

### Privacy Compliance Tests
```python
def test_sensitive_data_not_logged():
    """Ensure sensitive data never appears in logs."""
    # Create sensitive KV entry
    sensitive_key = KVRecord("secret_key", "classified_data", "internal", True)

    # Perform operation
    set_key(sensitive_key)

    # Verify logs don't contain the sensitive value
    logs = grep_audit_logs("secret_key")
    assert "classified_data" not in str(logs)
    assert "classified_data" not in json.dumps(logs)
```

This audit trail documentation ensures comprehensive compliance, operational visibility, and privacy protection for all Stage 4 approval and validation workflows.
