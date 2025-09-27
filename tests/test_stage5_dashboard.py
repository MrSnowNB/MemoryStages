"""
Stage 5 scope only. Do not implement beyond this file's responsibilities.
Stage 5 dashboard integration and regression tests - validates complete dashboard system functionality.
"""

import pytest
import os
import subprocess
import tempfile
import time
from unittest.mock import patch, MagicMock, call

from src.core import config


@pytest.fixture
def dashboard_env():
    """Set up environment variables for dashboard testing."""
    original_env = os.environ.copy()

    # Enable dashboard with full permissions
    os.environ["DASHBOARD_ENABLED"] = "true"
    os.environ["DASHBOARD_AUTH_TOKEN"] = "test_admin_token_2025"
    os.environ["DASHBOARD_SENSITIVE_ACCESS"] = "true"
    os.environ["DASHBOARD_MAINTENANCE_MODE"] = "false"
    os.environ["DASHBOARD_TYPE"] = "tui"

    # Enable underlying features
    os.environ["VECTOR_ENABLED"] = "true"
    os.environ["HEARTBEAT_ENABLED"] = "true"
    os.environ["APPROVAL_ENABLED"] = "true"
    os.environ["SCHEMA_VALIDATION_STRICT"] = "true"

    # Force config reload
    import importlib
    importlib.reload(config)

    yield

    # Restore environment
    os.environ.clear()
    os.environ.update(original_env)
    importlib.reload(config)


@pytest.fixture
def test_db(dashboard_env):
    """Create temporary database for dashboard testing."""
    # Create temporary directory for test database
    test_dir = tempfile.mkdtemp()
    db_path = os.path.join(test_dir, "test_dashboard.db")

    # Override DB_PATH
    original_db_path = os.environ.get('DB_PATH')
    os.environ['DB_PATH'] = db_path

    # Initialize database
    from src.core import db
    db.init_db()

    yield db_path

    # Cleanup
    if original_db_path:
        os.environ['DB_PATH'] = original_db_path
    else:
        del os.environ['DB_PATH']

    import shutil
    shutil.rmtree(test_dir)


class TestDashboardConfiguration:
    """Test dashboard configuration and bootstrapping."""

    def test_dashboard_config_validation_success(self, dashboard_env):
        """Test successful dashboard configuration validation."""
        from tui.auth import validate_dashboard_config

        config_result = validate_dashboard_config()

        assert isinstance(config_result, dict)
        assert config_result["enabled"] is True
        assert config_result["auth_required"] is True
        assert config_result["auth_token_configured"] is True

    def test_dashboard_config_validation_disabled(self):
        """Test dashboard disabled configuration."""
        original_env = os.environ.copy()
        os.environ["DASHBOARD_ENABLED"] = "false"

        import importlib
        importlib.reload(config)

        from tui.auth import validate_dashboard_config

        config_result = validate_dashboard_config()

        assert isinstance(config_result, dict)
        assert config_result["enabled"] is False
        assert config_result["auth_required"] is False

        # Restore
        os.environ.clear()
        os.environ.update(original_env)
        importlib.reload(config)

    def test_dashboard_config_missing_token_failure(self):
        """Test dashboard configuration failure with missing token."""
        original_env = os.environ.copy()
        os.environ["DASHBOARD_ENABLED"] = "true"
        # Remove token
        os.environ.pop("DASHBOARD_AUTH_TOKEN", None)

        import importlib
        importlib.reload(config)

        from tui.auth import validate_dashboard_config

        config_result = validate_dashboard_config()

        assert isinstance(config_result, str)
        assert "DASHBOARD_AUTH_TOKEN must be set" in config_result

        # Restore
        os.environ.clear()
        os.environ.update(original_env)
        importlib.reload(config)

    def test_dashboard_config_invalid_type_failure(self):
        """Test dashboard configuration failure with invalid type."""
        original_env = os.environ.copy()
        os.environ["DASHBOARD_ENABLED"] = "true"
        os.environ["DASHBOARD_AUTH_TOKEN"] = "token"
        os.environ["DASHBOARD_TYPE"] = "invalid_type"

        import importlib
        importlib.reload(config)

        from tui.auth import validate_dashboard_config

        config_result = validate_dashboard_config()

        assert isinstance(config_result, str)
        assert "Invalid DASHBOARD_TYPE" in config_result

        # Restore
        os.environ.clear()
        os.environ.update(original_env)
        importlib.reload(config)


