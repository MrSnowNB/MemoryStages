"""
Stage 6 scope only. Do not implement beyond this file's responsibilities.
Privacy, backup, and maintenance - ensures data protection and system integrity.

Automated maintenance routines for database integrity, vector validation, and cleanup.
"""

import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import logging

from .config import DB_PATH, are_vector_features_enabled, MAINTENANCE_ENABLED
from .dao import get_kv_count, list_keys
from .privacy import validate_sensitive_access


@dataclass
class MaintenanceReport:
    """Comprehensive maintenance operation report."""
    operation: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    issues_found: int = 0
    issues_resolved: int = 0
    actions_taken: List[str] = None
    recommendations: List[str] = None
    errors: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.actions_taken is None:
            self.actions_taken = []
        if self.recommendations is None:
            self.recommendations = []
        if self.errors is None:
            self.errors = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for serialization."""
        data = {
            "operation": self.operation,
            "started_at": self.started_at.isoformat(),
            "issues_found": self.issues_found,
            "issues_resolved": self.issues_resolved,
            "actions_taken": self.actions_taken,
            "recommendations": self.recommendations,
            "errors": self.errors,
            "metadata": self.metadata
        }
        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat()
        return data


class MaintenanceError(Exception):
    """Custom exception for maintenance operations."""
    pass


def _create_backup_for_maintenance(operation: str) -> Optional[str]:
    """Create a safety backup before maintenance operations that may alter data."""
    if not MAINTENANCE_ENABLED:
        return None

    try:
        # Import backup functionality
        from .backup import create_backup

        # Create maintenance backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"./data/maintenance_backup_{operation}_{timestamp}"

        manifest = create_backup(backup_path, encrypt=True, include_sensitive=False)

        from util.logging import audit_event
        audit_event(
            event_type="maintenance_backup_created",
            identifiers={"operation": operation, "backup_id": manifest.backup_id},
            payload={
                "backup_path": backup_path,
                "include_sensitive": False,
                "encrypted": True
            }
        )

        return backup_path

    except Exception as e:
        # Log but don't fail - maintenance can proceed
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to create maintenance backup for {operation}: {e}")
        return None


def check_database_integrity() -> MaintenanceReport:
    """
    Check SQLite database integrity and constraints.

    Returns:
        MaintenanceReport: Detailed integrity check results
    """
    if not MAINTENANCE_ENABLED:
        raise MaintenanceError("Maintenance system is disabled. Enable with MAINTENANCE_ENABLED=true")

    report = MaintenanceReport(
        operation="database_integrity_check",
        started_at=datetime.now()
    )

    try:
        # Check database file exists
        db_path = Path(DB_PATH)
        if not db_path.exists():
            report.errors.append(f"Database file not found: {DB_PATH}")
            report.completed_at = datetime.now()
            return report

        # Basic file integrity
        file_size = db_path.stat().st_size
        report.metadata["file_size"] = file_size

        if file_size == 0:
            report.errors.append("Database file is empty")
            report.completed_at = datetime.now()
            return report

        # Connect and run integrity check
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
            # SQLite integrity check
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()

            if integrity_result and integrity_result[0] == "ok":
                report.metadata["integrity_status"] = "passed"
            else:
                report.issues_found += 1
                report.errors.append(f"Integrity check failed: {integrity_result}")
                report.recommendations.append("Run database repair or restore from backup")

            # Check foreign key constraints
            cursor.execute("PRAGMA foreign_keys")
            fk_enabled = cursor.fetchone()[0]
            report.metadata["foreign_keys_enabled"] = bool(fk_enabled)

            if not fk_enabled:
                report.issues_found += 1
                report.recommendations.append("Foreign key constraints should be enabled")

            # Check for orphaned records
            # Count records in main tables
            cursor.execute("SELECT COUNT(*) FROM kv")
            kv_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM kv WHERE value != ''")
            non_tombstone_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM kv WHERE value = ''")
            tombstone_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM episodic")
            event_count = cursor.fetchone()[0]

            report.metadata.update({
                "total_kv_records": kv_count,
                "active_kv_records": non_tombstone_count,
                "tombstone_records": tombstone_count,
                "event_records": event_count
            })

            # Check for anomalies
            if kv_count == 0 and event_count == 0:
                report.recommendations.append("Database appears to be empty - consider initialization")
            elif tombstone_count > non_tombstone_count:
                report.issues_found += 1
                report.recommendations.append("High number of tombstone records - consider cleanup")

            # Validate table schemas
            cursor.execute("PRAGMA table_info(kv)")
            kv_columns = cursor.fetchall()
            expected_kv_columns = ['key', 'value', 'casing', 'source', 'updated_at', 'sensitive']

            if len(kv_columns) != len(expected_kv_columns):
                report.issues_found += 1
                report.errors.append("KV table schema mismatch")
            else:
                actual_columns = [col[1] for col in kv_columns]
                if actual_columns != expected_kv_columns:
                    report.issues_found += 1
                    report.errors.append("KV table column mismatch")

        finally:
            conn.close()

    except Exception as e:
        report.errors.append(f"Database integrity check failed: {e}")

    report.completed_at = datetime.now()
    return report


def validate_vector_index() -> MaintenanceReport:
    """
    Validate vector index consistency and data integrity.

    Returns:
        MaintenanceReport: Vector validation results
    """
    if not MAINTENANCE_ENABLED:
        raise MaintenanceError("Maintenance system is disabled. Enable with MAINTENANCE_ENABLED=true")

    report = MaintenanceReport(
        operation="vector_index_validation",
        started_at=datetime.now()
    )

    try:
        if not are_vector_features_enabled():
            report.metadata["vector_features"] = "disabled"
            report.recommendations.append("Vector features are disabled - validation skipped")
            report.completed_at = datetime.now()
            return report

        # Import vector functionality
        from .config import get_vector_store, get_embedding_provider

        vector_store = get_vector_store()
        embedding_provider = get_embedding_provider()

        if not vector_store or not embedding_provider:
            report.errors.append("Vector store or embedding provider not available")
            report.completed_at = datetime.now()
            return report

        # Basic vector store integrity checks
        report.metadata["provider"] = vector_store.__class__.__name__

        # Check if we can export data (test basic functionality)
        try:
            export_data = vector_store.export_data()
            report.metadata["can_export"] = True

            # Validate export data structure
            if "vectors" in export_data and "index" in export_data:
                vector_count = len(export_data.get("vectors", {}))
                index_count = len(export_data.get("index", {}))
                report.metadata["exported_vectors"] = vector_count
                report.metadata["exported_indices"] = index_count

                # Check for inconsistencies
                if vector_count != index_count:
                    report.issues_found += 1
                    report.errors.append(f"Vector data inconsistency: {vector_count} vectors vs {index_count} indices")
            else:
                report.issues_found += 1
                report.errors.append("Invalid vector export data structure")

        except Exception as e:
            report.issues_found += 1
            report.errors.append(f"Vector export failed: {e}")
            report.metadata["can_export"] = False

        # Cross-validate with KV store
        kv_keys = {record.key for record in list_keys()}
        vector_validation_keys = []  # Keys to validate if possible

        # Sample some keys for deeper validation
        sample_keys = list(kv_keys)[:10]  # Check first 10 keys

        for key in sample_keys:
            try:
                # Check if key exists in vector store (if supported)
                if hasattr(vector_store, 'search'):
                    # Try a simple search to test functionality
                    test_vector = embedding_provider.embed_text(key)
                    results = vector_store.search(test_vector, top_k=1)
                    vector_validation_keys.append(key)
            except Exception as e:
                report.errors.append(f"Vector search failed for key '{key}': {e}")

        report.metadata["validation_sample_size"] = len(sample_keys)
        report.metadata["successful_validations"] = len(vector_validation_keys)

        if len(vector_validation_keys) < len(sample_keys):
            report.issues_found += 1
            report.recommendations.append("Some vector operations failed - consider rebuilding index")

        # Overall assessment
        if report.issues_found == 0:
            report.metadata["vector_health"] = "good"
        elif report.issues_found < 3:
            report.metadata["vector_health"] = "warning"
            report.recommendations.append("Minor vector issues detected - monitor closely")
        else:
            report.metadata["vector_health"] = "critical"
            report.recommendations.append("Significant vector issues - consider full rebuild")

    except Exception as e:
        report.errors.append(f"Vector validation failed: {e}")

    report.completed_at = datetime.now()
    return report


def cleanup_orphaned_data() -> MaintenanceReport:
    """
    Remove orphaned vector entries and stale references.

    Returns:
        MaintenanceReport: Cleanup operation results
    """
    if not MAINTENANCE_ENABLED:
        raise MaintenanceError("Maintenance system is disabled. Enable with MAINTENANCE_ENABLED=true")

    # Create backup before destructive operation
    backup_path = _create_backup_for_maintenance("cleanup_orphaned_data")

    report = MaintenanceReport(
        operation="orphaned_data_cleanup",
        started_at=datetime.now(),
        metadata={"backup_created": backup_path is not None}
    )

    try:
        # Get current KV keys (non-sensitive for vector cleanup)
        kv_records = list_keys()
        current_kv_keys = {record.key for record in kv_records}

        cleanup_actions = []

        # Clean up vector orphans if vector features enabled
        if are_vector_features_enabled():
            try:
                from .config import get_vector_store
                vector_store = get_vector_store()

                if vector_store and hasattr(vector_store, 'export_data'):
                    vector_data = vector_store.export_data()
                    vector_keys = set(vector_data.get("vectors", {}).keys())

                    # Find orphaned vectors (vectors without corresponding KV records)
                    orphaned_vectors = vector_keys - current_kv_keys

                    if orphaned_vectors:
                        # Try to delete orphaned vectors
                        deleted_count = 0
                        for key in orphaned_vectors:
                            try:
                                # Validate privacy before deletion
                                validate_sensitive_access("maintenance_system", "vector_cleanup", f"Remove orphaned vector for key: {key}")

                                if hasattr(vector_store, 'delete'):
                                    vector_store.delete(key)
                                    deleted_count += 1
                                    cleanup_actions.append(f"Removed orphaned vector for key: {key}")
                                else:
                                    report.recommendations.append("Vector store doesn't support deletion - orphaned vectors not removed")
                                    break

                            except Exception as e:
                                report.errors.append(f"Failed to remove orphaned vector for key '{key}': {e}")

                        if deleted_count > 0:
                            report.issues_resolved += deleted_count
                            report.actions_taken.extend(cleanup_actions)
                    else:
                        report.metadata["orphaned_vectors"] = 0

            except Exception as e:
                report.errors.append(f"Vector cleanup failed: {e}")

        # Clean up old tombstone records (older than 30 days)
        try:
            import sqlite3
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # Find old tombstones
            thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
            cursor.execute(
                "SELECT COUNT(*) FROM kv WHERE value = '' AND updated_at < ?",
                (thirty_days_ago,)
            )
            old_tombstone_count = cursor.fetchone()[0]

            if old_tombstone_count > 0:
                # Actually delete old tombstones (privacy-safe operation)
                cursor.execute(
                    "DELETE FROM kv WHERE value = '' AND updated_at < ?",
                    (thirty_days_ago,)
                )

                deleted_rows = cursor.rowcount
                conn.commit()

                if deleted_rows > 0:
                    report.issues_resolved += deleted_rows
                    report.actions_taken.append(f"Removed {deleted_rows} old tombstone records")
                    report.metadata["tombstones_cleaned"] = deleted_rows

            conn.close()

        except Exception as e:
            report.errors.append(f"Tombstone cleanup failed: {e}")

        # Clean up old audit logs if they exist (future extension)
        # For now, just note that this could be implemented
        report.recommendations.append("Consider implementing audit log rotation for compliance")

        # Overall cleanup summary
        if report.issues_resolved > 0:
            report.metadata["cleanup_successful"] = True
        else:
            report.metadata["cleanup_successful"] = False
            if not report.errors:
                report.recommendations.append("No orphaned data found - cleanup completed successfully")

    except Exception as e:
        report.errors.append(f"Cleanup operation failed: {e}")

    report.completed_at = datetime.now()

    # Log maintenance operation
    from util.logging import audit_event
    audit_event(
        event_type="maintenance_completed",
        identifiers={"operation": report.operation, "issues_resolved": report.issues_resolved},
        payload={
            "backup_created": backup_path is not None,
            "actions_taken": len(report.actions_taken),
            "errors": len(report.errors),
            "metadata": report.metadata
        }
    )

    return report


def rebuild_vector_index(force: bool = False, backup_first: bool = True) -> MaintenanceReport:
    """
    Rebuild vector index from canonical SQLite data.

    Args:
        force: Force rebuild even if no issues detected
        backup_first: Create backup before rebuild

    Returns:
        MaintenanceReport: Rebuild operation results
    """
    if not MAINTENANCE_ENABLED:
        raise MaintenanceError("Maintenance system is disabled. Enable with MAINTENANCE_ENABLED=true")

    # Create backup before destructive operation if requested
    backup_path = None
    if backup_first:
        backup_path = _create_backup_for_maintenance("rebuild_vector_index")

    report = MaintenanceReport(
        operation="vector_index_rebuild",
        started_at=datetime.now(),
        metadata={"backup_created": backup_path is not None, "force_rebuild": force}
    )

    try:
        if not are_vector_features_enabled():
            report.errors.append("Vector features are disabled - cannot rebuild index")
            report.completed_at = datetime.now()
            return report

        # First validate current state
        validation_report = validate_vector_index()
        needs_rebuild = force or validation_report.issues_found > 0

        report.metadata["validation_issues"] = validation_report.issues_found
        report.metadata["rebuild_needed"] = needs_rebuild

        if not needs_rebuild:
            report.recommendations.append("Vector index validation passed - rebuild not needed")
            report.completed_at = datetime.now()
            return report

        # Proceed with rebuild
        from .config import get_vector_store, get_embedding_provider
        from .dao import list_keys

        vector_store = get_vector_store()
        embedding_provider = get_embedding_provider()

        if not vector_store or not embedding_provider:
            report.errors.append("Vector store or embedding provider not available for rebuild")
            report.completed_at = datetime.now()
            return report

        # Clear existing index
        vector_store.clear()
        report.actions_taken.append("Cleared existing vector index")

        # Rebuild from current KV data (only non-sensitive records)
        kv_records = list_keys()
        rebuild_count = 0

        for record in kv_records:
            if not record.sensitive:  # Only rebuild non-sensitive records for safety
                try:
                    # Generate embedding for the key-value pair
                    content = f"{record.key}: {record.value}"
                    embedding = embedding_provider.embed_text(content)

                    # Create vector record
                    from ..vector.types import VectorRecord
                    vector_record = VectorRecord(
                        id=record.key,
                        vector=embedding,
                        metadata={"source": record.source, "casing": record.casing}
                    )

                    # Add to vector store
                    vector_store.add(vector_record)
                    rebuild_count += 1

                except Exception as e:
                    report.errors.append(f"Failed to rebuild vector for key '{record.key}': {e}")

        report.issues_resolved = rebuild_count
        report.actions_taken.append(f"Rebuilt vectors for {rebuild_count} records")
        report.metadata["vectors_rebuilt"] = rebuild_count

        # Validate rebuild success
        post_validation = validate_vector_index()
        if post_validation.issues_found == 0:
            report.metadata["rebuild_successful"] = True
            report.actions_taken.append("Vector index rebuild validated successfully")
        else:
            report.metadata["rebuild_successful"] = False
            report.errors.extend(post_validation.errors)
            report.recommendations.append("Vector index rebuild completed but validation failed")

    except Exception as e:
        report.errors.append(f"Vector index rebuild failed: {e}")

    report.completed_at = datetime.now()

    # Log rebuild operation
    from util.logging import audit_event
    audit_event(
        event_type="vector_index_rebuilt",
        identifiers={
            "operation": report.operation,
            "vectors_rebuilt": report.metadata.get("vectors_rebuilt", 0)
        },
        payload={
            "force_rebuild": force,
            "backup_created": backup_path is not None,
            "rebuild_successful": report.metadata.get("rebuild_successful", False),
            "validation_issues": report.metadata.get("validation_issues", 0)
        }
    )

    return report


def perform_full_maintenance() -> List[MaintenanceReport]:
    """
    Perform comprehensive maintenance operations.

    Returns:
        List[MaintenanceReport]: Reports from all maintenance operations
    """
    if not MAINTENANCE_ENABLED:
        raise MaintenanceError("Maintenance system is disabled. Enable with MAINTENANCE_ENABLED=true")

    reports = []

    # Run all maintenance operations
    operations = [
        check_database_integrity,
        validate_vector_index,
        cleanup_orphaned_data,
    ]

    for operation in operations:
        try:
            report = operation()
            reports.append(report)
        except Exception as e:
            # Create error report for failed operation
            error_report = MaintenanceReport(
                operation=f"{operation.__name__}_failed",
                started_at=datetime.now(),
                completed_at=datetime.now(),
                errors=[str(e)]
            )
            reports.append(error_report)

    # Decide if vector rebuild is needed
    db_report = next((r for r in reports if r.operation == "database_integrity_check"), None)
    vector_report = next((r for r in reports if r.operation == "vector_index_validation"), None)

    needs_rebuild = (
        vector_report and vector_report.issues_found > 0 or
        db_report and "critical" in db_report.recommendations
    )

    if needs_rebuild:
        try:
            rebuild_report = rebuild_vector_index(force=False, backup_first=True)
            reports.append(rebuild_report)
        except Exception as e:
            rebuild_error_report = MaintenanceReport(
                operation="rebuild_vector_index_failed",
                started_at=datetime.now(),
                completed_at=datetime.now(),
                errors=[str(e)]
            )
            reports.append(rebuild_error_report)

    return reports
