"""
Stage 3 scope only. Do not implement beyond this file's responsibilities.
Heartbeat and drift correction - maintains vector overlay consistency with canonical SQLite.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import uuid
from datetime import datetime

from .drift_rules import CorrectionPlan
from .config import get_correction_mode, get_vector_store, get_embedding_provider, are_vector_features_enabled
from .dao import get_key, add_event
from .approval import create_approval_request, wait_for_approval
from .config import APPROVAL_ENABLED


@dataclass
class CorrectionResult:
    """Result of executing a correction action."""
    plan_id: str
    action_index: int
    success: bool
    action_taken: bool
    error_message: str
    details: Dict[str, Any]


def apply_corrections(plans: List[CorrectionPlan]) -> List[CorrectionResult]:
    """
    Apply correction plans according to current CORRECTION_MODE.

    Modes:
    - 'off': No-ops, only log what would be done
    - 'propose': Write episodic events, no database changes
    - 'apply': Execute corrections against vector store

    Returns results of attempted corrections.
    """
    correction_mode = get_correction_mode()
    results = []

    if not are_vector_features_enabled():
        print(f"⚠️  Vector features disabled, skipping corrections (mode: {correction_mode})")
        return []

    vector_store = get_vector_store()
    embedding_provider = get_embedding_provider()

    if not vector_store or not embedding_provider:
        print(f"⚠️  Vector store/provider unavailable, skipping corrections (mode: {correction_mode})")
        return []

    print(f"🔧 Applying {len(plans)} correction plans (mode: {correction_mode})")

    for plan in plans:
        plan_results = _execute_correction_plan(plan, correction_mode, vector_store, embedding_provider)
        results.extend(plan_results)

    successful = sum(1 for r in results if r.success and r.action_taken)
    print(f"✓ Corrections complete: {successful}/{len(results)} successful")

    return results


def revert_correction(plan_id: str) -> Dict[str, Any]:
    """
    Attempt to revert a correction plan.

    This is a best-effort operation - not all actions are reversible.
    Primarily handles removal of added vectors where possible.
    """
    # For safety and simplicity, Stage 3 scope limits revert capability
    # Full reversion would require storing pre-correction state
    # For now: log the revert request but don't perform destructive operations

    event_payload = {
        "operation": "revert_correction_attempted",
        "plan_id": plan_id,
        "timestamp": datetime.now().isoformat(),
        "result": "limited_support",
        "message": "Stage 3 revert limited to logging. Full revert requires manual intervention."
    }

    add_event(user_id="system", actor="correction_system", action="revert_correction", payload=str(event_payload))

    print(f"📝 Revert requested for plan {plan_id} (logged, no action taken)")

    return {
        "plan_id": plan_id,
        "reverted": False,
        "reason": "Stage 3 reversion limited to audit logging",
        "recommendation": "Manual intervention required for data restoration"
    }


def _execute_correction_plan(plan: CorrectionPlan, mode: str, vector_store, embedding_provider) -> List[CorrectionResult]:
    """Execute one correction plan's actions."""
    results = []

    # Log the correction attempt
    _log_correction_plan(plan, mode)

    for i, action in enumerate(plan.actions):
        result = _execute_correction_action(plan.id, i, action, mode, vector_store, embedding_provider)
        results.append(result)

    return results


def _execute_correction_action(plan_id: str, action_index: int, action, mode: str, vector_store, embedding_provider) -> CorrectionResult:
    """Execute a single correction action."""
    result = CorrectionResult(
        plan_id=plan_id,
        action_index=action_index,
        success=False,
        action_taken=False,
        error_message="",
        details={"action_type": action.type, "key": action.key}
    )

    try:
        if mode == "off":
            # Off mode: No action, just log preview
            result.success = True
            result.details["message"] = "Mode 'off' - no action taken"

        elif mode == "propose":
            # Propose mode: Write episodic event, no database changes
            _log_correction_proposal(plan_id, action)
            result.success = True
            result.action_taken = False
            result.details["message"] = "Correction proposed (logged only)"

        elif mode == "apply":
            # Apply mode: Execute the correction, but wait for approval if enabled
            success, message = _apply_correction_with_approval(plan_id, action, vector_store, embedding_provider)
            result.success = success
            result.action_taken = success
            result.details["message"] = message

        else:
            result.success = False
            result.error_message = f"Unknown correction mode: {mode}"

    except Exception as e:
        result.success = False
        result.error_message = str(e)
        result.details["message"] = f"Correction failed: {e}"

        # Log failed correction
        _log_correction_failure(plan_id, action, e)

    return result


def _apply_correction_action(action, vector_store, embedding_provider):
    """Actually execute a correction action against the vector store."""
    if action.type == "ADD_VECTOR":
        _apply_add_vector(action.key, vector_store, embedding_provider)

    elif action.type == "UPDATE_VECTOR":
        _apply_update_vector(action.key, vector_store, embedding_provider)

    elif action.type == "REMOVE_VECTOR":
        _apply_remove_vector(action.key, vector_store)

    else:
        raise ValueError(f"Unknown correction action type: {action.type}")


