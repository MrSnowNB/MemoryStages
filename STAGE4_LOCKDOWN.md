# STAGE 4 LOCKDOWN: Approval Workflows & Schema Validation

**⚠️ STAGE 4 SCOPE ONLY - DO NOT IMPLEMENT BEYOND THIS BOUNDARY ⚠️**

## Prerequisites

- Stage 1 is **COMPLETE** and **HUMAN-APPROVED**
- Stage 2 is **COMPLETE** and **HUMAN-APPROVED** 
- Stage 3 is **COMPLETE** and **HUMAN-APPROVED**
- All Stage 1/2/3 tests pass with all feature combinations
- Stage 3 gate documented in `docs/STAGE_CHECKS.md`
- Python 3.10 environment

## Stage 4 Objectives (LOCKED SCOPE)

Implement **approval workflows and comprehensive schema validation** for all app-level operations while maintaining existing safety guarantees:

✅ **IN SCOPE**:
- Strict typed validation for all API, KV, vector, and event payloads
- Approval workflow system for corrections and sensitive operations
- Manual and automated approval modes with comprehensive logging
- App-level integration testing with full workflow validation
- Advanced error reporting and audit trail enhancement
- Schema violation handling with transparent error messaging

🚫 **OUT OF SCOPE** (FUTURE STAGES):
- Agent orchestration or automated decision-making beyond explicit approval logic
- UI/TUI dashboards or monitoring interfaces
- Complex workflow engines or state machines beyond basic approval flows
- External approval systems or integrations
- Advanced ML-based validation or approval recommendations
- Real-time notification systems
- Complex role-based access controls
- Multi-user approval chains

## Critical Constraints (ANTI-DRIFT SAFEGUARDS)

### Behavioral Constraints
- **All existing Stage 1/2/3 behavior preserved** when approval features disabled
- **SQLite remains canonical source of truth** - approvals control vector operations only
- **No breaking changes** to existing APIs when approval features disabled
- **Sensitive data protection maintained** throughout approval workflows
- **Feature flags control all new behavior** - approval system dark by default

### Implementation Constraints
- **Python 3.10 compatibility required**
- **Minimal dependencies** - use existing Pydantic and logging infrastructure
- **Schema validation non-breaking** - backward compatibility for existing payloads
- **Approval workflows optional** - system works without approval enabled
- **Local-first operation** - no external approval services

## Environment and Configuration Flags

### Required Configuration Variables (.env)
```bash
# Approval system controls (default: disabled)
APPROVAL_ENABLED=false            # Master switch for approval workflows
APPROVAL_MODE=manual              # manual|auto (manual requires human decision)
APPROVAL_TIMEOUT_SEC=3600         # Request timeout (1 hour default)
SCHEMA_VALIDATION_STRICT=true     # Strict validation mode
AUDIT_LEVEL=standard              # minimal|standard|verbose

# Existing Stage 1/2/3 flags (unchanged)
HEARTBEAT_ENABLED=false
VECTOR_ENABLED=false
SEARCH_API_ENABLED=false
DB_PATH=./data/memory.db
DEBUG=true
```

### Flag Behavior Matrix
| APPROVAL_ENABLED | APPROVAL_MODE | Behavior |
|------------------|---------------|----------|
| false | * | **Stage 1/2/3 identical** - no approval workflows |
| true | manual | Human approval required for corrections |
| true | auto | **Not implemented in Stage 4** - reserved for future |

### Approval Workflow States
- **pending**: Approval request created, awaiting decision
- **approved**: Human/system approved the request
- **rejected**: Human/system rejected the request  
- **expired**: Request timed out without decision
- **applied**: Approved request successfully executed

## File Touch Policy (STRICT)

### Allowed Files for Stage 4 ONLY
```
src/api/schemas.py              (modify - add approval and validation models)
src/core/schema.py              (create - core typed models for all data structures)
src/core/approval.py            (create - approval workflow and state management)
src/api/main.py                 (modify - add approval endpoints)
src/core/dao.py                 (modify - integrate schema validation)
src/core/corrections.py         (modify - integrate approval requirements)
src/util/logging.py             (modify - add approval and audit logging)
tests/test_schema_valid.py      (create - schema validation tests)
tests/test_approval.py          (create - approval workflow tests)
tests/test_full_app_stage4.py   (create - end-to-end integration tests)
tests/test_logging_stage4.py    (create - audit logging tests)
docs/APPROVAL.md                (create - approval workflow documentation)
docs/AUDIT.md                   (create - audit trail documentation)
docs/STAGE_CHECKS.md            (modify - add Stage 4 gate checklist)
Makefile                        (modify - add Stage 4 test targets)
```

### VIOLATION POLICY
**Editing any other files is SCOPE CREEP** and requires immediate rollback.

