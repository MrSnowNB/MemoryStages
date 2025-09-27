#!/usr/bin/env python3
"""
Stage 6 scope only. Do not implement beyond this file's responsibilities.
Privacy, backup, and maintenance - ensures data protection and system integrity.

Command-line backup utility with privacy controls and encryption.
"""

import argparse
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.backup import create_backup, BackupError


def main():
    parser = argparse.ArgumentParser(
        description="Create encrypted backups with privacy controls",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s my_backup                # Create basic backup
  %(prog)s my_backup --encrypt      # Create encrypted backup
  %(prog)s my_backup --dry-run      # Validate backup without creating
  %(prog)s my_backup --include-sensitive --admin-confirmed  # Include sensitive data

Backup creates two files:
- my_backup (encrypted backup data + SQLite database)
- my_backup.manifest.json (unencrypted manifest with metadata)

Environment variables:
- BACKUP_ENABLED=true (required)
- BACKUP_ENCRYPTION_ENABLED=true (default true)
- BACKUP_INCLUDE_SENSITIVE=false (default false)
- BACKUP_MASTER_PASSWORD=... (for encryption, change from default)
        """
    )

    parser.add_argument(
        "backup_path",
        help="Path for the backup file (without extension)"
    )

    parser.add_argument(
        "--encrypt", "-e",
        action="store_true",
        help="Force encryption (default: based on BACKUP_ENCRYPTION_ENABLED)"
    )

    parser.add_argument(
        "--no-encrypt",
        action="store_true",
        help="Disable encryption (overrides environment)"
    )

    parser.add_argument(
        "--include-sensitive", "-s",
        action="store_true",
        help="Include sensitive data in backup (requires admin confirmation)"
    )

    parser.add_argument(
        "--admin-confirmed", "-c",
        action="store_true",
        help="Confirm admin approval for sensitive data operations"
    )

    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Validate backup configuration without creating files"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed backup information"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.backup_path:
        parser.error("Backup path is required")

    # Handle encryption flags
    encrypt = args.encrypt
    if args.no_encrypt:
        encrypt = False

    # Validate sensitive data requirements
    if args.include_sensitive and not args.admin_confirmed:
        print("ERROR: Including sensitive data requires --admin-confirmed flag")
        print("This operation will be logged and audited.")
        return 1

    try:
        # Create the backup
        manifest = create_backup(
            backup_path=args.backup_path,
            include_sensitive=args.include_sensitive,
            encrypt=encrypt,
            dry_run=args.dry_run
        )

        if args.dry_run:
            print("DRY RUN - Backup validation completed successfully")
            print(f"Backup Type: {manifest.backup_type}")
            print(f"Expected Size: {manifest.total_size:,} bytes")
            print(f"Estimated Files: {manifest.file_count}")
            if manifest.includes_sensitive:
                print("WARNING: This backup includes sensitive data")
            else:
                print("Privacy: Sensitive data will be redacted")
        else:
            print(f"Backup created successfully: {args.backup_path}")
            print(f"Backup ID: {manifest.backup_id}")
            print(f"Type: {manifest.backup_type}")
            print(f"Size: {manifest.total_size:,} bytes")
            print(f"Encrypted: {manifest.encrypted}")
            if args.verbose:
                print(f"Created: {manifest.created_at}")
                print(f"Files: {manifest.file_count}")
                print("Manifest: {args.backup_path}.manifest.json")

        return 0

    except BackupError as e:
        print(f"ERROR: Backup failed: {e}")
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
