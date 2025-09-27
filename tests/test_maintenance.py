"""
Stage 6 scope only. Do not implement beyond this file's responsibilities.
Privacy, backup, and maintenance - ensures data protection and system integrity.

Tests for maintenance operations including database integrity, vector validation, and cleanup.
"""

import pytest
import sqlite3
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from src.core.maintenance import (
    MaintenanceReport,
    check_database_integrity,
    validate_vector_index,
    cleanup_orphaned_data,
    rebuild_vector_index,
    perform_full_maintenance,
    MaintenanceError
)
from src.core.config import MAINTENANCE_ENABLED


@pytest.mark.skipif(not MAINTENANCE_ENABLED, reason="Maintenance system disabled")
class TestMaintenanceReport:
    """Test maintenance report functionality."""

    def test_report_creation(self):
        """Test maintenance report creation."""
        started = datetime.now()
        report = MaintenanceReport(
            operation="test_operation",
            started_at=started,
            issues_found=2,
            issues_resolved=1,
            actions_taken=["action1", "action2"],
            recommendations=["rec1"],
            errors=["error1"]
        )

        assert report.operation == "test_operation"
        assert report.issues_found == 2
        assert report.issues_resolved == 1
        assert len(report.actions_taken) == 2
        assert len(report.recommendations) == 1
        assert len(report.errors) == 1

    def test_report_to_dict(self):
        """Test report serialization."""
        report = MaintenanceReport(
            operation="test_op",
            started_at=datetime(2025, 1, 1, 12, 0, 0),
            completed_at=datetime(2025, 1, 1, 12, 1, 0),
            issues_found=1,
            metadata={"key": "value"}
        )

        data = report.to_dict()
        assert data["operation"] == "test_op"
        assert data["issues_found"] == 1
        assert "started_at" in data
        assert "completed_at" in data
        assert data["metadata"]["key"] == "value"


