"""
Stage 3 scope only. Do not implement beyond this file's responsibilities.
Heartbeat and drift correction - maintains vector overlay consistency with canonical SQLite.
"""

import time
import threading
from typing import Callable, Dict
from datetime import datetime

from .config import is_heartbeat_enabled, validate_heartbeat_config


tasks: Dict[str, Dict] = {}  # task_name -> {func, interval, last_run}
running = False
shutdown_event = None


def register_task(name: str, interval_sec: int, func: Callable):
    """
    Register a task to be executed periodically.

    Args:
        name: Unique task identifier
        interval_sec: How often to run this task in seconds
        func: Function to call (should be fast and not block)
    """
    if not callable(func):
        raise ValueError(f"Task function must be callable: {func}")

    if interval_sec < 1:
        raise ValueError(f"Interval must be >= 1 second: {interval_sec}")

    # Validate heartbeat config at registration time
    issues = validate_heartbeat_config()
    if issues:
        raise ValueError(f"Heartbeat configuration invalid: {issues}")

    tasks[name] = {
        "func": func,
        "interval": interval_sec,
        "last_run": None
    }

    print(f"✓ Registered heartbeat task '{name}' (every {interval_sec}s)")


def unregister_task(name: str):
    """Remove a task from the registry."""
    if name in tasks:
        del tasks[name]
        print(f"✓ Unregistered heartbeat task '{name}'")


def list_tasks():
    """Return list of registered task names."""
    return list(tasks.keys())


def start():
    """
    Start the heartbeat loop.

    This runs a cooperative scheduling loop that checks task intervals
    and executes tasks when due. Uses time.monotonic() for reliable timing.
    """
    global running, shutdown_event

    if not is_heartbeat_enabled():
        print ("Heartbeat disabled (HEARTBEAT_ENABLED=false). Skipping start.")
        return

    if running:
        raise RuntimeError("Heartbeat already running")

    # Validate configuration
    issues = validate_heartbeat_config()
    if issues:
        raise ValueError(f"Heartbeat configuration invalid: {issues}")

    running = True
    shutdown_event = threading.Event()

    print("🚀 Starting heartbeat loop")
    print(f"📋 Registered tasks: {list(tasks.keys())}")
    print("💡 Press Ctrl+C to stop")

    try:
        while running and not shutdown_event.is_set():
            start_time = time.monotonic()

            # Check each task
            for name, task_info in tasks.items():
                if should_run_task(name, task_info):
                    try:
                        run_task(name, task_info)
                    except Exception as e:
                        # Error isolation - log error but continue loop
                        print(f"❌ Heartbeat task '{name}' failed: {e}")

            # Sleep a bit to prevent tight loop (cooperative scheduling)
            time.sleep(0.1)

            # Exit if loop took too long (prevents runaway)
            elapsed = time.monotonic() - start_time
            if elapsed > 10.0:  # 10s max per cycle
                print(f"⚠️  Heartbeat cycle too slow ({elapsed:.1f}s). Exiting for safety.")
                break

    except KeyboardInterrupt:
        print("\n🛑 Heartbeat interrupted by user")
    finally:
        running = False
        print("🏁 Heartbeat loop stopped")


def stop():
    """Stop the heartbeat loop gracefully."""
    global running

    if not running:
        print("Heartbeat not running")
        return

    print("🛑 Stopping heartbeat loop...")
    running = False

    if shutdown_event:
        shutdown_event.set()

    # Wait a brief moment for clean shutdown
    time.sleep(0.2)

    print("✓ Heartbeat stopped")


def should_run_task(name: str, task_info: Dict) -> bool:
    """Check if a task should run this cycle."""
    if task_info["last_run"] is None:
        return True  # Run immediately if never run

    elapsed = time.monotonic() - task_info["last_run"]
    return elapsed >= task_info["interval"]


def run_task(name: str, task_info: Dict):
    """Execute a task and record timing."""
    start_time = time.monotonic()

    try:
        task_info["func"]()
        end_time = time.monotonic()
        duration = end_time - start_time

        # Update last run time
        task_info["last_run"] = end_time

        print(".2f")
    except Exception as e:
        end_time = time.monotonic()
        duration = end_time - start_time
        raise RuntimeError(f"Task '{name}' failed after {duration:.2f}s: {e}")


def reset_task(name: str):
    """Reset a task's last_run time to force immediate execution."""
    if name in tasks:
        tasks[name]["last_run"] = None
        print(f"✓ Reset heartbeat task '{name}' (will run immediately)")


def get_status():
    """Return current heartbeat status for monitoring."""
    if not is_heartbeat_enabled():
        return {"status": "disabled", "reason": "HEARTBEAT_ENABLED=false"}

    return {
        "status": "running" if running else "stopped",
        "tasks": {
            name: {
                "interval_sec": info["interval"],
                "last_run": info["last_run"],
                "next_run": info["last_run"] + info["interval"] if info["last_run"] else None
            }
            for name, info in tasks.items()
        },
        "uptime_sec": time.monotonic() - (min(info["last_run"] for info in tasks.values() if info["last_run"]) if any(info["last_run"] for info in tasks.values()) else time.monotonic())
    }