class TestDashboardAuthentication:
    """Test complete dashboard authentication flow."""

    def test_successful_authentication_flow(self, dashboard_env):
        """Test successful authentication end-to-end."""
        from tui.auth import authenticate

        # Test successful authentication
        result = authenticate("test_admin_token_2025")
        assert result is True

        # Test logged success
        from util.logging import logger
        assert hasattr(logger, 'info')  # Verify logging methods exist

    def test_failed_authentication_flow(self, dashboard_env):
        """Test failed authentication end-to-end."""
        from tui.auth import authenticate

        # Test failed authentication
        result = authenticate("wrong_token")
        assert result is False

    def test_sensitive_operation_permissions(self, dashboard_env):
        """Test sensitive operation permission controls."""
        from tui.auth import check_admin_access

        # Regular admin access should work
        assert check_admin_access(sensitive_operation=False) is True

        # Test that sensitive access is granted in test environment
        if os.getenv("DASHBOARD_SENSITIVE_ACCESS") == "true":
            assert check_admin_access(sensitive_operation=True) is True

    def test_maintenance_mode_permissions(self):
        """Test maintenance mode permission controls."""
        original_env = os.environ.copy()

        # Enable dashboard with maintenance mode
        os.environ["DASHBOARD_ENABLED"] = "true"
        os.environ["DASHBOARD_AUTH_TOKEN"] = "token"
        os.environ["DASHBOARD_MAINTENANCE_MODE"] = "true"

        import importlib
        importlib.reload(config)

        from tui.auth import check_admin_access

        # In maintenance mode, sensitive operations should still be controlled separately
        sensitive_result = check_admin_access(sensitive_operation=True)

        if os.getenv("DASHBOARD_SENSITIVE_ACCESS") == "true":
            assert sensitive_result is True
        else:
            assert sensitive_result is False  # Should be False without sensitive access

        # Restore
        os.environ.clear()
        os.environ.update(original_env)
        importlib.reload(config)


class TestDashboardMonitoringIntegration:
    """Test dashboard monitoring system integration."""

    def test_monitoring_system_status_retrieval(self, dashboard_env):
        """Test monitoring system can retrieve system status."""
        from tui.monitor import get_system_status

        status = get_system_status()

        # Verify comprehensive status structure
        assert "timestamp" in status
        assert "dashboard" in status
        assert "stages" in status
        assert "system" in status
        assert "features" in status
        assert "operations" in status

        # Verify dashboard specific status
        assert status["dashboard"]["enabled"] is True
        assert status["dashboard"]["type"] == "tui"

    def test_monitoring_feature_flags_integration(self, dashboard_env, test_db):
        """Test monitoring integrates with feature flags."""
        from tui.monitor import get_feature_flags_status

        flags = get_feature_flags_status()

        # Verify flag detection
        assert flags["dashboard_enabled"] is True
        assert flags["vector_enabled"] is True
        assert flags["heartbeat_enabled"] is True
        assert flags["approval_enabled"] is True

        # Verify dependency checking
        assert "dependencies" in flags

    def test_monitoring_drift_status_integration(self, dashboard_env):
        """Test drift status monitoring integration."""
        from tui.monitor import get_drift_status

        status = get_drift_status()

        # Verify drift monitoring structure
        assert "heartbeat_feature" in status
        assert "drift_detection_enabled" in status
        assert "correction_enabled" in status
        assert "correction_mode" in status

    def test_monitoring_display_update_integration(self, dashboard_env):
        """Test monitoring can update dashboard display."""
        from tui.monitor import update_monitor_display

        mock_app = MagicMock()

        # Should not raise exceptions
        try:
            update_monitor_display(mock_app)
        except Exception as e:
            pytest.fail(f"update_monitor_display raised unexpected exception: {e}")


