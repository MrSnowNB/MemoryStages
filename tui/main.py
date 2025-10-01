"""
Stage 5 scope only. Do not implement beyond this file's responsibilities.
Operations dashboard - secure administrative interface for monitoring and maintenance.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer, Static, Button, Label, Input
from textual.screen import Screen

from util.logging import logger
from .auth import authenticate, validate_dashboard_config, log_auth_event
from .monitor import update_monitor_display
from .trigger import (
    execute_heartbeat,
    execute_drift_scan,
    execute_vector_rebuild,
    get_active_triggers,
    get_trigger_status
)
from .audit_viewer import (
    get_recent_audit_events,
    get_audit_summary,
    AuditSearchCriteria
)

class AuthScreen(Screen):
    """Authentication screen for dashboard access."""

    def compose(self) -> ComposeResult:
        yield Container(
            Static("🔐 MemoryStages Operations Dashboard", classes="title"),
            Static("Please authenticate to continue", classes="subtitle"),
            Label("Auth Token:", classes="label"),
            Input(id="auth-token", placeholder="Enter admin token..."),
            Button("Authenticate", id="auth-button", variant="primary"),
            Static("ESC to cancel", classes="hint"),
            id="auth-container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "auth-button":
            self.handle_auth()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "auth-token":
            self.handle_auth()

    def handle_auth(self) -> None:
        token_input = self.get_widget_by_id("auth-token").value

        if authenticate(token_input):
            log_auth_event(True, "dashboard login")
            # Valid authentication - proceed to main dashboard
            self.app.pop_screen()
            self.app.push_screen("dashboard")
        else:
            log_auth_event(False, "dashboard login attempt")
            # Invalid authentication - show error and stay on screen
            self.handle_auth_failure()

    def handle_auth_failure(self) -> None:
        """Handle authentication failure."""
        # Update auth button text and style
        button = self.get_widget_by_id("auth-button")
        button.label = "❌ Invalid Token - Try Again"
        button.variant = "error"

        # Clear the token input
        token_input = self.get_widget_by_id("auth-token")
        token_input.value = ""

class DashboardScreen(Screen):
    """Main dashboard screen after authentication."""

    def compose(self) -> ComposeResult:
        # Update monitoring display when screen is shown
        self._update_monitoring_display()
        yield Container(
            Static("📊 MemoryStages Operations Dashboard", classes="title"),
            Static("Administrative controls and monitoring", classes="subtitle"),
            Container(
                Static("System Health", classes="section-title"),
                Static("● Database: Ready\n● Vector Store: Ready\n● Features: Enabled", classes="system-health"),
                id="health-section"
            ),
            Container(
                Static("Manual Triggers", classes="section-title"),
                Button("Run Heartbeat", id="heartbeat-trigger", variant="success"),
                Button("Scan for Drift", id="drift-trigger", variant="warning"),
                Button("View Pending Approvals", id="approvals-trigger", variant="primary"),
                id="triggers-section"
            ),
            Container(
                Static("Log Viewer", classes="section-title"),
                Button("View Recent Events", id="events-view", variant="primary"),
                Button("Search Events", id="events-search", variant="secondary"),
                id="logs-section"
            ),
            Static("Press ESC to exit, Q to quit", classes="footer-hint"),
            id="dashboard-container",
        )

    def _update_monitoring_display(self) -> None:
        """Update the monitoring display with current system status."""
        try:
            update_monitor_display(self.app)
        except Exception as e:
            logger.error(f"Failed to update monitoring display: {e}")
            # Continue without monitoring update - dashboard still functional
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id == "heartbeat-trigger":
            self.run_heartbeat()
        elif button_id == "drift-trigger":
            self.run_drift_scan()
        elif button_id == "approvals-trigger":
            self.show_approvals()
        elif button_id == "events-view":
            self.show_recent_events()
        elif button_id == "events-search":
            self.search_events()

    def run_heartbeat(self) -> None:
        """Trigger manual heartbeat execution."""
        result = execute_heartbeat()
        if result["success"]:
            self.notify(f"🔄 {result['message']}", title="Heartbeat Triggered", severity="information")
            self._schedule_status_check(result["trigger_id"], "heartbeat")
        else:
            self.notify(f"❌ {result['error']}", title="Heartbeat Failed", severity="error")

    def run_drift_scan(self) -> None:
        """Trigger manual drift detection scan."""
        result = execute_drift_scan()
        if result["success"]:
            self.notify(f"🔍 {result['message']}", title="Drift Scan Triggered", severity="information")
            self._schedule_status_check(result["trigger_id"], "drift")
        else:
            self.notify(f"❌ {result['error']}", title="Drift Scan Failed", severity="error")

    def _schedule_status_check(self, trigger_id: str, trigger_type: str) -> None:
        """Schedule automatic status checking for background triggers."""
        # This is a placeholder - in a full implementation, we'd use Textual's timer
        # For now, status will be checked when user interacts with dashboard
        pass

    def show_approvals(self) -> None:
        """Show pending approvals."""
        from src.core.approval import list_pending_requests
        pending = list_pending_requests()
        if pending:
            count = len(pending)
            self.notify(f"📋 {count} pending approval(s)", title="Pending Approvals", severity="information")
            # TODO: Show approval interface
        else:
            self.notify("✅ No pending approvals", title="Approvals", severity="success")

    def show_recent_events(self) -> None:
        """Show recent audit events."""
        try:
            recent_events = get_recent_audit_events(limit=10)

            if not recent_events:
                self.notify("📜 No recent audit events found", title="Event Viewer", severity="information")
                return

            # Format events for display
            events_display = []
            for event in recent_events:
                timestamp = event.ts.strftime("%H:%M:%S")
                sensitive_indicator = "🔐" if event.is_sensitive else "📄"
                events_display.append(f"{timestamp} {sensitive_indicator} {event.actor} - {event.action}")

            events_text = "\n".join(events_display[:5])  # Limit to 5 for display
            if len(recent_events) > 5:
                events_text += f"\n... and {len(recent_events) - 5} more"

            # Update the health section with recent events (temporary - in real TUI, this would be a popup/modal)
            current_health = self.get_widget_by_id("health-section").query_one("Static.system-health")
            current_health.update(f"Recent Audit Events:\n{events_text}")

            self.notify(f"📜 Showing {len(recent_events)} recent events", title="Event Viewer", severity="information")
            logger.info(f"Dashboard access: viewing {len(recent_events)} recent audit events")

        except Exception as e:
            self.notify(f"❌ Failed to load audit events: {str(e)}", title="Audit Error", severity="error")
            logger.error(f"Dashboard audit events display failed: {e}")

    def search_events(self) -> None:
        """Show event search interface."""
        self.notify("🔎 Event search interface", title="Search", severity="information")
        # TODO: Implement event search interface
        logger.info("Dashboard access: event search initiated")

class DashboardApp(App):
    """MemoryStages Operations Dashboard TUI Application."""

    CSS = """
    .title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: blue;
    }

    .subtitle {
        text-align: center;
        margin-bottom: 2;
        color: gray;
    }

    .section-title {
        text-style: bold;
        margin-bottom: 1;
        color: cyan;
    }

    .label {
        margin-bottom: 1;
    }

    .system-health {
        background: darkblue;
        border: solid cyan;
        padding: 1;
        margin-bottom: 1;
    }

    #health-section, #triggers-section, #logs-section {
        width: 100%;
        margin-bottom: 2;
        padding: 1;
        border: solid white;
    }

    .footer-hint {
        text-align: center;
        margin-top: 2;
        color: gray;
    }

    .hint {
        text-align: center;
        margin-top: 1;
        color: gray;
        text-style: italic;
    }

    #auth-container {
        width: 60;
        height: 20;
        align: center middle;
    }
    """

    TITLE = "MemoryStages Operations Dashboard"

    SCREENS = {
        "auth": AuthScreen(),
        "dashboard": DashboardScreen(),
    }

    def on_mount(self) -> None:
        """Initialize dashboard on startup."""
        logger.info("MemoryStages Operations Dashboard started")

        # Validate configuration
        config_validation = validate_dashboard_config()
        if isinstance(config_validation, str):
            self.exit(message=config_validation)

        if config_validation["enabled"]:
            if config_validation["auth_required"]:
                # Show authentication screen
                self.push_screen("auth")
            else:
                # No auth required, go directly to dashboard
                self.push_screen("dashboard")
        else:
            self.exit(message="Dashboard feature is disabled. Set DASHBOARD_ENABLED=true to enable.")

    def on_key(self, event) -> None:
        """Handle global key events."""
        if event.key == "q":
            logger.info("Dashboard exit requested by user")
            self.exit(message="Dashboard exited by user request")
        elif event.key.name == "escape":
            # Handle escape differently based on current screen
            current_screen = self.screen
            if isinstance(current_screen, AuthScreen):
                self.exit(message="Dashboard authentication cancelled")
            elif isinstance(current_screen, DashboardScreen):
                self.push_screen("auth")

def main():
    """Main dashboard entry point."""
    try:
        # Validate dashboard is enabled before starting
        config_validation = validate_dashboard_config()
        if isinstance(config_validation, str):
            print(f"❌ Dashboard configuration error: {config_validation}")
            sys.exit(1)

        if config_validation["enabled"]:
            print("🚀 Starting MemoryStages Operations Dashboard...")
            app = DashboardApp()
            app.run()
        else:
            print("ℹ️  Dashboard is disabled. Set DASHBOARD_ENABLED=true and DASHBOARD_AUTH_TOKEN to enable.")
            sys.exit(0)

    except KeyboardInterrupt:
        print("\nℹ️  Dashboard interrupted by user")
        logger.info("Dashboard exited via keyboard interrupt")
    except Exception as e:
        error_msg = f"Dashboard startup failed: {e}"
        print(f"❌ {error_msg}")
        logger.error(error_msg)
        sys.exit(1)

if __name__ == "__main__":
    main()
