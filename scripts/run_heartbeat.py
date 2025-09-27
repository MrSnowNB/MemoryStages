#!/usr/bin/env python3
"""
Stage 3 scope only. Do not implement beyond this file's responsibilities.
Heartbeat and drift correction - maintains vector overlay consistency with canonical SQLite.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.heartbeat import register_task, start, stop, get_status
from core.config import get_heartbeat_interval, are_heartbeat_features_enabled


def drift_audit_task():
    """
    Main heartbeat task: audit vector overlay vs SQLite KV for drift.

    This task will be implemented to:
    1. Query SQLite KV for current non-sensitive, non-tombstoned entries
    2. Compare with vector index contents
    3. Detect missing, stale, or orphaned vectors
    4. Generate correction plans based on CORRECTION_MODE
    5. Apply corrections if configured
    6. Log all operations to episodic events
    """
    from core.drift_rules import detect_drift
    from core.corrections import apply_corrections
    from core.config import get_correction_mode

    print("🔍 Running drift audit...")

    # Detect drift between SQLite and vector store
    findings = detect_drift()

    if not findings:
        print("✅ No drift detected")
        return

    print(f"⚠️  Found {len(findings)} drift issues")

    # Generate correction plans
    correction_plans = []
    for finding in findings:
        # For now, create basic correction plan
        # Full implementation in corrections.py and drift_rules.py
        correction_plans.append(finding)

    # Apply corrections based on mode
    correction_mode = get_correction_mode()

    if correction_mode == "off":
        print("📊 Correction mode=off, logging only")
    elif correction_mode == "propose":
        print("📝 Correction mode=propose, generating plans")
        # Log proposed corrections to episodic
    elif correction_mode == "apply":
        print("🔧 Correction mode=apply, executing corrections")
        apply_corrections(correction_plans)

    print("✓ Drift audit completed")


def main():
    """Main entry point for heartbeat script."""
    try:
        if not are_heartbeat_features_enabled():
            print("❌ Heartbeat requires VECTOR_ENABLED=true and HEARTBEAT_ENABLED=true")
            print("See STAGE3_LOCKDOWN.md for configuration details")
            sys.exit(1)

        # Register the main drift audit task
        interval = get_heartbeat_interval()
        register_task("drift_audit", interval, drift_audit_task)

        print(f"🏃 Configuring drift audit task (every {interval} seconds)")

        # Start the heartbeat loop
        start()

    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
        stop()
    except Exception as e:
        print(f"💥 Critical error: {e}")
        stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