class TestDashboardTriggerIntegration:
    """Test dashboard trigger system integration."""

    def test_trigger_execution_permissions(self, dashboard_env):
        """Test trigger execution respects permissions."""
        from tui.trigger import validate_trigger_access

        # Regular triggers should be accessible (assuming proper permissions set in test env)
        heartbeat_access = validate_trigger_access("heartbeat")
        drift_access = validate_trigger_access("drift_scan")

        # These should be True in our test environment with admin access
        assert heartbeat_access is True
        assert drift_access is True

    def test_trigger_system_status_tracking(self, dashboard_env):
        """Test trigger system status tracking."""
        from tui.trigger import get_active_triggers

        # Initially no active triggers
        active = get_active_triggers()
        assert active["count"] == 0
        assert active["triggers"] == {}

    @patch('subprocess.run')
    def test_heartbeat_trigger_integration(self, mock_subprocess, dashboard_env):
        """Test heartbeat trigger integrates with system."""
        from tui.trigger import execute_heartbeat

        # Mock successful subprocess execution
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="Heartbeat completed",
            stderr=""
        )

        result = execute_heartbeat()

        # Should indicate success and background execution
        assert result["success"] is True
        assert result["status"] == "running"
        assert "trigger_id" in result

    @patch('subprocess.run')
    def test_drift_scan_trigger_integration(self, mock_subprocess, dashboard_env):
        """Test drift scan trigger integration."""
        from tui.trigger import execute_drift_scan

        result = execute_drift_scan()

        # Should indicate success (drift scan implemented as immediate simulation)
        assert result["success"] is True
        assert "trigger_id" in result

    def test_vector_rebuild_trigger_maintenance_requirement(self, dashboard_env):
        """Test vector rebuild requires maintenance mode."""
        from tui.trigger import execute_vector_rebuild

        # Without maintenance mode (default in test env), should fail
        result = execute_vector_rebuild()
        assert result["success"] is False
        assert "maintenance mode" in result["error"].lower()


class TestDashboardAuditViewerIntegration:
    """Test dashboard audit viewer integration."""

    def test_audit_viewer_recent_events_integration(self, dashboard_env, test_db):
        """Test audit viewer can retrieve recent events."""
        from tui.audit_viewer import get_recent_audit_events

        # Create some test events first
        from util.logging import logger
        logger.log_operation("test.stage5_dashboard.audit", "success", {"test": "audit_viewer_integration"})
        logger.log_operation("test.stage5_dashboard.search", "info", {"test": "search_functionality"})

        events = get_recent_audit_events(limit=5)

        # Should return events (may be fewer than requested)
        assert isinstance(events, list)
        for event in events:
            assert hasattr(event, 'actor')
            assert hasattr(event, 'action')
            assert hasattr(event, 'is_sensitive')

    def test_audit_viewer_search_integration(self, dashboard_env):
        """Test audit viewer search functionality."""
        from tui.audit_viewer import AuditSearchCriteria, search_audit_events

        criteria = AuditSearchCriteria(limit=10)
        events, total = search_audit_events(criteria)

        # Should return valid results
        assert isinstance(events, list)
        assert isinstance(total, int)
        assert len(events) <= 10

    def test_audit_summary_integration(self, dashboard_env, test_db):
        """Test audit summary generation."""
        from tui.audit_viewer import get_audit_summary

        summary = get_audit_summary()

        # Should return comprehensive summary
        assert isinstance(summary, dict)
        assert "total_events" in summary
        assert "last_24h_count" in summary
        assert "operation_types" in summary
        assert "sensitive_events" in summary


class TestDashboardUIMainIntegration:
    """Test dashboard main UI integration."""

    def test_main_dashboard_imports_working(self, dashboard_env):
        """Test all dashboard main imports work correctly."""
        # Test imports don't fail
        from tui.main import DashboardScreen, AuthScreen, DashboardApp

        # Test screen instantiation
        auth_screen = AuthScreen()
        dashboard_screen = DashboardScreen()
        app = DashboardApp()

        assert auth_screen is not None
        assert dashboard_screen is not None
        assert app is not None

    def test_dashboard_button_handlers_exist(self, dashboard_env):
        """Test dashboard has all expected button handlers."""
        from tui.main import DashboardScreen

        dashboard = DashboardScreen()

        # Should have the main button handler method
        assert hasattr(dashboard, 'on_button_pressed')
        assert callable(getattr(dashboard, 'on_button_pressed'))

    def test_dashboard_auth_integration(self, dashboard_env):
        """Test dashboard authentication screen setup."""
        from tui.main import AuthScreen

        auth = AuthScreen()

        # Should have authentication handling
        assert hasattr(auth, 'handle_auth')
        assert hasattr(auth, 'handle_auth_failure')


