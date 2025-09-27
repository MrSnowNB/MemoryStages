"""
Stage 6 scope only. Do not implement beyond this file's responsibilities.
Privacy, backup, and maintenance - ensures data protection and system integrity.

Tests for backup and restore functionality including encryption and privacy controls.
"""

import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.backup import (
    create_backup,
    restore_backup,
    BackupError,
    RestoreError,
    BackupManifest,
    _calculate_checksum,
    _encrypt_data,
    _decrypt_data
)
from src.core.config import BACKUP_ENABLED


@pytest.mark.skipif(not BACKUP_ENABLED, reason="Backup system disabled")
class TestBackupCore:
    """Test core backup functionality."""

    def test_checksum_calculation(self):
        """Test SHA-256 checksum calculation."""
        data = b"test data"
        expected = "916f0027a575074ce72a331777c3478d6513f786a591bd892da1a577bf2335f9"
        assert _calculate_checksum(data) == expected

    def test_encryption_decryption(self):
        """Test AES-256-GCM encryption and decryption."""
        key = os.urandom(32)
        data = b"Hello, secure world!"

        encrypted = _encrypt_data(data, key)
        decrypted = _decrypt_data(encrypted, key)

        assert decrypted == data
        assert encrypted != data

    def test_encryption_wrong_key(self):
        """Test that wrong key fails decryption."""
        key1 = os.urandom(32)
        key2 = os.urandom(32)
        data = b"Secret message"

        encrypted = _encrypt_data(data, key1)

        with pytest.raises(RestoreError):
            _decrypt_data(encrypted, key2)

    def test_backup_manifest_serialization(self):
        """Test backup manifest JSON serialization."""
        manifest = BackupManifest(
            backup_id="test_backup_123",
            created_at="2025-01-01T12:00:00",
            backup_type="full",
            includes_sensitive=True,
            encrypted=True,
            file_count=2,
            total_size=1024,
            checksum="abc123",
            encrypted_key="def456",
            salt="xyz789"
        )

        # Test serialization
        data = manifest.to_dict()
        assert data["backup_id"] == "test_backup_123"
        assert data["includes_sensitive"] is True

        # Test deserialization
        restored = BackupManifest.from_dict(data)
        assert restored.backup_id == manifest.backup_id
        assert restored.includes_sensitive == manifest.includes_sensitive

    @patch('src.core.backup.BACKUP_ENABLED', True)
    @patch('src.core.backup.DB_PATH', './test.db')
    @patch('src.core.backup._read_sqlite_db')
    @patch('src.core.backup._prepare_backup_data')
    def test_backup_creation_disabled_backup(self, mock_prepare, mock_read):
        """Test backup fails when disabled."""
        with patch('src.core.backup.BACKUP_ENABLED', False):
            with pytest.raises(BackupError, match="Backup system is disabled"):
                create_backup("test_backup", dry_run=True)

    @patch('src.core.backup.BACKUP_ENABLED', True)
    @patch('src.core.backup.DB_PATH', './test.db')
    @patch('src.core.backup._read_sqlite_db')
    @patch('src.core.backup._prepare_backup_data')
    def test_dry_run_backup(self, mock_prepare, mock_read):
        """Test dry-run backup validation."""
        mock_read.return_value = b"fake db data"
        mock_prepare.return_value = {"test": "data"}

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = create_backup(
                backup_path=os.path.join(tmpdir, "test_backup"),
                dry_run=True
            )

            assert isinstance(manifest, BackupManifest)
            assert manifest.file_count == 2
            assert manifest.total_size == 35  # len of fake data + json

    @patch('src.core.backup.BACKUP_ENABLED', True)
    @patch('src.core.backup.BACKUP_INCLUDE_SENSITIVE', False)
    def test_sensitive_data_validation(self):
        """Test sensitive data inclusion validation."""
        with pytest.raises(BackupError, match="Sensitive data inclusion not permitted"):
            create_backup("test_backup", include_sensitive=True, dry_run=True)


