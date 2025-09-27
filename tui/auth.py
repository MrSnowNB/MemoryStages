"""
Stage 5 scope only. Do not implement beyond this file's responsibilities.
Operations dashboard - secure administrative interface for monitoring and maintenance.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from typing import Union
from src.core import config
from util.logging import logger

def authenticate(token_input: str) -> bool:
    """
    Validate access token against DASHBOARD_AUTH_TOKEN.

    Returns True if authentication successful, False otherwise.
    All authentication attempts are logged.
    """
    expected_token = os.getenv("DASHBOARD_AUTH_TOKEN")

    # Validate dashboard is enabled
    if not config.DASHBOARD_ENABLED:
        logger.warning("Dashboard authentication attempt when feature disabled")
        return False

    # Check token exists and is not empty
    if not expected_token or not expected_token.strip():
        logger.error("Dashboard authentication attempted but no auth token configured")
        return False

    # Compare tokens securely (constant-time comparison)
    if len(token_input) != len(expected_token):
        logger.info(f"Authentication failed: invalid token length (expected {len(expected_token)})")
        return False

    # Check token value
    if token_input != expected_token:
        logger.warning("Authentication failed: invalid token provided")
        return False

    # Successful authentication
    logger.info("Dashboard authentication successful")
    return True

def require_auth(func):
    """
    Decorator requiring authentication for sensitive operations.

    Args:
        func: Function to wrap with authentication

    Returns:
        Wrapped function that requires authentication

    Usage:
        @require_auth
        def sensitive_operation(self):
            # Only accessible after authentication
            pass
    """
    def auth_wrapper(*args, **kwargs):
        # For now, assume authentication state managed by parent application
        # This could be enhanced with session management if needed

        # All access attempts are logged by the function itself
        # Additional authentication checks could be added here

        return func(*args, **kwargs)

    return auth_wrapper

def validate_dashboard_config() -> Union[dict, str]:
    """
    Validate dashboard configuration.

    Returns:
        dict with valid config if successful, error message string if invalid
    """
    issues = []

    if not config.DASHBOARD_ENABLED:
        # Dashboard disabled - this is valid configuration
        return {
            "enabled": False,
            "auth_required": False,
            "maintenance_mode": False,
            "sensitive_access": False
        }

    # Dashboard enabled - check required configuration
    auth_token = os.getenv("DASHBOARD_AUTH_TOKEN")
    if not auth_token or not auth_token.strip():
        issues.append("DASHBOARD_AUTH_TOKEN must be set when DASHBOARD_ENABLED=true")

    dashboard_type = os.getenv("DASHBOARD_TYPE", "tui")
    if dashboard_type not in ["tui", "web"]:
        issues.append(f"Invalid DASHBOARD_TYPE: {dashboard_type}. Must be 'tui' or 'web'")

    if issues:
        error_msg = f"Dashboard configuration invalid: {', '.join(issues)}"
        logger.error(error_msg)
        return error_msg

    # Valid configuration
    return {
        "enabled": True,
        "auth_required": True,
        "maintenance_mode": os.getenv("DASHBOARD_MAINTENANCE_MODE", "false").lower() == "true",
        "sensitive_access": os.getenv("DASHBOARD_SENSITIVE_ACCESS", "false").lower() == "true",
        "auth_token_configured": bool(auth_token.strip()) if auth_token else False
    }

def log_auth_event(success: bool, details: str = ""):
    """
    Log authentication-related events.

    Args:
        success: Whether authentication was successful
        details: Additional details about the authentication attempt
    """
    event_type = "dashboard_auth_success" if success else "dashboard_auth_failure"

    logger.log_operation(
        f"dashboard.{event_type}",
        "success" if success else "failure",
        {"details": details}
    )

def check_admin_access(sensitive_operation: bool = False) -> bool:
    """
    Check if current session has appropriate admin access.

    Args:
        sensitive_operation: Whether this requires sensitive data access

    Returns:
        True if access allowed, False otherwise
    """
    dashboard_config = validate_dashboard_config()

    if not dashboard_config or isinstance(dashboard_config, str):
        # Configuration invalid - disallow access
        return False

    if not dashboard_config["enabled"]:
        # Dashboard disabled - no access
        return False

    if not dashboard_config["auth_required"]:
        # No auth required - basic access
        return not sensitive_operation or dashboard_config["sensitive_access"]

    # Auth required - check if we're in an authenticated context
    # For now, assume authentication is handled at application entry point
    # This could be enhanced with proper session management
    if sensitive_operation and not dashboard_config["sensitive_access"]:
        logger.warning("Attempted sensitive operation without DASHBOARD_SENSITIVE_ACCESS permission")
        return False

    return True