### File Header Requirement
All new files must include:
```python
"""
Stage 4 scope only. Do not implement beyond this file's responsibilities.
Approval workflows and schema validation - ensures data integrity and auditability.
"""
```

## Stage 4 Logical Slice Implementation Plan

### Slice 4.1: Schema Extension & Typed Validation

**Purpose**: Expand all API, KV, vector, and event payloads to use strict typed validation with comprehensive error handling.

**Allowed Files**:
- `src/core/schema.py` (create)
- `src/api/schemas.py` (modify)
- `src/core/dao.py` (modify)
- `tests/test_schema_valid.py` (create)

**Deliverables**:

**Core Schema Models** (`src/core/schema.py`):
```python
@dataclass
class KVRecord:
    key: str
    value: str
    source: str
    casing: str
    sensitive: bool
    updated_at: datetime

@dataclass
class VectorRecord:
    id: str
    vector: list[float]
    metadata: dict
    updated_at: datetime

@dataclass
class EpisodicEvent:
    id: int
    ts: datetime
    actor: str
    action: str
    payload: dict

@dataclass
class CorrectionAction:
    type: str  # ADD_VECTOR, UPDATE_VECTOR, REMOVE_VECTOR
    key: str
    metadata: dict
    timestamp: datetime
```

**API Schema Extensions** (`src/api/schemas.py`):
- Enhanced request/response models with validation rules
- Error response models with detailed field-level validation messages
- Approval request/response models for workflow endpoints

**DAO Integration** (`src/core/dao.py`):
- Validate all inputs using schema models before database operations
- Return typed results consistently across all DAO functions
- Comprehensive error handling for validation failures

**Test Plan**:
```bash
pytest tests/test_schema_valid.py -v
```

**Test Coverage Requirements**:
- Valid payloads for all data types pass validation
- Invalid payloads rejected with specific error messages
- Backward compatibility with existing Stage 1/2/3 data
- Performance impact of validation within acceptable limits

**Hard Gate Criteria**:
- [ ] All schema validation tests pass
- [ ] Invalid payloads rejected with clear error messages
- [ ] No regression in Stage 1/2/3 functionality
- [ ] Manual curl test: invalid API requests return 422 with detailed errors

**Rollback Guidance**: Revert changes to dao.py and schemas.py, delete schema.py and validation tests

---

### Slice 4.2: Approval Workflow (Manual and Automated Modes)

**Purpose**: Implement approval workflow system for corrections and sensitive operations with comprehensive state tracking.

**Allowed Files**:
- `src/core/approval.py` (create)
- `src/api/main.py` (modify)
- `src/core/corrections.py` (modify)
- `tests/test_approval.py` (create)
- `docs/APPROVAL.md` (create)

**Deliverables**:

**Approval Engine** (`src/core/approval.py`):
```python
@dataclass
class ApprovalRequest:
    id: str
    type: str  # 'correction', 'sensitive_operation'
    payload: dict
    requester: str
    status: str  # pending, approved, rejected, expired
    created_at: datetime
    expires_at: datetime

def create_approval_request(type: str, payload: dict, requester: str) -> ApprovalRequest
def get_approval_status(request_id: str) -> ApprovalRequest
def approve_request(request_id: str, approver: str, reason: str) -> bool
def reject_request(request_id: str, approver: str, reason: str) -> bool
def cleanup_expired_requests() -> int
```

**Approval API Endpoints** (`src/api/main.py`):
- `POST /approval/request` - Create approval request (feature-flagged)
- `GET /approval/{request_id}` - Get approval status
- `POST /approval/{request_id}/approve` - Approve request (manual mode)
- `POST /approval/{request_id}/reject` - Reject request (manual mode)
- `GET /approval/pending` - List pending requests (debug mode)

**Corrections Integration** (`src/core/corrections.py`):
- Modify `apply_corrections()` to require approval when `APPROVAL_ENABLED=true`
- Block execution until approval granted or request rejected/expired
- Log all approval interactions in episodic events

**Documentation** (`docs/APPROVAL.md`):
- Approval workflow overview and state diagram
- Manual approval procedures and best practices
- Feature flag interactions and configuration guidance
- Security considerations and audit requirements

**Test Plan**:
```bash
APPROVAL_ENABLED=true APPROVAL_MODE=manual pytest tests/test_approval.py -v
```

**Test Coverage Requirements**:
- Approval request creation and status tracking
- Manual approval and rejection workflows
- Request expiration and cleanup
- Integration with corrections engine
- Episodic event logging for all approval actions

**Hard Gate Criteria**:
- [ ] All approval workflow tests pass
- [ ] Manual verification: approval endpoints function correctly
- [ ] Corrections blocked until approval when feature enabled
- [ ] Comprehensive approval logging in episodic events
- [ ] Stage 1/2/3 behavior unchanged when approval disabled

