"""
Stage 5 scope only. Do not implement beyond this file's responsibilities.
Operations dashboard monitoring tests - validates system monitoring and status tracking.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from src.core import config


@pytest.fixture
def monitoring_env():
    """Set environment variables for enabling monitoring."""
    original_env = os.environ.copy()
    os.environ["DASHBOARD_ENABLED"] = "true"
    os.environ["VECTOR_ENABLED"] = "true"
    os.environ["HEARTBEAT_ENABLED"] = "true"
    os.environ["APPROVAL_ENABLED"] = "true"

    # Force reload config
    import importlib
    importlib.reload(config)

    yield

    # Restore environment
    os.environ.clear()
    os.environ.update(original_env)
    importlib.reload(config)


class TestSystemStatusMonitoring:
    """Test system status monitoring functionality."""

    def test_get_system_status_basic_functionality(self, monitoring_env):
        """Test that system status returns expected structure."""
        from tui.monitor import get_system_status

        status = get_system_status()

        # Verify structure
        assert isinstance(status, dict)
        assert "timestamp" in status
        assert "dashboard" in status
        assert "stages" in status
        assert "system" in status
        assert "features" in status
        assert "operations" in status

        # Verify timestamp is valid ISO format
        datetime.fromisoformat(status["timestamp"])

    def test_get_system_status_stage_tracking(self, monitoring_env):
        """Test that system stages are correctly tracked."""
        from tui.monitor import get_system_status

        status = get_system_status()

        # Stage 1 should always be available
        assert status["stages"]["1_foundation"] is True

        # Other stages should match environment configuration
        assert status["stages"]["2_vector"] == config.VECTOR_ENABLED
        assert status["stages"]["3_heartbeat"] == config.HEARTBEAT_ENABLED
        assert status["stages"]["4_approval"] == config.APPROVAL_ENABLED

    def test_get_system_status_feature_flags(self, monitoring_env):
        """Test that feature flags are correctly represented."""
        from tui.monitor import get_system_status

        status = get_system_status()

        # Verify feature availability matches configuration
        assert status["features"]["vector_search"] == config.VECTOR_ENABLED
        assert status["features"]["heartbeat_monitoring"] == config.HEARTBEAT_ENABLED
        assert status["features"]["approval_workflow"] == config.APPROVAL_ENABLED
        assert status["features"]["schema_validation"] == config.SCHEMA_VALIDATION_STRICT

    @patch('tui.monitor.psutil')
    @patch('tui.monitor.SystemHealthMonitor._check_database_health')
    @patch('src.core.dao.get_kv_count')
    @patch('src.core.approval.list_pending_requests')
    def test_get_system_status_system_monitoring(self, mock_approvals, mock_kv_count, mock_db_health, mock_psutil, monitoring_env):
        """Test system health monitoring with mocked dependencies."""
        # Setup mocks
        mock_psutil.virtual_memory.return_value.percent = 65.5
        mock_psutil.cpu_percent.return_value = 23.4
        mock_db_health.return_value = True
        mock_kv_count.return_value = 42
        mock_approvals.return_value = [{"id": "test_approval"}]

        from tui.monitor import get_system_status
        status = get_system_status()

        # Verify system monitoring
        assert status["system"]["database"] is True
        assert status["system"]["memory_usage"] == 65.5
        # Note: CPU percent is called with interval, may vary

        # Verify operations data
        assert status["operations"]["total_kv_entries"] == 42
        assert status["operations"]["pending_approvals"] == 1

    def test_get_system_status_health_score_calculation(self, monitoring_env):
        """Test health score calculation."""
        from tui.monitor import SystemHealthMonitor

        monitor = SystemHealthMonitor()

        # Mock good system state
        with patch.object(monitor, 'get_system_status') as mock_status:
            mock_status.return_value = {
                "system": {"database": True, "memory_usage": 45.0},
                "features": {
                    "kv_operations": True,
                    "vector_search": True,
                    "schema_validation": True,
                    "sensitive_data_redaction": True
                }
            }

            health_score = monitor._calculate_health_score()
            assert isinstance(health_score, int)
            assert 0 <= health_score <= 100

    def test_get_system_status_caching_behavior(self, monitoring_env):
        """Test that system status uses caching within timeout."""
        from tui.monitor import SystemHealthMonitor

        monitor = SystemHealthMonitor()

        # First call
        status1 = monitor.get_system_status()
        timestamp1 = status1["timestamp"]

        # Immediate second call should return cached data
        status2 = monitor.get_system_status()
        timestamp2 = status2["timestamp"]

        # Timestamps should be identical (cached)
        assert status1["timestamp"] == status2["timestamp"]


class TestFeatureFlagsMonitoring:
    """Test feature flags monitoring."""

    def test_get_feature_flags_status_structure(self, monitoring_env):
        """Test feature flags status structure."""
        from tui.monitor import get_feature_flags_status

        flags = get_feature_flags_status()

        assert isinstance(flags, dict)
        assert "dashboard_enabled" in flags
        assert "vector_enabled" in flags
        assert "heartbeat_enabled" in flags
        assert "approval_enabled" in flags
        assert "schema_validation_strict" in flags

    def test_get_feature_flags_status_dependencies(self, monitoring_env):
        """Test feature flag dependencies are detected."""
        from tui.monitor import get_feature_flags_status

        flags = get_feature_flags_status()

        # Check for dependency information
        assert "dependencies" in flags
        dependencies = flags["dependencies"]

        # Verify dependency warnings when features are misconfigured
        if flags["heartbeat_enabled"] and not flags["vector_enabled"]:
            assert "heartbeat_requires_vector" in dependencies["warnings"]
            dependencies["warnings"].remove("heartbeat_requires_vector")  # Remove for test

        if flags["dashboard_enabled"] and not os.getenv("DASHBOARD_AUTH_TOKEN"):
            assert "dashboard_requires_auth_token" in dependencies["warnings"]


class TestDriftStatusMonitoring:
    """Test drift detection and correction status monitoring."""

    def test_get_drift_status_structure(self, monitoring_env):
        """Test drift status structure."""
        from tui.monitor import get_drift_status

        status = get_drift_status()

        assert isinstance(status, dict)
        assert "heartbeat_feature" in status
        assert "drift_detection_enabled" in status
        assert "correction_enabled" in status
        assert "correction_mode" in status

    def test_get_drift_status_correction_mode(self, monitoring_env):
        """Test correction mode information."""
        from tui.monitor import get_drift_status

        status = get_drift_status()

        correction_mode = status["correction_mode"]
        assert "current" in correction_mode
        assert "description" in correction_mode

        expected_modes = ["off", "propose", "apply"]
        assert correction_mode["current"] in expected_modes
        assert correction_mode["current"] == os.getenv("CORRECTION_MODE", "propose")


class TestSystemHealthMethodologies:
    """Test system health checking methodologies."""

    @patch('src.core.db.get_db')
    def test_database_health_check_success(self, mock_get_db, monitoring_env):
        """Test database health check success."""
        from tui.monitor import SystemHealthMonitor

        # Mock successful database connection
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = "SELECT 1 result"

        monitor = SystemHealthMonitor()
        result = monitor._check_database_health()

        assert result is True
        # Verify SELECT 1 query was executed
        mock_cursor.execute.assert_called_with("SELECT 1")

    @patch('src.core.db.get_db')
    def test_database_health_check_failure(self, mock_get_db, monitoring_env):
        """Test database health check failure."""
        from tui.monitor import SystemHealthMonitor

        # Mock failed database connection
        mock_get_db.side_effect = Exception("Database connection failed")

        monitor = SystemHealthMonitor()
        result = monitor._check_database_health()

        assert result is False

    @patch('src.core.config.get_vector_store')
    @patch('src.core.config.get_embedding_provider')
    def test_vector_system_check_success(self, mock_provider, mock_store, monitoring_env):
        """Test vector system availability check success."""
        from tui.monitor import SystemHealthMonitor

        # Mock successful vector system
        mock_store.return_value = MagicMock()
        mock_provider.return_value = MagicMock()

        monitor = SystemHealthMonitor()
        result = monitor._check_vector_system()

        assert result is True

    @patch('src.core.config.get_vector_store')
    def test_vector_system_check_failure(self, mock_store, monitoring_env):
        """Test vector system availability check failure."""
        from tui.monitor import SystemHealthMonitor

        # Mock failed vector system
        mock_store.return_value = None

        monitor = SystemHealthMonitor()
        result = monitor._check_vector_system()

        assert result is False

    @patch('tui.monitor.psutil')
    def test_memory_usage_monitoring_success(self, mock_psutil, monitoring_env):
        """Test memory usage monitoring."""
        from tui.monitor import SystemHealthMonitor

        mock_psutil.virtual_memory.return_value.percent = 72.5

        monitor = SystemHealthMonitor()
        usage = monitor._get_memory_usage()

        assert usage == 72.5

    @patch('tui.monitor.psutil')
    def test_memory_usage_monitoring_failure(self, mock_psutil, monitoring_env):
        """Test memory usage monitoring with errors."""
        from tui.monitor import SystemHealthMonitor

        mock_psutil.virtual_memory.side_effect = Exception("PSUtil error")

        monitor = SystemHealthMonitor()
        usage = monitor._get_memory_usage()

        # Should return default value on error
        assert usage == 0.0


class TestMonitoringDisplayIntegration:
    """Test monitoring display integration with dashboard."""

    def test_update_monitor_display_success(self, monitoring_env):
        """Test successful monitoring display update."""
        from tui.monitor import update_monitor_display
        from unittest.mock import MagicMock

        mock_app = MagicMock()

        # Should not raise exception
        update_monitor_display(mock_app)

        # Verify the app query was called
        assert mock_app.query_one.called

    def test_update_monitor_display_failure_graceful(self, monitoring_env):
        """Test monitoring display update failure handling."""
        from tui.monitor import update_monitor_display
        from unittest.mock import MagicMock

        mock_app = MagicMock()
        mock_app.query_one.side_effect = Exception("Display update failed")

        # Should handle exception gracefully without raising
        try:
            update_monitor_display(mock_app)
        except Exception:
            pytest.fail("update_monitor_display should handle exceptions gracefully")


class TestCachingBehavior:
    """Test monitoring caching behavior."""

    def test_cache_timeout_behavior(self, monitoring_env):
        """Test that cache expires after timeout."""
        from tui.monitor import SystemHealthMonitor
        import time

        monitor = SystemHealthMonitor()
        monitor._cache_timeout = 0.1  # Short timeout for testing

        # First call
        status1 = monitor.get_system_status()

        # Wait longer than cache timeout
        time.sleep(0.2)

        # Second call should fetch fresh data
        status2 = monitor.get_system_status()

        # Timestamps should be different (cache expired)
        assert status1["timestamp"] != status2["timestamp"]

    def test_cache_invalid_after_manual_refresh(self, monitoring_env):
        """Test cache invalidation after manual refresh."""
        from tui.monitor import get_system_status

        # Call twice quickly - should be cached
        status1 = get_system_status()
        status2 = get_system_status()

        assert status1["timestamp"] == status2["timestamp"]

        # Force cache invalidation by clearing global monitor
        import tui.monitor
        tui.monitor.system_monitor._last_refresh = None

        # Next call should be fresh
        status3 = get_system_status()
        assert status1["timestamp"] != status3["timestamp"]


class TestMonitoringConfigurationIntegration:
    """Test integration with configuration system."""

    def test_monitoring_adapts_to_config_changes(self):
        """Test that monitoring adapts to configuration changes."""
        original_env = os.environ.copy()

        # Configure minimal monitoring
        os.environ["DASHBOARD_ENABLED"] = "true"
        os.environ["VECTOR_ENABLED"] = "false"
        os.environ["HEARTBEAT_ENABLED"] = "false"
        os.environ["APPROVAL_ENABLED"] = "false"

        import importlib
        importlib.reload(config)

        from tui.monitor import get_system_status

        status = get_system_status()
        assert status["stages"]["2_vector"] is False
        assert status["stages"]["3_heartbeat"] is False
        assert status["stages"]["4_approval"] is False

        # Restore environment
        os.environ.clear()
        os.environ.update(original_env)
        importlib.reload(config)
