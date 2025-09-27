"""
Stage 3 scope only. Do not implement beyond this file's responsibilities.
Heartbeat and drift correction - maintains vector overlay consistency with canonical SQLite.
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from src.core.heartbeat import register_task, unregister_task, list_tasks, start, stop, should_run_task, run_task, get_status


@pytest.fixture(autouse=True)
def reset_heartbeat():
    """Reset heartbeat state between tests."""
    from src.core import heartbeat
    heartbeat.tasks.clear()
    heartbeat.running = False
    heartbeat.shutdown_event = None


class TestHeartbeatRegistration:
    """Test task registration functionality."""

    def test_register_task_valid(self):
        """Test registering a valid task."""
        def dummy_func():
            pass

        register_task("test_task", 30, dummy_func)

        assert "test_task" in list_tasks()
        tasks = list_tasks()
        assert len(tasks) == 1
        assert tasks[0] == "test_task"

    def test_register_task_invalid_func(self):
        """Test registering with non-callable function."""
        with pytest.raises(ValueError, match="Task function must be callable"):
            register_task("bad_task", 30, "not_callable")

    def test_register_task_invalid_interval(self):
        """Test registering with invalid interval."""
        with pytest.raises(ValueError, match="Interval must be >= 1 second"):
            register_task("bad_task", 0, lambda: None)

    def test_register_duplicate_task(self):
        """Test registering task with existing name replaces it."""
        register_task("duplicate", 30, lambda: None)
        register_task("duplicate", 60, lambda: None)  # Should replace

        assert len(list_tasks()) == 1

    def test_unregister_task(self):
        """Test unregistering a task."""
        register_task("test_task", 30, lambda: None)
        assert "test_task" in list_tasks()

        unregister_task("test_task")
        assert "test_task" not in list_tasks()

    def test_unregister_nonexistent_task(self):
        """Test unregistering non-existent task is safe."""
        unregister_task("nonexistent")  # Should not raise

    @patch('src.core.heartbeat.is_heartbeat_enabled', return_value=False)
    def test_register_task_disabled_heartbeat(self, mock_enabled):
        """Test task registration when heartbeat is globally disabled."""
        # Should still allow registration even if globally disabled
        register_task("disabled_test", 30, lambda: None)
        assert "disabled_test" in list_tasks()


class TestHeartbeatScheduling:
    """Test task scheduling logic."""

    def test_should_run_first_time(self):
        """Task should run immediately when never run before."""
        task_info = {"last_run": None, "interval": 30}
        assert should_run_task("test", task_info) == True

    def test_should_run_when_due(self):
        """Task should run when interval has elapsed."""
        past_time = time.monotonic() - 35  # More than 30 seconds ago
        task_info = {"last_run": past_time, "interval": 30}
        assert should_run_task("test", task_info) == True

    def test_should_not_run_too_soon(self):
        """Task should not run before interval elapsed."""
        recent_time = time.monotonic() - 10  # Only 10 seconds ago
        task_info = {"last_run": recent_time, "interval": 30}
        assert should_run_task("test", task_info) == False


class TestHeartbeatExecution:
    """Test task execution and heartbeat loop."""

    @patch('src.core.heartbeat.is_heartbeat_enabled', return_value=False)
    def test_start_disabled_heartbeat(self, mock_enabled, capsys):
        """Test that heartbeat start is skipped when disabled."""
        start()
        captured = capsys.readouterr()
        assert "Heartbeat disabled" in captured.out

    @patch('src.core.heartbeat.is_heartbeat_enabled', return_value=True)
    @patch('src.core.heartbeat.validate_heartbeat_config', return_value=[])
    def test_start_registers_tasks(self, mock_enabled, mock_validate, capsys):
        """Test heartbeat start operation."""
        register_task("test", 30, lambda: None)
        start()  # Should start briefly then exit since no proper loop
        captured = capsys.readouterr()
        assert "Starting heartbeat loop" in captured.out

    @patch('src.core.heartbeat.running', True)
    def test_start_already_running(self):
        """Test starting when already running raises error."""
        with patch('src.core.heartbeat.is_heartbeat_enabled', return_value=True), \
             patch('src.core.heartbeat.validate_heartbeat_config', return_value=[]), \
             pytest.raises(RuntimeError, match="already running"):
            start()

    @patch('src.core.heartbeat.running', True)
    @patch('src.core.heartbeat.is_heartbeat_enabled', return_value=True)
    def test_stop_running_heartbeat(self, mock_enabled):
        """Test stopping a running heartbeat."""
        stop()
        # Should not raise exceptions

    @patch('src.core.heartbeat.running', False)
    def test_stop_not_running_heartbeat(self, capsys):
        """Test stopping heartbeat that isn't running."""
        stop()
        captured = capsys.readouterr()
        assert "Heartbeat not running" in captured.out

    @patch('src.core.heartbeat.is_heartbeat_enabled', return_value=True)
    def test_run_task_success(self, mock_enabled):
        """Test successful task execution."""
        mock_func = MagicMock()
        task_info = {"func": mock_func, "interval": 30, "last_run": None}

        run_task("test_task", task_info)

        mock_func.assert_called_once()
        # Should update last_run
        assert task_info["last_run"] is not None

    @patch('src.core.heartbeat.is_heartbeat_enabled', return_value=True)
    def test_run_task_failure(self, mock_enabled):
        """Test task execution with failure."""
        mock_func = MagicMock(side_effect=ValueError("Task failed"))
        task_info = {"func": mock_func, "interval": 30, "last_run": None}

        with pytest.raises(RuntimeError, match="Task failed"):
            run_task("failing_task", task_info)

        mock_func.assert_called_once()


class TestHeartbeatStatus:
    """Test heartbeat status and monitoring."""

    def test_get_status_disabled(self):
        """Test status when heartbeat is disabled."""
        with patch('src.core.heartbeat.is_heartbeat_enabled', return_value=False):
            status = get_status()
            assert status["status"] == "disabled"
            assert "HEARTBEAT_ENABLED=false" in status["reason"]

    def test_get_status_stopped(self):
        """Test status when heartbeat is enabled but stopped."""
        with patch('src.core.heartbeat.is_heartbeat_enabled', return_value=True), \
             patch('src.core.heartbeat.running', False):
            status = get_status()
            assert status["status"] == "stopped"
            assert "tasks" in status

    def test_get_status_running(self):
        """Test status when heartbeat is running."""
        with patch('src.core.heartbeat.is_heartbeat_enabled', return_value=True), \
             patch('src.core.heartbeat.running', True):
            register_task("test_task", 60, lambda: None)
            status = get_status()
            assert status["status"] == "running"
            assert "test_task" in status["tasks"]
            assert status["tasks"]["test_task"]["interval_sec"] == 60


class TestHeartbeatConfiguration:
    """Test heartbeat configuration validation."""

    @patch('src.core.heartbeat.validate_heartbeat_config', return_value=["Invalid setting"])
    def test_register_with_invalid_config(self, mock_validate):
        """Test task registration fails with invalid config."""
        with pytest.raises(ValueError, match="Heartbeat configuration invalid"):
            register_task("bad_config", 30, lambda: None)