def _apply_correction_with_approval(plan_id: str, action, vector_store, embedding_provider) -> tuple[bool, str]:
    """Apply a correction action with approval workflow if enabled."""
    if APPROVAL_ENABLED:
        # Create approval request
        approval_payload = {
            "plan_id": plan_id,
            "action_type": action.type,
            "key": action.key,
            "action_metadata": action.metadata,
            "description": f"Apply {action.type} correction for key '{action.key}' in plan {plan_id}"
        }

        approval_req = create_approval_request(
            type="correction",
            payload=approval_payload,
            requester="correction_system"
        )

        if not approval_req:
            return False, "Approval system disabled unexpectedly"

        # Log approval request creation
        add_event(user_id="system", actor="correction_system", action="approval_requested",
                  payload=f"Correction approval requested: {approval_req.id}")

        # Wait for approval (in real implementation, this might be async)
        status = wait_for_approval(approval_req.id)

        if status != 'approved':
            return False, f"Correction not approved (status: {status})"

        # Log approval received
        add_event(user_id="system", actor="correction_system", action="correction_approved",
                  payload=f"Correction approved for {plan_id}: {action.type} on '{action.key}'")

    # Execute the correction
    try:
        _apply_correction_action(action, vector_store, embedding_provider)
        _log_correction_application(plan_id, action)
        return True, f"Applied {action.type} for key '{action.key}'"
    except Exception as e:
        return False, f"Correction execution failed: {e}"


def _apply_add_vector(key: str, vector_store, embedding_provider):
    """Add missing vector for existing KV entry."""
    kv_entry = get_key(key)
    if not kv_entry:
        raise ValueError(f"Cannot add vector: KV entry '{key}' not found in SQLite")

    if kv_entry.sensitive:
        raise ValueError(f"Refusing to vectorize sensitive key '{key}'")

    # Generate embedding
    content_to_embed = f"{key}: {kv_entry.value}"
    embedding = embedding_provider.embed_text(content_to_embed)

    # Create vector record
    vector_record = type('VectorRecord', (), {
        'id': key,
        'vector': embedding,
        'metadata': {
            'source': kv_entry.source,
            'casing': kv_entry.casing,
            'updated_at': kv_entry.updated_at.isoformat()
        }
    })()

    # Add to vector store
    vector_store.add(vector_record)


def _apply_update_vector(key: str, vector_store, embedding_provider):
    """Update stale vector embedding."""
    kv_entry = get_key(key)
    if not kv_entry:
        raise ValueError(f"Cannot update vector: KV entry '{key}' not found in SQLite")

    if kv_entry.sensitive:
        raise ValueError(f"Refusing to re-vectorize sensitive key '{key}'")

    # Generate fresh embedding
    content_to_embed = f"{key}: {kv_entry.value}"
    embedding = embedding_provider.embed_text(content_to_embed)

    # Update vector record
    vector_store.update(key, embedding)  # Assumes vector store has update method

    # If update not supported, remove and re-add
    try:
        vector_store.update(key, embedding)
    except AttributeError:
        # Fallback for stores without update method
        vector_store.delete(key)  # May raise NotImplementedError for FAISS
        _apply_add_vector(key, vector_store, embedding_provider)


def _apply_remove_vector(key: str, vector_store):
    """Remove orphaned vector entry."""
    # Use delete with graceful handling for non-existent or unsupported deletion
    vector_store.delete(key)


def _log_correction_plan(plan: CorrectionPlan, mode: str):
    """Log correction plan execution attempt."""
    event_payload = {
        "event_type": "correction_plan_execution",
        "plan_id": plan.id,
        "finding_id": plan.finding_id,
        "drift_type": plan.preview.get("drift_type"),
        "severity": plan.preview.get("severity"),
        "affected_key": plan.preview.get("affected_key"),
        "action_count": len(plan.actions),
        "correction_mode": mode,
        "timestamp": datetime.now().isoformat()
    }

    add_event(user_id="system", actor="correction_system", action="correction_plan_started", payload=str(event_payload))


def _log_correction_proposal(plan_id: str, action):
    """Log correction proposal."""
    event_payload = {
        "event_type": "correction_proposed",
        "plan_id": plan_id,
        "action_type": action.type,
        "key": action.key,
        "metadata": action.metadata,
        "timestamp": datetime.now().isoformat()
    }

    add_event(user_id="system", actor="correction_system", action="correction_proposed", payload=str(event_payload))


def _log_correction_application(plan_id: str, action):
    """Log successful correction application."""
    event_payload = {
        "event_type": "correction_applied",
        "plan_id": plan_id,
        "action_type": action.type,
        "key": action.key,
        "metadata": action.metadata,
        "timestamp": datetime.now().isoformat()
    }

    add_event(user_id="system", actor="correction_system", action="correction_applied", payload=str(event_payload))


def _log_correction_failure(plan_id: str, action, error: Exception):
    """Log correction failure."""
    event_payload = {
        "event_type": "correction_failed",
        "plan_id": plan_id,
        "action_type": action.type,
        "key": action.key,
        "error": str(error),
        "timestamp": datetime.now().isoformat()
    }

    add_event(user_id="system", actor="correction_system", action="correction_failed", payload=str(event_payload))


# Stage 4 stub function for audit testing
def apply_correction_action(action, vector_store, embedding_provider):
    """Stub function for Stage 4 audit testing - applies a single correction action."""
    return _apply_correction_action(action, vector_store, embedding_provider)