@pytest.mark.skipif(not MAINTENANCE_ENABLED, reason="Maintenance system disabled")
class TestDatabaseIntegrity:
    """Test database integrity checking."""

    @patch('src.core.maintenance.MAINTENANCE_ENABLED', True)
    def test_database_integrity_check_disabled(self):
        """Test integrity check when maintenance disabled."""
        with patch('src.core.maintenance.MAINTENANCE_ENABLED', False):
            with pytest.raises(MaintenanceError, match="Maintenance system is disabled"):
                check_database_integrity()

    @patch('src.core.maintenance.MAINTENANCE_ENABLED', True)
    @patch('src.core.maintenance.DB_PATH', './test.db')
    def test_database_file_not_found(self):
        """Test integrity check with missing database file."""
        with patch('src.core.maintenance.DB_PATH', '/nonexistent/path.db'):
            report = check_database_integrity()

            assert report.operation == "database_integrity_check"
            assert len(report.errors) > 0
            assert "not found" in report.errors[0].lower()

    @patch('src.core.maintenance.MAINTENANCE_ENABLED', True)
    @patch('src.core.maintenance.DB_PATH', './nonexistent.db')
    def test_empty_database_file(self):
        """Test integrity check with empty database file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_db = os.path.join(tmpdir, "empty.db")
            # Create empty file
            Path(empty_db).touch()

            with patch('src.core.maintenance.DB_PATH', empty_db):
                report = check_database_integrity()

                assert report.operation == "database_integrity_check"
                assert len(report.errors) > 0
                assert "empty" in report.errors[0].lower()


@pytest.mark.skipif(not MAINTENANCE_ENABLED, reason="Maintenance system disabled")
class TestVectorValidation:
    """Test vector index validation."""

    @patch('src.core.maintenance.MAINTENANCE_ENABLED', True)
    @patch('src.core.maintenance.are_vector_features_enabled')
    def test_vector_validation_disabled_features(self, mock_enabled):
        """Test vector validation when features disabled."""
        mock_enabled.return_value = False

        report = validate_vector_index()

        assert report.operation == "vector_index_validation"
        assert report.metadata["vector_features"] == "disabled"
        assert len(report.recommendations) > 0
        assert "disabled" in report.recommendations[0]

    @patch('src.core.maintenance.MAINTENANCE_ENABLED', True)
    @patch('src.core.maintenance.are_vector_features_enabled')
    @patch('src.core.maintenance.get_vector_store')
    @patch('src.core.maintenance.get_embedding_provider')
    def test_vector_validation_unavailable_store(self, mock_embed, mock_store, mock_enabled):
        """Test vector validation with unavailable store."""
        mock_enabled.return_value = True
        mock_store.return_value = None
        mock_embed.return_value = None

        report = validate_vector_index()

        assert report.operation == "vector_index_validation"
        assert len(report.errors) >= 2  # Store and provider errors
        assert report.metadata["can_export"] is False


@pytest.mark.skipif(not MAINTENANCE_ENABLED, reason="Maintenance system disabled")
class TestCleanupOperations:
    """Test orphaned data cleanup operations."""

    @patch('src.core.maintenance.MAINTENANCE_ENABLED', True)
    def test_cleanup_orphaned_data_structure(self):
        """Test cleanup operation basic structure."""
        # Test that cleanup runs without throwing errors (detailed mocks would be complex)
        report = cleanup_orphaned_data()

        assert report.operation == "orphaned_data_cleanup"
        assert isinstance(report, MaintenanceReport)
        assert report.completed_at is not None
        assert "backup_created" in report.metadata

    @patch('src.core.maintenance.MAINTENANCE_ENABLED', True)
    def test_cleanup_operations_list(self):
        """Test cleanup operations metadata."""
        report = cleanup_orphaned_data()

        # Check metadata structure
        assert isinstance(report.metadata, dict)
        assert "cleanup_successful" in report.metadata

    @patch('src.core.maintenance.MAINTENANCE_ENABLED', True)
    @patch('src.core.maintenance.list_keys')
    @patch('src.core.maintenance.are_vector_features_enabled')
    def test_cleanup_with_kv_data(self, mock_vector_enabled, mock_list_keys):
        """Test cleanup with mock KV data."""
        mock_vector_enabled.return_value = False  # Disable vector operations for simple test
        mock_list_keys.return_value = [
            type('KVRecord', (), {"key": "test1", "sensitive": False})(),
            type('KVRecord', (), {"key": "test2", "sensitive": True})()
        ]

        report = cleanup_orphaned_data()

        assert report.operation == "orphaned_data_cleanup"
        assert report.completed_at is not None


@pytest.mark.skipif(not MAINTENANCE_ENABLED, reason="Maintenance system disabled")
class TestIndexRebuild:
    """Test vector index rebuild functionality."""

    @patch('src.core.maintenance.MAINTENANCE_ENABLED', True)
    @patch('src.core.maintenance.are_vector_features_enabled')
    def test_rebuild_vector_disabled_features(self, mock_enabled):
        """Test vector rebuild when features disabled."""
        mock_enabled.return_value = False

        report = rebuild_vector_index(force=False)

        assert report.operation == "vector_index_rebuild"
        assert len(report.errors) > 0
        assert "disabled" in report.errors[0]

    @patch('src.core.maintenance.MAINTENANCE_ENABLED', True)
    @patch('src.core.maintenance.are_vector_features_enabled')
    @patch('src.core.maintenance.get_vector_store')
    @patch('src.core.maintenance.get_embedding_provider')
    @patch('src.core.maintenance.list_keys')
    def test_rebuild_vector_unavailable(self, mock_list_keys, mock_embed, mock_store, mock_enabled):
        """Test vector rebuild with unavailable components."""
        mock_enabled.return_value = True
        mock_store.return_value = None
        mock_embed.return_value = None
        mock_list_keys.return_value = []

        report = rebuild_vector_index(force=True)

        assert report.operation == "vector_index_rebuild"
        assert len(report.errors) > 0
        assert "not available" in " ".join(report.errors).lower()


@pytest.mark.skipif(not MAINTENANCE_ENABLED, reason="Maintenance system disabled")
class TestFullMaintenance:
    """Test comprehensive maintenance operations."""

    @patch('src.core.maintenance.MAINTENANCE_ENABLED', True)
    def test_full_maintenance_returns_reports(self):
        """Test that full maintenance returns a list of reports."""
        reports = perform_full_maintenance()

        assert isinstance(reports, list)
        assert len(reports) >= 3  # At least integrity, validation, cleanup

        operations = [r.operation for r in reports]
        assert "database_integrity_check" in operations
        assert "vector_index_validation" in operations
        assert "orphaned_data_cleanup" in operations

    @patch('src.core.maintenance.MAINTENANCE_ENABLED', True)
    def test_full_maintenance_report_structure(self):
        """Test structure of full maintenance reports."""
        reports = perform_full_maintenance()

        for report in reports:
            assert isinstance(report, MaintenanceReport)
            assert report.operation
            assert report.started_at
            assert report.completed_at is not None
            assert isinstance(report.metadata, dict)
            assert isinstance(report.errors, list)
            assert isinstance(report.recommendations, list)
            assert isinstance(report.actions_taken, list)


@pytest.mark.skipif(not MAINTENANCE_ENABLED, reason="Maintenance system disabled")
class TestMaintenanceSafety:
    """Test safety features in maintenance operations."""

    @patch('src.core.maintenance.MAINTENANCE_ENABLED', True)
    @patch('src.core.maintenance._create_backup_for_maintenance')
    def test_cleanup_backup_creation(self, mock_backup):
        """Test that cleanup operations attempt backup creation."""
        mock_backup.return_value = "/path/to/backup"

        cleanup_orphaned_data()

        mock_backup.assert_called_once_with("orphaned_data_cleanup")

    @patch('src.core.maintenance.MAINTENANCE_ENABLED', True)
    @patch('src.core.maintenance._create_backup_for_maintenance')
    def test_rebuild_backup_creation(self, mock_backup):
        """Test that rebuild operations create backups."""
        mock_backup.return_value = "/path/to/backup"

        rebuild_vector_index(backup_first=True)

        mock_backup.assert_called_once_with("rebuild_vector_index")


@pytest.mark.skipif(not MAINTENANCE_ENABLED, reason="Maintenance system disabled")
class TestMaintenanceAuditLogging:
    """Test that maintenance operations properly log audit events."""

    @patch('src.core.maintenance.MAINTENANCE_ENABLED', True)
    @patch('util.logging.audit_event')
    def test_cleanup_logs_audit_event(self, mock_audit):
        """Test that cleanup operations log audit events."""
        cleanup_orphaned_data()

        mock_audit.assert_called_once()
        call_args = mock_audit.call_args[1]  # kwargs
        assert "maintenance_completed" in call_args["event_type"]
        assert call_args["identifiers"]["operation"] == "orphaned_data_cleanup"


@pytest.mark.skipif(not MAINTENANCE_ENABLED, reason="Maintenance system disabled")
class TestMaintenanceErrorHandling:
    """Test error handling in maintenance operations."""

    @patch('src.core.maintenance.MAINTENANCE_ENABLED', True)
    def test_operation_exceptions_handled(self):
        """Test that maintenance properly handles unexpected exceptions."""
        # This mostly tests that exceptions don't crash the entire process
        reports = perform_full_maintenance()

        # Check that we got some reports even if some operations failed
        assert len(reports) > 0

        # At least some operations should have completed
        completed_reports = [r for r in reports if r.completed_at is not None]
        assert len(completed_reports) > 0