@pytest.mark.skipif(not BACKUP_ENABLED, reason="Backup system disabled")
class TestRestoreCore:
    """Test core restore functionality."""

    @patch('src.core.backup.BACKUP_ENABLED', True)
    def test_restore_disabled_backup(self):
        """Test restore fails when disabled."""
        with patch('src.core.backup.BACKUP_ENABLED', False):
            with pytest.raises(RestoreError, match="Backup system is disabled"):
                restore_backup("test_backup", "test_manifest.json", dry_run=True)

    @patch('src.core.backup.BACKUP_ENABLED', True)
    def test_restore_sensitive_data_validation(self):
        """Test restore sensitive data validation."""
        manifest_data = {
            "backup_id": "test_backup",
            "created_at": "2025-01-01T12:00:00",
            "backup_type": "full",
            "includes_sensitive": True,
            "encrypted": False,
            "file_count": 2,
            "total_size": 1024,
            "checksum": "test_checksum"
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = os.path.join(tmpdir, "manifest.json")
            backup_path = os.path.join(tmpdir, "backup")

            with open(manifest_path, 'w') as f:
                json.dump(manifest_data, f)

            # Create empty backup file
            Path(backup_path).touch()

            with pytest.raises(RestoreError, match="requires admin confirmation"):
                restore_backup(backup_path, manifest_path, admin_confirmed=False, dry_run=False)


@pytest.mark.skipif(not BACKUP_ENABLED, reason="Backup system disabled")
class TestVectorBackupIntegration:
    """Test vector store backup integration."""

    @patch('src.core.backup.are_vector_features_enabled')
    def test_vector_export_disabled(self, mock_enabled):
        """Test vector export when disabled."""
        mock_enabled.return_value = False

        from src.core.backup import _export_vector_data
        result = _export_vector_data()

        assert result["enabled"] is False
        assert result["data"] == {}

    @patch('src.core.backup.are_vector_features_enabled')
    @patch('src.core.backup.get_vector_store')
    def test_vector_export_memory_store(self, mock_get_store, mock_enabled):
        """Test vector export with memory store."""
        mock_enabled.return_value = True

        # Mock memory vector store
        mock_store = MagicMock()
        mock_store.export_data.return_value = {"vectors": {}, "index": {}}
        mock_get_store.return_value = mock_store

        from src.core.backup import _export_vector_data
        result = _export_vector_data()

        assert result["enabled"] is True
        assert result["data"] == {"vectors": {}, "index": {}}
        mock_store.export_data.assert_called_once()


@pytest.mark.skipif(not BACKUP_ENABLED, reason="Backup system disabled")
class TestEndToEndBackup:
    """End-to-end backup and restore tests."""

    @patch('src.core.backup.BACKUP_ENABLED', True)
    @patch('src.core.backup.DB_PATH', './test.db')
    @patch('src.core.backup._read_sqlite_db')
    @patch('src.core.backup.list_keys')
    @patch('src.core.backup.list_events')
    @patch('src.core.backup._export_vector_data')
    def test_full_backup_workflow(self, mock_vector_export, mock_events, mock_keys, mock_read):
        """Test complete backup workflow."""
        # Setup mocks
        mock_read.return_value = b"sqlite data"
        mock_keys.return_value = []
        mock_events.return_value = []
        mock_vector_export.return_value = {"enabled": False, "data": {}}

        with tempfile.TemporaryDirectory() as tmpdir:
            backup_path = os.path.join(tmpdir, "test_backup")

            # Create backup
            manifest = create_backup(backup_path, encrypt=False)

            # Verify files were created
            assert os.path.exists(backup_path)
            assert os.path.exists(f"{backup_path}.manifest.json")

            # Verify manifest
            assert manifest.backup_id.startswith("backup_")
            assert manifest.backup_type == "selective"
            assert not manifest.encrypted
            assert manifest.file_count == 2

            # Verify manifest file contents
            with open(f"{backup_path}.manifest.json", 'r') as f:
                saved_manifest = json.load(f)
                assert saved_manifest["backup_id"] == manifest.backup_id

    @patch('src.core.backup.BACKUP_ENABLED', True)
    @patch('src.core.backup._write_sqlite_db')
    @patch('src.core.backup.set_key')
    @patch('src.core.backup._restore_vector_data')
    def test_full_restore_workflow(self, mock_vector_restore, mock_set_key, mock_write_db):
        """Test complete restore workflow."""
        manifest_data = {
            "backup_id": "test_backup_restore",
            "created_at": "2025-01-01T12:00:00.000000",
            "backup_type": "selective",
            "includes_sensitive": False,
            "encrypted": False,
            "file_count": 2,
            "total_size": 100,
            "checksum": "test_checksum"
        }

        backup_data = {
            "kv_records": [{"key": "test", "value": "value", "source": "test", "casing": "exact", "sensitive": False}],
            "events": [],
            "vector_data": {"enabled": False, "data": {}}
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = os.path.join(tmpdir, "manifest.json")
            backup_path = os.path.join(tmpdir, "backup")

            # Write test manifest
            with open(manifest_path, 'w') as f:
                json.dump(manifest_data, f)

            # Write test backup data (JSON format for simplicity)
            with open(backup_path, 'wb') as f:
                f.write(b'MEMORY_BACKUP_V1\n')
                f.write(json.dumps(backup_data).encode())
                f.write(b'\n---DB_DATA---\n')
                f.write(b'sqlite_backup_data')

            # Perform restore
            result = restore_backup(backup_path, manifest_path, dry_run=True)

            # Verify dry-run result
            assert result["valid"] is True
            assert result["dry_run"] is True
            assert result["backup_data_summary"]["kv_records_count"] == 1
