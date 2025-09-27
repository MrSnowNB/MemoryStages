"""
Stage 3 scope only. Do not implement beyond this file's responsibilities.
Heartbeat and drift correction - maintains vector overlay consistency with canonical SQLite.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import uuid
from datetime import datetime

from .dao import list_keys, get_key
from .config import get_vector_store, are_vector_features_enabled, get_drift_ruleset


@dataclass
class DriftFinding:
    """Represents a detected inconsistency between SQLite KV and vector overlay."""
    id: str
    type: str  # 'missing_vector', 'stale_vector', 'orphaned_vector'
    severity: str  # 'low', 'medium', 'high'
    kv_key: str
    details: Dict[str, Any]


@dataclass
class CorrectionAction:
    """Represents a corrective action to resolve drift."""
    type: str  # 'ADD_VECTOR', 'UPDATE_VECTOR', 'REMOVE_VECTOR'
    key: str
    metadata: Dict[str, Any]


@dataclass
class CorrectionPlan:
    """A complete plan to resolve a drift finding."""
    id: str
    finding_id: str
    actions: List[CorrectionAction]
    preview: Dict[str, Any]


def detect_drift() -> List[DriftFinding]:
    """
    Detect inconsistencies between SQLite KV canonical data and vector overlay.

    Compares:
    1. SQLite KV → vector store (missing vectors)
    2. Vector store → SQLite KV (orphaned vectors, stale embeddings)

    Sensitive data never checked per Stage 1+ protections.

    Returns:
        List of detected drift findings with severity based on ruleset.
    """
    if not are_vector_features_enabled():
        return []

    findings = []

    # Get vector store for auditing
    vector_store = get_vector_store()
    if not vector_store:
        return []

    # Get all current SQLite KV entries (non-sensitive, non-tombstoned)
    sqlite_kv = {kv.key: kv for kv in list_keys() if not kv.sensitive}

    # Get all vector entries (assuming they have metadata with keys)
    try:
        # Get a list of vector entries by searching with a dummy query
        # This is a simplified approach - real implementation would need
        # vector store introspection methods
        vector_entries = _get_audit_vector_entries(vector_store)
    except Exception as e:
        # If vector audit fails, skip detection
        print(f"⚠️  Vector audit unavailable: {e}")
        return []

    # Rule 1: Find MissingVectorForNonSensitiveKV
    # Check SQLite entries missing from vector store
    for kv_key, kv_entry in sqlite_kv.items():
        if kv_key not in vector_entries:
            finding = DriftFinding(
                id=str(uuid.uuid4()),
                type="missing_vector",
                severity=_calculate_severity("missing_vector"),
                kv_key=kv_key,
                details={
                    "sqlite_updated": kv_entry.updated_at.isoformat(),
                    "sqlite_source": kv_entry.source,
                    "reason": "KV entry exists in SQLite but missing from vector overlay"
                }
            )
            findings.append(finding)

    # Rule 2: Find StaleVectorEmbedding
    # Check vector entries older than SQLite updates
    for vector_key, vector_metadata in vector_entries.items():
        sqlite_entry = sqlite_kv.get(vector_key)
        if sqlite_entry:
            vector_updated = vector_metadata.get("updated_at")
            sqlite_updated = sqlite_entry.updated_at.isoformat() if hasattr(sqlite_entry.updated_at, 'isoformat') else str(sqlite_entry.updated_at)

            # Compare timestamps (any difference = stale)
            if vector_updated != sqlite_updated:
                finding = DriftFinding(
                    id=str(uuid.uuid4()),
                    type="stale_vector",
                    severity=_calculate_severity("stale_vector"),
                    kv_key=vector_key,
                    details={
                        "vector_updated": vector_updated,
                        "sqlite_updated": sqlite_updated,
                        "reason": "Vector embedding is stale compared to SQLite update"
                    }
                )
                findings.append(finding)

    # Rule 3: Find OrphanedVectorEntry
    # Check vector entries without corresponding SQLite KV
    for vector_key in vector_entries.keys():
        if vector_key not in sqlite_kv:
            finding = DriftFinding(
                id=str(uuid.uuid4()),
                type="orphaned_vector",
                severity=_calculate_severity("orphaned_vector"),
                kv_key=vector_key,
                details={
                    "vector_updated": vector_entries[vector_key].get("updated_at"),
                    "reason": "Vector entry exists but corresponding SQLite KV is missing/tombstoned"
                }
            )
            findings.append(finding)

    return findings


def _get_audit_vector_entries(vector_store) -> Dict[str, Dict[str, Any]]:
    """
    Get vector entries for audit purposes.

    This is a placeholder implementation. Real vector stores would need
    introspection methods to list all entries with metadata.

    For now, returns empty dict to simulate "no vectors" case.
    """
    # TODO: Implement proper vector store audit introspection
    # This requires adding audit methods to vector store interface

    # Placeholder: assume no entries for now
    # Real implementation would need to iterate through vector store
    # and extract keys + metadata (like updated_at timestamps)
    return {}


def _calculate_severity(drift_type: str) -> str:
    """Calculate severity based on drift type and ruleset configuration."""
    ruleset = get_drift_ruleset()

    if ruleset == "strict":
        return "high"

    # lenient ruleset
    if drift_type in ["missing_vector", "stale_vector"]:
        return "medium"
    elif drift_type == "orphaned_vector":
        return "low"

    return "medium"  # default


def create_correction_plan(finding: DriftFinding) -> CorrectionPlan:
    """
    Generate a correction plan for a drift finding.

    Returns an actionable plan with specific correction actions.
    """
    plan_id = str(uuid.uuid4())

    if finding.type == "missing_vector":
        action = CorrectionAction(
            type="ADD_VECTOR",
            key=finding.kv_key,
            metadata={
                "reason": "Add missing vector for existing KV entry",
                "finding_details": finding.details
            }
        )

    elif finding.type == "stale_vector":
        action = CorrectionAction(
            type="UPDATE_VECTOR",
            key=finding.kv_key,
            metadata={
                "reason": "Update stale vector embedding",
                "finding_details": finding.details
            }
        )

    elif finding.type == "orphaned_vector":
        action = CorrectionAction(
            type="REMOVE_VECTOR",
            key=finding.kv_key,
            metadata={
                "reason": "Remove orphaned vector entry",
                "finding_details": finding.details
            }
        )

    else:
        raise ValueError(f"Unknown drift type: {finding.type}")

    return CorrectionPlan(
        id=plan_id,
        finding_id=finding.id,
        actions=[action],  # Single action per finding for now
        preview={
            "drift_type": finding.type,
            "severity": finding.severity,
            "affected_key": finding.kv_key,
            "action_type": action.type,
            "estimated_impact": f"{'Safe' if finding.severity != 'high' else 'Critical'} operation"
        }
    )
