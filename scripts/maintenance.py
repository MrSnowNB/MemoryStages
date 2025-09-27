#!/usr/bin/env python3
"""
Stage 6 scope only. Do not implement beyond this file's responsibilities.
Privacy, backup, and maintenance - ensures data protection and system integrity.

Command-line maintenance utility with comprehensive database and vector validation.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.maintenance import (
    check_database_integrity,
    validate_vector_index,
    cleanup_orphaned_data,
    rebuild_vector_index,
    perform_full_maintenance,
    MaintenanceReport,
    MaintenanceError
)


def format_report(report: MaintenanceReport) -> str:
    """Format a maintenance report for display."""
    lines = []

    lines.append(f"Operation: {report.operation}")
    if report.completed_at and report.started_at:
        duration = report.completed_at - report.started_at
        lines.append(f"Duration: {duration.total_seconds():.2f} seconds")

    # Status summary
    if report.errors:
        lines.append(f"Status: FAILED ({len(report.errors)} errors)")
    elif report.issues_found > 0:
        lines.append(f"Status: ISSUES FOUND ({report.issues_found} issues)")
    else:
        lines.append("Status: SUCCESS")

    # Key metrics
    if report.issues_found > 0:
        lines.append(f"Issues Found: {report.issues_found}")
    if report.issues_resolved > 0:
        lines.append(f"Issues Resolved: {report.issues_resolved}")
    if report.actions_taken:
        lines.append(f"Actions Taken: {len(report.actions_taken)}")

    # Metadata
    if report.metadata:
        lines.append("Details:")
        for key, value in report.metadata.items():
            lines.append(f"  {key}: {value}")

    # Errors
    if report.errors:
        lines.append("Errors:")
        for error in report.errors:
            lines.append(f"  - {error}")

    # Recommendations
    if report.recommendations:
        lines.append("Recommendations:")
        for rec in report.recommendations:
            lines.append(f"  - {rec}")

    # Actions taken (detailed)
    if report.actions_taken and len(report.actions_taken) <= 5:  # Don't flood output
        lines.append("Actions Taken:")
        for action in report.actions_taken:
            lines.append(f"  - {action}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Database and vector maintenance utilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --check-integrity         # Check database integrity
  %(prog)s --validate-vectors        # Validate vector index
  %(prog)s --cleanup-orphans         # Clean up orphaned data
  %(prog)s --rebuild-index           # Rebuild vector index
  %(prog)s --full-maintenance        # Run all maintenance operations
  %(prog)s --full-maintenance --json # Output results as JSON

Maintenance Operations:
  integrity_check    - SQLite database integrity and schema validation
  vector_validation  - Vector index consistency and health checks
  orphaned_cleanup   - Remove orphaned vectors and old tombstones
  index_rebuild      - Rebuild vector index from canonical data

Environment variables:
- MAINTENANCE_ENABLED=true (required)
- DB_PATH=./data/memory.db (database location)
- VECTOR_ENABLED=true (enable vector operations)
        """
    )

    parser.add_argument(
        "--check-integrity", "-i",
        action="store_true",
        help="Check SQLite database integrity and constraints"
    )

    parser.add_argument(
        "--validate-vectors", "-v",
        action="store_true",
        help="Validate vector index health and consistency"
    )

    parser.add_argument(
        "--cleanup-orphans", "-c",
        action="store_true",
        help="Remove orphaned vector entries and clean up old data"
    )

    parser.add_argument(
        "--rebuild-index", "-r",
        action="store_true",
        help="Rebuild vector index from canonical SQLite data"
    )

    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force vector index rebuild even if validation passes"
    )

    parser.add_argument(
        "--full-maintenance", "-f",
        action="store_true",
        help="Perform all maintenance operations in sequence"
    )

    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip automatic backup creation before destructive operations"
    )

    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output results as JSON instead of human-readable text"
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress non-error output"
    )

    args = parser.parse_args()

    # Validate arguments - must specify at least one operation
    operations_specified = (
        args.check_integrity or
        args.validate_vectors or
        args.cleanup_orphans or
        args.rebuild_index or
        args.full_maintenance
    )

    if not operations_specified:
        parser.error("Must specify at least one maintenance operation")

    if args.full_maintenance and any([args.check_integrity, args.validate_vectors, args.cleanup_orphans, args.rebuild_index]):
        parser.error("--full-maintenance cannot be combined with individual operations")

    try:
        reports = []

        # Execute requested operations
        if args.full_maintenance:
            if not args.quiet:
                print("Running full maintenance suite...")
            reports = perform_full_maintenance()

        else:
            # Individual operations
            if args.check_integrity:
                if not args.quiet:
                    print("Checking database integrity...")
                reports.append(check_database_integrity())

            if args.validate_vectors:
                if not args.quiet:
                    print("Validating vector index...")
                reports.append(validate_vector_index())

            if args.cleanup_orphans:
                if not args.quiet:
                    print("Cleaning up orphaned data...")
                reports.append(cleanup_orphaned_data())

            if args.rebuild_index:
                backup_first = not args.no_backup
                if not args.quiet:
                    print("Rebuilding vector index...")
                    if backup_first:
                        print("Creating backup before rebuild...")
                reports.append(rebuild_vector_index(
                    force=args.force_rebuild,
                    backup_first=backup_first
                ))

        # Output results
        if args.json:
            # JSON output
            json_output = {
                "maintenance_run": {
                    "timestamp": str(reports[0].started_at) if reports else None,
                    "operations": len(reports),
                    "total_issues_found": sum(r.issues_found for r in reports),
                    "total_issues_resolved": sum(r.issues_resolved for r in reports),
                    "errors": sum(len(r.errors) for r in reports)
                },
                "reports": [report.to_dict() for report in reports]
            }
            print(json.dumps(json_output, indent=2, default=str))

        else:
            # Human-readable output
            total_issues = sum(r.issues_found for r in reports)
            total_resolved = sum(r.issues_resolved for r in reports)
            total_errors = sum(len(r.errors) for r in reports)

            if not args.quiet:
                print(f"\nMaintenance completed: {len(reports)} operations")
                print(f"Total issues found: {total_issues}")
                print(f"Total issues resolved: {total_resolved}")
                if total_errors > 0:
                    print(f"Total errors: {total_errors}")
                print("-" * 60)

            # Show individual reports
            for i, report in enumerate(reports, 1):
                if not args.quiet or report.errors:
                    if len(reports) > 1:
                        print(f"\nOperation {i}: {report.operation.upper()}")
                        print("-" * 40)
                    print(format_report(report))

            # Overall summary
            if not args.quiet:
                print("\n" + "=" * 60)
                if total_errors > 0:
                    print("MAINTENANCE COMPLETED WITH ERRORS")
                    print("Review error messages above and consider manual intervention.")
                elif total_issues > 0:
                    print("MAINTENANCE COMPLETED WITH ISSUES FOUND")
                    print("Review recommendations above for actions to take.")
                else:
                    print("MAINTENANCE COMPLETED SUCCESSFULLY")
                    print("All systems validated and healthy.")

        # Return appropriate exit code
        if any(r.errors for r in reports):
            return 1  # Errors occurred
        elif any(r.issues_found > 0 for r in reports):
            return 2  # Issues found but no errors
        else:
            return 0  # Success

    except MaintenanceError as e:
        print(f"ERROR: Maintenance operation failed: {e}")
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
