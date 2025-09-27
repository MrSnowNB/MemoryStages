#!/usr/bin/env python3
"""
Stage 6 scope only. Do not implement beyond this file's responsibilities.
Privacy, backup, and maintenance - ensures data protection and system integrity.

Command-line restore utility with validation and conflict resolution.
"""

import argparse
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.backup import restore_backup, RestoreError


def main():
    parser = argparse.ArgumentParser(
        description="Restore from encrypted backups with validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s my_backup my_backup.manifest.json  # Basic restore
  %(prog)s my_backup my_backup.manifest.json --dry-run  # Validate without restoring
  %(prog)s my_backup my_backup.manifest.json --admin-confirmed  # Confirm sensitive data restore

The restore process:
1. Validates backup integrity and checksums
2. Checks permission requirements for sensitive data
3. Creates safety backup of current database
4. Restores SQLite database and KV records
5. Optionally restores vector data
6. Logs comprehensive audit trail

Environment variables:
- BACKUP_ENABLED=true (required)
- BACKUP_MASTER_PASSWORD=... (for decryption, change from default)

Safety features:
- Automatic pre-restore backup creation
- Dry-run validation mode
- Comprehensive error recovery
- Audit logging for all operations
        """
    )

    parser.add_argument(
        "backup_path",
        help="Path to the backup file"
    )

    parser.add_argument(
        "manifest_path",
        help="Path to the backup manifest file (usually backup_path.manifest.json)"
    )

    parser.add_argument(
        "--admin-confirmed", "-c",
        action="store_true",
        help="Confirm admin approval for sensitive data restoration"
    )

    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Validate backup without performing restoration"
    )

    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Skip additional safety confirmations (use with caution)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed restoration information"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.backup_path or not args.manifest_path:
        parser.error("Both backup_path and manifest_path are required")

    # Check if manifest file exists
    manifest_path = Path(args.manifest_path)
    if not manifest_path.exists():
        print(f"ERROR: Manifest file not found: {manifest_path}")
        return 1

    # Check if backup file exists
    backup_path = Path(args.backup_path)
    if not backup_path.exists():
        print(f"ERROR: Backup file not found: {backup_path}")
        return 1

    # Read and display manifest information
    try:
        import json
        with open(manifest_path, 'r') as f:
            manifest_data = json.load(f)

        backup_id = manifest_data.get('backup_id', 'unknown')
        backup_type = manifest_data.get('backup_type', 'unknown')
        includes_sensitive = manifest_data.get('includes_sensitive', False)
        encrypted = manifest_data.get('encrypted', False)
        created_at = manifest_data.get('created_at', 'unknown')

        print("Backup Information:")
        print(f"  ID: {backup_id}")
        print(f"  Type: {backup_type}")
        print(f"  Created: {created_at}")
        print(f"  Encrypted: {encrypted}")
        print(f"  Includes Sensitive: {includes_sensitive}")
        print()

        # Validate sensitive data permissions
        if includes_sensitive and not args.admin_confirmed and not args.dry_run:
            print("ERROR: Restoring sensitive data requires --admin-confirmed flag")
            print("This operation will overwrite existing data and be fully audited.")
            return 1

        # Safety confirmation for non-dry-run operations
        if not args.dry_run and not args.force:
            print("WARNING: This will restore from backup and may overwrite existing data!")
            print(f"Target database: {os.getenv('DB_PATH', './data/memory.db')}")
            if includes_sensitive:
                print("WARNING: This backup contains sensitive data!")
            print()

            response = input("Are you sure you want to proceed? (type 'yes' to continue): ")
            if response.lower() != 'yes':
                print("Operation cancelled by user.")
                return 0

        # Perform restoration
        result = restore_backup(
            backup_path=str(backup_path),
            manifest_path=str(manifest_path),
            admin_confirmed=args.admin_confirmed,
            dry_run=args.dry_run
        )

        if args.dry_run:
            print("DRY RUN - Backup validation completed successfully")
            summary = result.get("backup_data_summary", {})
            print(f"KV Records: {summary.get('kv_records_count', 0)}")
            print(f"Events: {summary.get('events_count', 0)}")
            print(f"Vector Data: {'Present' if summary.get('vector_data_present', False) else 'Not present'}")
            print(f"Sensitive Data: {'Included' if summary.get('includes_sensitive', False) else 'Redacted'}")
        else:
            statistics = result.get("statistics", {})
            success = result.get("success", False)

            if success:
                print("Restore completed successfully")
                print(f"KV Records Restored: {statistics.get('kv_records_restored', 0)}")
                print(f"Events Restored: {statistics.get('events_restored', 0)}")
                print(f"Database Restored: {statistics.get('database_restored', False)}")
                print(f"Vector Data Restored: {statistics.get('vector_data_restored', False)}")

                warnings = statistics.get('warnings', [])
                if warnings:
                    print(f"Warnings: {len(warnings)}")
                    if args.verbose:
                        for warning in warnings:
                            print(f"  - {warning}")
            else:
                print("ERROR: Restore operation failed")
                return 1

        return 0

    except RestoreError as e:
        print(f"ERROR: Restore failed: {e}")
        return 1
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid manifest file: {e}")
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
