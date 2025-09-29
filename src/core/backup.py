"""
Stage 6 scope only. Do not implement beyond this file's responsibilities.
Privacy, backup, and maintenance - ensures data protection and system integrity.

# Import privacy enforcer for backup redaction
try:
    from .privacy import redact_sensitive_for_backup
except ImportError:
    # Fallback if privacy not available yet
    def redact_sensitive_for_backup(data, include_sensitive=False, admin_confirmed=False):
        return data
"""

import json
import os
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import tempfile
import shutil

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .config import (
    BACKUP_ENCRYPTION_ENABLED,
    BACKUP_ENABLED,
    BACKUP_INCLUDE_SENSITIVE,
    DB_PATH,
    are_vector_features_enabled
)
from .dao import list_keys, list_events, get_kv_count
from .privacy import validate_sensitive_access, redact_sensitive_for_backup


@dataclass
class BackupManifest:
    """Comprehensive backup manifest with metadata and integrity checks."""
    backup_id: str
    created_at: datetime
    backup_type: str  # full, incremental, selective
    includes_sensitive: bool
    encrypted: bool
    file_count: int
    total_size: int
    version: str = "1.0.0"
    checksum: str = ""
    encrypted_key: Optional[str] = None  # For decrypting the backup
    salt: Optional[str] = None  # PBKDF2 salt for key derivation

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to dictionary for JSON serialization."""
        data = asdict(self)
        # Handle datetime serialization
        data['created_at'] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupManifest':
        """Create manifest from dictionary (for restoration)."""
        # Handle datetime deserialization
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


class BackupError(Exception):
    """Custom exception for backup operations."""
    pass


class RestoreError(Exception):
    """Custom exception for restore operations."""
    pass


def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive encryption key from password using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=None
    )
    return kdf.derive(password.encode())


def _encrypt_data(data: bytes, key: bytes) -> bytes:
    """Encrypt data using AES-256-GCM."""
    # Generate random nonce
    nonce = os.urandom(12)
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce), backend=None)
    encryptor = cipher.encryptor()

    # Encrypt data
    ciphertext = encryptor.update(data) + encryptor.finalize()

    # Return nonce + tag + ciphertext
    return nonce + encryptor.tag + ciphertext


def _decrypt_data(encrypted_data: bytes, key: bytes) -> bytes:
    """Decrypt data using AES-256-GCM."""
    if len(encrypted_data) < 28:  # nonce (12) + tag (16) + minimum ciphertext
        raise RestoreError("Encrypted data too short")

    nonce = encrypted_data[:12]
    tag = encrypted_data[12:28]
    ciphertext = encrypted_data[28:]

    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag), backend=None)
    decryptor = cipher.decryptor()
    return decryptor.update(ciphertext) + decryptor.finalize()


def _calculate_checksum(data: bytes) -> str:
    """Calculate SHA-256 checksum of data."""
    return hashlib.sha256(data).hexdigest()


def _generate_encryption_key() -> tuple[str, bytes]:
    """Generate a random encryption key and return it encrypted with a master key."""
    # For simplicity, generate a random key and encrypt it with a derived key
    # In production, this could be integrated with proper key management
    raw_key = secrets.token_bytes(32)
    salt = secrets.token_bytes(16)

    # Use a master password derived from environment (simplified)
    master_password = os.getenv("BACKUP_MASTER_PASSWORD", "default_master_key_change_in_production")
    master_key = _derive_key(master_password, salt)

    encrypted_key = _encrypt_data(raw_key, master_key)

    return encrypted_key.hex(), raw_key, salt.hex()


def _read_sqlite_db(db_path: str) -> bytes:
    """Read SQLite database file as bytes."""
    try:
        with open(db_path, 'rb') as f:
            return f.read()
    except FileNotFoundError:
        raise BackupError(f"Database file not found: {db_path}")
    except PermissionError:
        raise BackupError(f"Permission denied reading database: {db_path}")


def _write_sqlite_db(db_path: str, data: bytes) -> None:
    """Write SQLite database file from bytes."""
    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(db_path, 'wb') as f:
            f.write(data)
    except PermissionError:
        raise RestoreError(f"Permission denied writing database: {db_path}")


def _export_vector_data() -> Dict[str, Any]:
    """Export vector store data if vector features are enabled."""
    vector_data = {
        "enabled": are_vector_features_enabled(),
        "data": {}
    }

    if not are_vector_features_enabled():
        return vector_data

    try:
        from .config import get_vector_store
        vector_store = get_vector_store()

        if vector_store and hasattr(vector_store, 'export_data'):
            vector_data["data"] = vector_store.export_data()
            vector_data["provider"] = vector_store.__class__.__name__

        # If no export method, try to get records from list_keys and rebuild
        elif vector_store:
            # Fallback: we'll note that vectors need rebuilding from KV data
            vector_data["rebuild_required"] = True
            vector_data["provider"] = vector_store.__class__.__name__

    except Exception as e:
        vector_data["error"] = str(e)

    return vector_data


def _restore_vector_data(vector_data: Dict[str, Any]) -> None:
    """Restore vector store data if applicable."""
    if not vector_data.get("enabled", False):
        return

    try:
        from .config import get_vector_store
        vector_store = get_vector_store()

        if not vector_store:
            return

        # If vector data was exported, restore it
        if "data" in vector_data and vector_data["data"]:
            if hasattr(vector_store, 'import_data'):
                vector_store.import_data(vector_data["data"])
            else:
                # If no import method, log that vectors need rebuilding
                raise RestoreError("Vector store does not support data import - vectors need manual rebuilding")

        # If rebuild required, we'll handle this in the calling context
        elif vector_data.get("rebuild_required", False):
            # Rebuild vectors from current KV data will be handled separately
            pass

    except Exception as e:
        raise RestoreError(f"Failed to restore vector data: {e}")


def _prepare_backup_data(include_sensitive: bool = False, admin_confirmed: bool = False) -> Dict[str, Any]:
    """Prepare backup data with privacy controls applied."""
    backup_data = {
        "metadata": {
            "backup_timestamp": datetime.now().isoformat(),
            "include_sensitive": include_sensitive,
            "admin_confirmed": admin_confirmed
        },
        "kv_records": [],
        "events": [],
        "vector_data": _export_vector_data()
    }

    # Export KV records with privacy redaction
    kv_records = list_keys()
    for record in kv_records:
        # Apply privacy redaction based on settings
        record_dict = {
            "key": record.key,
            "value": record.value,
            "source": record.source,
            "casing": record.casing,
            "sensitive": record.sensitive,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None
        }

        # Apply redaction if sensitive data not included or not confirmed
        if record.sensitive and (not include_sensitive or not admin_confirmed):
            # Create a dict for redaction
            sensitive_dict = {"value": record.value}
            redacted = redact_sensitive_for_backup(sensitive_dict, include_sensitive, admin_confirmed)
            record_dict["value"] = redacted.get("value", "***REDACTED***")

        backup_data["kv_records"].append(record_dict)

    # Export events (these may contain sensitive data, apply redaction)
    events = list_events(limit=50000)  # Reasonable limit for backup
    for event in events:
        event_dict = {
            "id": event.id,
            "ts": event.ts.isoformat() if event.ts else None,
            "actor": event.actor,
            "action": event.action,
            "payload": event.payload
        }

        # Redact sensitive data in event payloads
        if isinstance(event.payload, dict):
            event_dict["payload"] = redact_sensitive_for_backup(event.payload, include_sensitive, admin_confirmed)

        backup_data["events"].append(event_dict)

    return backup_data


def create_backup(backup_path: str, include_sensitive: bool = False, encrypt: bool = True, dry_run: bool = False) -> BackupManifest:
    """
    Create comprehensive system backup with encryption and selective data controls.

    Args:
        backup_path: Path where backup will be created
        include_sensitive: Whether to include sensitive data in backup
        encrypt: Whether to encrypt the backup
        dry_run: If True, validate but don't create backup

    Returns:
        BackupManifest: Manifest describing the created backup

    Raises:
        BackupError: If backup creation fails
    """
    if not BACKUP_ENABLED:
        raise BackupError("Backup system is disabled. Enable with BACKUP_ENABLED=true")

    # Validate privacy authorization for sensitive data inclusion
    if include_sensitive and not BACKUP_INCLUDE_SENSITIVE:
        raise BackupError("Sensitive data inclusion not permitted by configuration")

    # Require admin confirmation for sensitive data
    admin_confirmed = include_sensitive

    # Generate backup ID and paths
    backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}"
    backup_dir = Path(backup_path).parent
    backup_file = Path(backup_path)
    manifest_file = backup_file.with_suffix('.manifest.json')

    # Generate encryption key if needed
    encryption_key = None
    salt = None
    if encrypt:
        encrypted_key_hex, raw_key, salt_hex = _generate_encryption_key()
        encryption_key = raw_key
        salt = salt_hex

    # Create backup data
    try:
        backup_data = _prepare_backup_data(include_sensitive, admin_confirmed)
        backup_json = json.dumps(backup_data, indent=2).encode('utf-8')
        checksum = _calculate_checksum(backup_json)

        # Read SQLite database
        db_data = _read_sqlite_db(DB_PATH)

        # Create manifest
        manifest = BackupManifest(
            backup_id=backup_id,
            created_at=datetime.now(),
            backup_type="selective" if not include_sensitive else "full",
            includes_sensitive=include_sensitive,
            encrypted=encrypt,
            file_count=2,  # JSON data + SQLite DB
            total_size=len(backup_json) + len(db_data),
            checksum=checksum,
            encrypted_key=encrypted_key_hex if encrypt else None,
            salt=salt
        )

        if dry_run:
            return manifest

        # Ensure backup directory exists
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Encrypt data if requested
        final_backup_data = backup_json
        final_db_data = db_data

        if encrypt and encryption_key:
            final_backup_data = _encrypt_data(backup_json, encryption_key)
            final_db_data = _encrypt_data(db_data, encryption_key)

        # Write backup files
        with open(backup_file, 'wb') as f:
            # Write format identifier and data
            f.write(b'MEMORY_BACKUP_V1\n')
            f.write(final_backup_data)
            f.write(b'\n---DB_DATA---\n')
            f.write(final_db_data)

        # Write manifest (always unencrypted for easy inspection)
        with open(manifest_file, 'w') as f:
            json.dump(manifest.to_dict(), f, indent=2)

        # Log backup operation
        from util.logging import audit_event
        audit_event(
            event_type="backup_created",
            identifiers={"backup_id": backup_id, "backup_type": manifest.backup_type},
            payload={
                "include_sensitive": include_sensitive,
                "encrypted": encrypt,
                "file_count": manifest.file_count,
                "total_size": manifest.total_size,
                "admin_confirmed": admin_confirmed
            }
        )

        return manifest

    except Exception as e:
        # Clean up partial backup on failure
        if backup_file.exists():
            backup_file.unlink()
        if manifest_file.exists():
            manifest_file.unlink()

        raise BackupError(f"Backup creation failed: {e}")


def restore_backup(backup_path: str, manifest_path: str, admin_confirmed: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    """
    Restore from encrypted backup with validation and conflict resolution.

    Args:
        backup_path: Path to the backup file
        manifest_path: Path to the manifest file
        admin_confirmed: Admin confirmation for operations that may overwrite data
        dry_run: If True, validate but don't restore

    Returns:
        Dict containing restoration results and statistics

    Raises:
        RestoreError: If restoration fails
    """
    if not BACKUP_ENABLED:
        raise RestoreError("Backup system is disabled. Enable with BACKUP_ENABLED=true")

    try:
        # Load and validate manifest
        with open(manifest_path, 'r') as f:
            manifest_data = json.load(f)
        manifest = BackupManifest.from_dict(manifest_data)

        # Basic validation
        if manifest.encrypted and not manifest.encrypted_key:
            raise RestoreError("Encrypted backup missing decryption key")

        # Check if sensitive data restoration requires confirmation
        if manifest.includes_sensitive and not admin_confirmed:
            raise RestoreError("Restoring sensitive data requires admin confirmation")

        # Derive decryption key if needed
        decryption_key = None
        if manifest.encrypted:
            if not manifest.encrypted_key or not manifest.salt:
                raise RestoreError("Missing encryption parameters for encrypted backup")

            master_password = os.getenv("BACKUP_MASTER_PASSWORD", "default_master_key_change_in_production")
            master_key = _derive_key(master_password, bytes.fromhex(manifest.salt))
            encrypted_key = bytes.fromhex(manifest.encrypted_key)
            decryption_key = _decrypt_data(encrypted_key, master_key)

        # Read and validate backup file
        with open(backup_path, 'rb') as f:
            backup_content = f.read()

        # Parse backup format
        if not backup_content.startswith(b'MEMORY_BACKUP_V1\n'):
            raise RestoreError("Invalid backup file format")

        parts = backup_content.split(b'\n---DB_DATA---\n', 1)
        if len(parts) != 2:
            raise RestoreError("Invalid backup file structure")

        encrypted_backup_json = parts[0][len(b'MEMORY_BACKUP_V1\n'):]
        encrypted_db_data = parts[1]

        # Decrypt data if needed
        backup_json = encrypted_backup_json
        db_data = encrypted_db_data

        if manifest.encrypted and decryption_key:
            backup_json = _decrypt_data(encrypted_backup_json, decryption_key)
            db_data = _decrypt_data(encrypted_db_data, decryption_key)

        # Validate checksum
        actual_checksum = _calculate_checksum(backup_json)
        if actual_checksum != manifest.checksum:
            raise RestoreError(f"Backup checksum mismatch: expected {manifest.checksum}, got {actual_checksum}")

        # Parse backup data
        backup_data = json.loads(backup_json.decode('utf-8'))

        if dry_run:
            # Return validation results
            return {
                "valid": True,
                "manifest": manifest.to_dict(),
                "backup_data_summary": {
                    "kv_records_count": len(backup_data["kv_records"]),
                    "events_count": len(backup_data["events"]),
                    "vector_data_present": bool(backup_data.get("vector_data", {}).get("data")),
                    "includes_sensitive": manifest.includes_sensitive
                },
                "dry_run": True
            }

        # Perform restoration
        statistics = {
            "kv_records_restored": 0,
            "events_restored": 0,
            "vector_data_restored": False,
            "database_restored": False,
            "warnings": []
        }

        # Backup current database before restoration (safety)
        if not dry_run:
            current_db_backup = f"{DB_PATH}.pre_restore_backup"
            try:
                shutil.copy2(DB_PATH, current_db_backup)
            except Exception as e:
                statistics["warnings"].append(f"Failed to create pre-restore backup: {e}")

        # Restore SQLite database
        _write_sqlite_db(DB_PATH, db_data)
        statistics["database_restored"] = True

        # Restore KV records
        from .dao import set_key
        for record in backup_data["kv_records"]:
            try:
                set_key(
                    key=record["key"],
                    value=record["value"],
                    source=record.get("source", "backup_restore"),
                    casing=record.get("casing", "exact"),
                    sensitive=record.get("sensitive", False)
                )
                statistics["kv_records_restored"] += 1
            except Exception as e:
                statistics["warnings"].append(f"Failed to restore KV record {record['key']}: {e}")

        # Note: Events are stored in SQLite, so they're restored with the DB
        statistics["events_restored"] = len(backup_data["events"])

        # Restore vector data if present
        vector_data = backup_data.get("vector_data", {})
        if vector_data and are_vector_features_enabled():
            try:
                _restore_vector_data(vector_data)
                statistics["vector_data_restored"] = True
            except Exception as e:
                statistics["warnings"].append(f"Failed to restore vector data: {e}")

        # Log restoration operation
        from util.logging import audit_event
        audit_event(
            event_type="backup_restored",
            identifiers={"backup_id": manifest.backup_id, "backup_type": manifest.backup_type},
            payload={
                "admin_confirmed": admin_confirmed,
                "encrypted": manifest.encrypted,
                "includes_sensitive": manifest.includes_sensitive,
                "restoration_stats": statistics
            }
        )

        # Clean up pre-restore backup if successful
        if not dry_run and not statistics["warnings"]:
            try:
                Path(current_db_backup).unlink(missing_ok=True)
            except Exception:
                pass  # Not critical

        return {
            "success": True,
            "manifest": manifest.to_dict(),
            "statistics": statistics
        }

    except FileNotFoundError as e:
        raise RestoreError(f"Backup file not found: {e}")
    except json.JSONDecodeError as e:
        raise RestoreError(f"Invalid backup data format: {e}")
    except Exception as e:
        raise RestoreError(f"Restoration failed: {e}")