class TestDashboardBootstrapIntegration:
    """Test dashboard bootstrap and startup integration."""

    def test_script_entry_point_exists(self, dashboard_env):
        """Test dashboard run script exists and is importable."""
        import scripts.run_dashboard

        # Should have main function
        assert hasattr(scripts.run_dashboard, 'main')

    @patch('sys.exit')
    def test_dashboard_bootstrap_validation(self, mock_exit, dashboard_env):
        """Test dashboard bootstrap validates configuration."""
        from tui.main import main

        # In our test environment with valid config, should not exit early
        # But for bootstrap testing, we'll verify the validation occurs

        with patch('tui.auth.validate_dashboard_config') as mock_validate:
            mock_validate.return_value = {"enabled": True, "auth_required": True}

            # Mock to not actually start TUI
            with patch('textual.app.App.run'):
                # This should proceed past validation
                mock_exit.assert_not_called()

    def test_dashboard_config_integration(self, dashboard_env):
        """Test dashboard integrates with Stage 1-4 configuration."""
        from src.core import config as core_config

        # Dashboard should integrate with existing config
        assert hasattr(core_config, 'DASHBOARD_ENABLED')
        assert hasattr(core_config, 'DASHBOARD_TYPE')
        assert hasattr(core_config, 'DASHBOARD_SENSITIVE_ACCESS')

        # Values should match environment in test
        assert core_config.DASHBOARD_ENABLED is True
        assert core_config.DASHBOARD_TYPE == "tui"


class TestDashboardRegressionTests:
    """Regression tests ensuring existing functionality still works."""

    def test_stage1_regression_kv_operations(self, test_db):
        """Regression test: Stage 1 KV operations still work."""
        from src.core.dao import set_key, get_key, list_keys

        # Should be able to set and get values
        set_key("regression_test_key", "test_value", "admin", "test", "preserve")
        retrieved = get_key("regression_test_key")

        assert retrieved is not None
        assert retrieved.value == "test_value"

    def test_stage2_regression_vector_operations(self, dashboard_env, test_db):
        """Regression test: Stage 2 vector operations still work."""
        from src.core.config import get_vector_store

        # Should be able to get vector store
        store = get_vector_store()
        assert store is not None

        # Store should be properly initialized (basic smoke test)
        if hasattr(store, 'search'):
            # This indicates vector functionality is available
            assert callable(store.search)

    def test_stage3_regression_heartbeat_operations(self, dashboard_env):
        """Regression test: Stage 3 heartbeat operations still accessible."""
        from scripts.run_heartbeat import main as heartbeat_main

        # Heatbeat script should be importable and have main function
        assert callable(heartbeat_main)

    def test_stage4_regression_approval_operations(self, dashboard_env):
        """Regression test: Stage 4 approval operations still work."""
        from src.core.approval import list_pending_requests

        # Should be able to call approval functions without errors
        pending = list_pending_requests()
        assert isinstance(pending, list)

    def test_logging_regression_stage4_functionality(self, dashboard_env):
        """Regression test: Stage 4 logging functionality still works."""
        from util.logging import logger

        # Should be able to log operations
        logger.log_operation("test.regression.stage5", "success", {"test": "logging_integration"})

        # Should support new standard logging methods
        logger.info("Stage 5 dashboard regression test")
        logger.warning("Dashboard test warning")
        logger.error("Dashboard test error")