**Rollback Guidance**: Remove approval.py, revert corrections.py and main.py changes, delete approval tests

---

### Slice 4.3: App-Level Integration & Regression Testing

**Purpose**: Comprehensive end-to-end testing of full workflow: ingest → validate → drift detect → propose → approve → apply → audit.

**Allowed Files**:
- `tests/test_full_app_stage4.py` (create)
- `Makefile` (modify)
- `docs/STAGE_CHECKS.md` (modify)

**Deliverables**:

**Integration Test Suite** (`tests/test_full_app_stage4.py`):
```python
def test_full_workflow_with_approval():
    # 1. Create KV entries with schema validation
    # 2. Enable vector system and heartbeat
    # 3. Simulate drift conditions
    # 4. Verify correction proposals created
    # 5. Verify approval required for application
    # 6. Approve corrections manually
    # 7. Verify corrections applied and logged
    # 8. Verify final state consistency

def test_approval_rejection_workflow():
    # Test correction rejection and state handling

def test_schema_validation_integration():
    # Test invalid data rejected throughout pipeline

def test_mixed_feature_flag_scenarios():
    # Test various combinations of feature flags
```

**Makefile Targets** (modify existing):
```makefile
# Add Stage 4 specific targets
test-stage4:
	pytest tests/test_schema_valid.py tests/test_approval.py -v

test-integration-stage4:
	pytest tests/test_full_app_stage4.py -v

test-full-stage4: test-stage4 test-integration-stage4
	@echo "✅ All Stage 4 tests passed"
```

**Stage Checks Documentation** (`docs/STAGE_CHECKS.md`):
- Stage 4 gate checklist with all validation criteria
- Manual verification procedures for approval workflows
- Integration test requirements and success criteria
- Regression test matrix for all prior stages

**Test Plan**:
```bash
make test-full-stage4
```

**Test Coverage Requirements**:
- End-to-end workflow with all features enabled
- Mixed feature flag combinations
- Error scenarios and recovery paths
- Performance validation under load
- Cross-stage regression verification

**Hard Gate Criteria**:
- [ ] All prior unit tests continue to pass
- [ ] All new Stage 4 tests pass
- [ ] Integration tests demonstrate full workflow
- [ ] Manual verification per Stage 4 checklist complete
- [ ] No performance degradation beyond acceptable limits

**Rollback Guidance**: Revert Makefile changes, delete integration tests, update stage checks

---

### Slice 4.4: Advanced Error Reporting & Auditing

**Purpose**: Comprehensive error reporting, audit trail enhancement, and transparent logging for all approval and validation operations.

**Allowed Files**:
- `src/util/logging.py` (modify)
- `tests/test_logging_stage4.py` (create)
- `docs/AUDIT.md` (create)

**Deliverables**:

**Enhanced Logging** (`src/util/logging.py`):
```python
def log_schema_validation_error(operation: str, errors: list, payload: dict):
    # Structured logging for validation failures

def log_approval_request(request_id: str, type: str, requester: str):
    # Log approval request creation

def log_approval_decision(request_id: str, decision: str, approver: str, reason: str):
    # Log approval/rejection decisions

def log_audit_event(event_type: str, actor: str, details: dict, sensitivity: str):
    # Comprehensive audit logging with privacy controls
```

**Error Reporting Enhancement**:
- Detailed validation error messages with field-level specificity
- Approval workflow errors with clear resolution guidance
- Audit trail gaps detection and reporting
- Performance impact monitoring and alerting

**Audit Documentation** (`docs/AUDIT.md`):
- Complete audit trail specification
- Error type taxonomy and resolution procedures
- Privacy compliance verification procedures
- Audit log analysis and monitoring guidance

**Test Plan**:
```bash
pytest tests/test_logging_stage4.py -v
```

**Test Coverage Requirements**:
- All error scenarios produce appropriate log entries
- Audit trails complete and tamper-evident
- Privacy controls prevent sensitive data leakage in logs
- Log format consistency and machine readability

**Hard Gate Criteria**:
- [ ] Error reporting tests cover all failure scenarios
- [ ] Audit log verification procedures documented and tested
- [ ] Privacy compliance maintained in all logging
- [ ] Manual verification of audit trails using curl/scripts
- [ ] Documentation complete and actionable

**Rollback Guidance**: Revert logging.py changes, delete audit tests and documentation

## Global Test & Verification Matrix

### Automated Testing Strategy

**Per-Slice Testing** (progressive validation):
```bash
# Slice 4.1: Schema validation
pytest tests/test_schema_valid.py -v

# Slice 4.2: Approval workflows  
APPROVAL_ENABLED=true pytest tests/test_approval.py -v

# Slice 4.3: Integration testing
pytest tests/test_full_app_stage4.py -v

# Slice 4.4: Advanced logging
pytest tests/test_logging_stage4.py -v

# Full regression
make test-full-stage4
```

