"""
Stage 5 scope only. Do not implement beyond this file's responsibilities.
Operations utilities - CLI tools for administrative operations.
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.backup import create_backup, restore_backup
from src.core.maintenance import run_integrity_check, get_maintenance_status
from util.logging import logger


def create_backup_command():
    """CLI command for creating system backups."""
    parser = argparse.ArgumentParser(description="Create MemoryStages system backup")
    parser.add_argument(
        "--output-dir",
        default="./backups",
        help="Output directory for backup (default: ./backups)"
    )
    parser.add_argument(
        "--include-sensitive",
        action="store_true",
        help="Include sensitive data in backup (requires explicit confirmation)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force backup creation without additional prompts"
    )

    args = parser.parse_args()

    # Validate dashboard features are enabled
    dashboard_enabled = os.getenv("DASHBOARD_ENABLED", "false").lower() == "true"
    maintenance_mode = os.getenv("DASHBOARD_MAINTENANCE_MODE", "false").lower() == "true"

    if not dashboard_enabled or not maintenance_mode:
        print("❌ ERROR: Dashboard must be enabled with maintenance mode for backup operations")
        print("   Set DASHBOARD_ENABLED=true and DASHBOARD_MAINTENANCE_MODE=true")
        sys.exit(1)

    if args.include_sensitive and not args.force:
        print("⚠️  WARNING: Including sensitive data in backup")
        print("This will include potentially sensitive information like API keys, tokens, and private data.")
        response = input("Are you sure you want to continue? (yes/no): ").strip().lower()
        if response != "yes":
            print("Backup cancelled.")
            sys.exit(0)

    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{args.output_dir}/backup_{timestamp}"

    print(f"🔄 Creating backup to {backup_path}...")

    try:
        result = create_backup(
            backup_path=backup_path,
            include_sensitive=args.include_sensitive
        )

        if result["success"]:
            print("✅ Backup completed successfully")
            print(f"   Backup location: {result.get('backup_path', backup_path)}")

            # Show backup contents summary if available
            if "files_backed_up" in result:
                print(f"   Files backed up: {result['files_backed_up']}")
            if "total_size" in result:
                print(f"   Total size: {result['total_size']}")

        else:
            print("❌ Backup failed")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Backup failed with unexpected error: {e}")
        logger.error(f"CLI backup failed: {e}")
        sys.exit(1)


def restore_backup_command():
    """CLI command for restoring system from backup."""
    parser = argparse.ArgumentParser(description="Restore MemoryStages system from backup")
    parser.add_argument(
        "backup_path",
        help="Path to backup directory to restore from"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force restore without additional prompts"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be restored without actually restoring"
    )

    args = parser.parse_args()

    # Validate dashboard features are enabled
    dashboard_enabled = os.getenv("DASHBOARD_ENABLED", "false").lower() == "true"
    maintenance_mode = os.getenv("DASHBOARD_MAINTENANCE_MODE", "false").lower() == "true"

    if not dashboard_enabled or not maintenance_mode:
        print("❌ ERROR: Dashboard must be enabled with maintenance mode for restore operations")
        print("   Set DASHBOARD_ENABLED=true and DASHBOARD_MAINTENANCE_MODE=true")
        sys.exit(1)

    if not os.path.exists(args.backup_path):
        print(f"❌ ERROR: Backup path does not exist: {args.backup_path}")
        sys.exit(1)

    if not args.dry_run and not args.force:
        print("⚠️  WARNING: Restoring from backup will overwrite current system state")
        print("This operation cannot be undone. Ensure you have a recent backup if needed.")
        response = input("Are you sure you want to proceed with restore? (yes/no): ").strip().lower()
        if response != "yes":
            print("Restore cancelled.")
            sys.exit(0)

    # Perform restore
    if args.dry_run:
        print(f"🔍 Performing dry-run restore from {args.backup_path}...")
    else:
        print(f"🔄 Restoring from backup {args.backup_path}...")

    try:
        result = restore_backup(
            backup_path=args.backup_path,
            dry_run=args.dry_run
        )

        if result["success"]:
            if args.dry_run:
                print("✅ Dry-run completed successfully")
                print("   The following would be restored:")
                if "files_to_restore" in result:
                    for file_path in result["files_to_restore"][:10]:  # Limit output
                        print(f"     - {file_path}")
                    if len(result["files_to_restore"]) > 10:
                        print(f"     ... and {len(result['files_to_restore']) - 10} more files")
            else:
                print("✅ Restore completed successfully")

            # Show restore details
            if "files_restored" in result:
                print(f"   Files restored: {result['files_restored']}")

        else:
            print("❌ Restore failed")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Restore failed with unexpected error: {e}")
        logger.error(f"CLI restore failed: {e}")
        sys.exit(1)


def integrity_check_command():
    """CLI command for running system integrity checks."""
    parser = argparse.ArgumentParser(description="Run MemoryStages system integrity checks")
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed integrity check results"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format"
    )

    args = parser.parse_args()

    # Validate dashboard features are enabled
    dashboard_enabled = os.getenv("DASHBOARD_ENABLED", "false").lower() == "true"

    if not dashboard_enabled:
        print("❌ ERROR: Dashboard must be enabled for integrity check operations")
        print("   Set DASHBOARD_ENABLED=true")
        sys.exit(1)

    print("🔍 Running system integrity checks...")

    try:
        result = run_integrity_check()

        if result["success"]:
            print("✅ Integrity checks completed")

            issues_found = result.get("issues_found", 0)
            checks_performed = result.get("checks_performed", [])

            if issues_found > 0:
                print(f"⚠️  Issues found: {issues_found}")
            else:
                print("✅ No integrity issues detected")

            print(f"   Checks performed: {len(checks_performed)}")

            if args.detailed:
                print("\nDetailed Results:")
                print(f"   Status: {'PASS' if issues_found == 0 else 'WARN'}")

                if checks_performed:
                    print("   Checks run:")
                    for check in checks_performed[:10]:  # Limit output
                        print(f"     - {check}")

                recommendations = result.get("recommendations", [])
                if recommendations:
                    print("   Recommendations:")
                    for rec in recommendations[:5]:  # Limit output
                        print(f"     - {rec}")

        else:
            print("❌ Integrity checks failed")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Integrity check failed with unexpected error: {e}")
        logger.error(f"CLI integrity check failed: {e}")
        sys.exit(1)


def maintenance_status_command():
    """CLI command for showing maintenance status."""
    parser = argparse.ArgumentParser(description="Show MemoryStages maintenance status")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output status in JSON format"
    )

    args = parser.parse_args()

    # Validate dashboard features are enabled
    dashboard_enabled = os.getenv("DASHBOARD_ENABLED", "false").lower() == "true"

    if not dashboard_enabled:
        print("❌ ERROR: Dashboard must be enabled for maintenance status")
        print("   Set DASHBOARD_ENABLED=true")
        sys.exit(1)

    try:
        status = get_maintenance_status()

        if args.json:
            import json
            print(json.dumps(status, indent=2, default=str))
        else:
            print("🔧 MemoryStages Maintenance Status")

            last_backup = status.get("last_backup_time")
            if last_backup:
                print(f"   Last backup: {last_backup}")
            else:
                print("   Last backup: Never")

            vector_health = status.get("vector_store_health", "Unknown")
            print(f"   Vector store health: {vector_health}")

            db_size = status.get("database_size", "Unknown")
            print(f"   Database size: {db_size}")

            scheduled_tasks = status.get("scheduled_tasks", [])
            if scheduled_tasks:
                print(f"   Scheduled tasks: {len(scheduled_tasks)}")
                for task in scheduled_tasks[:3]:  # Show first 3
                    print(f"     - {task.get('task_type', 'Unknown')} at {task.get('schedule_time', 'Unknown')}")
                if len(scheduled_tasks) > 3:
                    print(f"     ... and {len(scheduled_tasks) - 3} more")
            else:
                print("   Scheduled tasks: None")

    except Exception as e:
        print(f"❌ Failed to get maintenance status: {e}")
        logger.error(f"CLI maintenance status failed: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point for operations utilities."""
    parser = argparse.ArgumentParser(
        description="MemoryStages Operations CLI Utilities",
        prog="python scripts/ops_util.py"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create system backup")
    backup_parser.set_defaults(func=create_backup_command)

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("backup_path", help="Path to backup to restore from")
    restore_parser.set_defaults(func=restore_backup_command)

    # Integrity check command
    integrity_parser = subparsers.add_parser("integrity", help="Run integrity checks")
    integrity_parser.set_defaults(func=integrity_check_command)

    # Maintenance status command
    status_parser = subparsers.add_parser("status", help="Show maintenance status")
    status_parser.set_defaults(func=maintenance_status_command)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Run the selected command
    args.func()


if __name__ == "__main__":
    main()