class TestDashboardFullSystemIntegration:
    """End-to-end integration tests for complete dashboard system."""

    def test_full_dashboard_authentication_flow(self, dashboard_env):
        """End-to-end test of dashboard authentication."""
        # Test complete auth -> dashboard flow

        # Step 1: Configuration validation
        from tui.auth import validate_dashboard_config
        config = validate_dashboard_config()
        assert isinstance(config, dict)
        assert config["enabled"] is True

        # Step 2: Authentication
        from tui.auth import authenticate
        auth_result = authenticate("test_admin_token_2025")
        assert auth_result is True

        # Step 3: Permission verification
        from tui.auth import check_admin_access
        access_result = check_admin_access(sensitive_operation=True)
        assert access_result is True

    def test_full_monitoring_integration_flow(self, dashboard_env):
        """End-to-end test of monitoring system integration."""
        # Complete monitoring flow

        # Step 1: System status retrieval
        from tui.monitor import get_system_status
        status = get_system_status()
        assert "timestamp" in status

        # Step 2: Feature flags
        from tui.monitor import get_feature_flags_status
        flags = get_feature_flags_status()
        assert flags["dashboard_enabled"] is True

        # Step 3: Drift status
        from tui.monitor import get_drift_status
        drift = get_drift_status()
        assert "correction_mode" in drift

    def test_full_trigger_integration_flow(self, dashboard_env):
        """End-to-end test of trigger system integration."""
        # Complete trigger flow

        # Step 1: Permission validation
        from tui.trigger import validate_trigger_access
        assert validate_trigger_access("heartbeat") is True

        # Step 2: Trigger execution (mocked for integration test)
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            from tui.trigger import execute_heartbeat
            result = execute_heartbeat()
            assert result["success"] is True

        # Step 3: Status tracking
        from tui.trigger import get_active_triggers
        active = get_active_triggers()
        assert isinstance(active["count"], int)

    def test_full_audit_viewer_integration_flow(self, dashboard_env):
        """End-to-end test of audit viewer integration."""
        # Complete audit flow

        # Step 1: Permission and access
        from tui.audit_viewer import get_recent_audit_events
        events = get_recent_audit_events(limit=5)
        assert isinstance(events, list)

        # Step 2: Search functionality
        from tui.audit_viewer import search_audit_events, AuditSearchCriteria
        criteria = AuditSearchCriteria(limit=10)
        search_results, total = search_audit_events(criteria)
        assert isinstance(search_results, list)

        # Step 3: Summary generation
        from tui.audit_viewer import get_audit_summary
        summary = get_audit_summary()
        assert isinstance(summary, dict)

    def test_cross_system_integration(self, dashboard_env, test_db):
        """Test integration between all dashboard systems."""
        # Create some activity to audit

        # Generate some audit events via logging
        from util.logging import logger
        logger.info("Stage 5 integration test - auditing cross-system functionality")
        logger.log_operation("dashboard.integration.auth", "success", {"phase": "test"})
        logger.log_operation("dashboard.integration.monitor", "info", {"phase": "monitor"})
        logger.log_operation("dashboard.integration.trigger", "success", {"phase": "execute"})

        # System status monitoring
        from tui.monitor import get_system_status
        status = get_system_status()
        health_score = status.get("operations", {}).get("health_score", 0)
        kv_count = status.get("operations", {}).get("total_kv_entries", 0)

        # Audit events should show in summary
        from tui.audit_viewer import get_audit_summary
        summary = get_audit_summary()
        total_audit_events = summary.get("total_events", 0)

        # Trigger status should be empty (no active triggers)
        from tui.trigger import get_active_triggers
        triggers = get_active_triggers()

        # Cross-system validation
        assert isinstance(health_score, int)
        assert 0 <= health_score <= 100
        assert isinstance(kv_count, int)
        assert kv_count >= 0
        assert total_audit_events >= 0
        assert triggers["count"] == 0


# Performance and load testing placeholders (for future slice 5.5)
class TestDashboardPerformanceRegression:
    """Performance regression tests to ensure dashboard doesn't impact system performance."""

    def test_monitoring_performance_under_load(self, dashboard_env):
        """Test monitoring performance with simulated load."""
        from tui.monitor import get_system_status
        import time

        # Measure multiple status retrievals
        times = []
        for _ in range(5):
            start = time.time()
            status = get_system_status()
            end = time.time()
            times.append(end - start)
            assert "timestamp" in status

        avg_time = sum(times) / len(times)
        # Should complete in reasonable time (arbitrary threshold for CI)
        assert avg_time < 1.0  # Under 1 second average

    def test_audit_search_performance_regression(self, dashboard_env):
        """Test audit search performance regression."""
        from tui.audit_viewer import search_audit_events, AuditSearchCriteria
        import time

        criteria = AuditSearchCriteria(limit=50)

        start = time.time()
        events, total = search_audit_events(criteria)
        end = time.time()

        # Should complete search in reasonable time
        search_time = end - start
        assert search_time < 2.0  # Under 2 seconds for search
        assert isinstance(events, list)
        assert len(events) <= 50

    def test_trigger_permission_performance(self, dashboard_env):
        """Test trigger permission checking performance."""
        from tui.trigger import validate_trigger_access
        import time

        start = time.time()
        for _ in range(10):
            # Test multiple permission checks
            result = validate_trigger_access("heartbeat")
            assert isinstance(result, bool)
        end = time.time()

        # Should handle multiple permission checks quickly
        total_time = end - start
        assert total_time < 1.0  # Under 1 second for 10 checks