**Cross-Stage Regression Testing**:
```bash
# Stage 1 regression
pytest tests/test_smoke.py -v

# Stage 2 regression with flags disabled
VECTOR_ENABLED=false pytest tests/test_vector_mock.py -v

# Stage 3 regression with flags disabled  
HEARTBEAT_ENABLED=false pytest tests/test_heartbeat.py -v

# All features enabled integration
VECTOR_ENABLED=true HEARTBEAT_ENABLED=true APPROVAL_ENABLED=true \
    pytest tests/test_full_app_stage4.py -v
```

### Manual Verification Procedures

**Schema Validation Testing**:
```bash
# Test invalid API requests
curl -X PUT http://localhost:8000/kv -H "Content-Type: application/json" \
    -d '{"key":"","value":"test"}'  # Should return 422 with validation errors

# Test valid requests still work
curl -X PUT http://localhost:8000/kv -H "Content-Type: application/json" \
    -d '{"key":"test","value":"valid","source":"user"}'  # Should succeed
```

**Approval Workflow Testing**:
```bash
# Enable approval system
export APPROVAL_ENABLED=true APPROVAL_MODE=manual

# Create drift scenario and verify approval required
# Follow complete workflow in docs/APPROVAL.md
```

**Audit Trail Verification**:
```bash
# Generate various operations and verify comprehensive logging
# Validate privacy controls and error reporting
# Follow procedures in docs/AUDIT.md
```

## Security and Privacy Considerations

### Data Protection
- **Schema validation never logs sensitive payload data**
- **Approval requests respect existing sensitive data protections**
- **Audit logs apply redaction rules consistently**
- **Error messages don't expose sensitive information**

### Approval Security
- **Approval requests include requester identification**
- **Approval decisions logged with approver and reason**
- **Request expiration prevents stale approvals**
- **Approval state tampering detection through episodic logging**

### Audit Integrity
- **All approval actions produce immutable episodic events**
- **Schema validation failures logged with sufficient detail**
- **Error scenarios include audit trail entries**
- **Audit log completeness verification procedures**

## Hard Gate Criteria (COMPLETION REQUIREMENTS)

### Automated Test Gates
- [ ] **All Stage 1/2/3 regression tests pass** with Stage 4 features disabled
- [ ] **All Stage 4 slice tests pass** individually and in combination
- [ ] **Integration tests demonstrate full workflow** with all features enabled
- [ ] **Performance tests show acceptable overhead** from validation and approval

### Manual Verification Gates
- [ ] **Schema validation rejects invalid inputs** with clear error messages
- [ ] **Approval workflows function correctly** in manual mode
- [ ] **Audit trails complete and verifiable** for all operations
- [ ] **Error scenarios handled gracefully** with appropriate logging

### Documentation Gates
- [ ] **APPROVAL.md complete** with operational procedures and examples
- [ ] **AUDIT.md complete** with verification procedures and compliance guidance
- [ ] **Stage 4 section in STAGE_CHECKS.md** comprehensive and tested
- [ ] **API documentation updated** with new endpoints and validation rules

### Integration Gates
- [ ] **Cross-stage feature flag combinations work correctly**
- [ ] **Backward compatibility maintained** for existing installations
- [ ] **Migration path documented** for upgrading from Stage 3
- [ ] **Rollback procedures tested** and documented

## Stage 4 Success Metrics

### Functional Success
- ✅ **Comprehensive schema validation** prevents invalid data throughout system
- ✅ **Approval workflows provide human oversight** for sensitive operations
- ✅ **End-to-end integration** demonstrates full feature stack working together
- ✅ **Advanced audit capabilities** enable compliance and troubleshooting

### Quality Success
- ✅ **No regression** in existing Stage 1/2/3 functionality
- ✅ **Performance overhead acceptable** for educational and development use
- ✅ **Error handling comprehensive** with clear resolution guidance
- ✅ **Documentation complete** and actionable for operators

### Safety Success
- ✅ **Privacy protections maintained** throughout approval and validation
- ✅ **Feature flag safety** ensures gradual rollout capability
- ✅ **Audit trail integrity** provides tamper-evident operation history
- ✅ **Rollback capability** enables safe experimentation and recovery

---

**⚠️ STAGE 4 LOCKDOWN COMPLETE - NO IMPLEMENTATION BEYOND THIS SCOPE ⚠️**

This document defines the complete, gated execution plan for Stage 4. Upon successful completion of all slices and gates, Stage 4 will provide comprehensive validation and approval capabilities while maintaining all safety, privacy, and educational guarantees established in foundational stages.