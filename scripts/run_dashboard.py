#!/usr/bin/env python3
"""
Stage 5 scope only. Do not implement beyond this file's responsibilities.
Dashboard entrypoint - secure administrative interface for monitoring and maintenance.
"""

import sys
import os
from pathlib import Path

# Load environment variables from .env file first
import dotenv
dotenv.load_dotenv()

# Add project root to path for imports (src/ and tui/ are both in project root)
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    """Dashboard entrypoint - validates configuration and launches appropriate dashboard."""
    try:
        # Check if dashboard is enabled
        dashboard_enabled = os.getenv("DASHBOARD_ENABLED", "false").lower() == "true"
        if not dashboard_enabled:
            print("ℹ️  Operations dashboard is disabled.")
            print("   Set DASHBOARD_ENABLED=true and DASHBOARD_AUTH_TOKEN to enable.")
            return 0

        # Check dashboard type
        dashboard_type = os.getenv("DASHBOARD_TYPE", "tui")

        if dashboard_type == "tui":
            # Launch TUI dashboard
            try:
                from tui.main import main as tui_main
                tui_main()
            except ImportError as e:
                print(f"❌ Failed to import TUI dashboard: {e}")
                print("   Make sure textual is installed: pip install textual")
                return 1
        elif dashboard_type == "web":
            # Launch web dashboard (placeholder for future implementation)
            print("❌ Web dashboard not yet implemented. Use DASHBOARD_TYPE=tui")
            return 1
        else:
            print(f"❌ Invalid DASHBOARD_TYPE: {dashboard_type}. Must be 'tui' or 'web'")
            return 1

    except KeyboardInterrupt:
        print("\nℹ️  Dashboard interrupted")
        return 0
    except Exception as e:
        print(f"❌ Dashboard startup failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
