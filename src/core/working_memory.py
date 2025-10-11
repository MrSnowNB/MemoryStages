"""
Stage 3: Bot Swarm Orchestration - Working Memory Scratchpad
Request-scoped temporary storage for agent intermediate results.

The WorkingMemory provides a clean, isolated storage space for each request
that allows agents to share intermediate results during swarm orchestration.
Automatically flushed after response completion.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import threading


class WorkingMemory:
    """
    Request-scoped working memory for agent intermediate results.

    Features:
    - Thread-safe storage per request
    - Automatic cleanup after request completion
    - Structured access with defaults
    - Debug and audit capabilities
    """

    def __init__(self):
        """Initialize working memory with thread-local storage."""
        self._local = threading.local()
        self._stats = {
            "requests_processed": 0,
            "memory_operations": 0,
            "peak_memory_usage": 0
        }

    def clear(self):
        """Clear all data for the current request."""
        self._local.data = {}
        self._local.created_at = datetime.now()
        self._local.request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

    def set(self, key: str, value: Any):
        """Set a value in working memory."""
        if not hasattr(self._local, 'data'):
            self.clear()

        self._local.data[key] = {
            "value": value,
            "set_at": datetime.now(),
            "access_count": 0
        }
        self._stats["memory_operations"] += 1

        # Update peak usage tracking
        current_usage = len(self._local.data)
        if current_usage > self._stats["peak_memory_usage"]:
            self._stats["peak_memory_usage"] = current_usage

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from working memory."""
        if not hasattr(self._local, 'data') or key not in self._local.data:
            return default

        entry = self._local.data[key]
        entry["access_count"] += 1
        entry["last_accessed"] = datetime.now()

        return entry["value"]

    def exists(self, key: str) -> bool:
        """Check if a key exists in working memory."""
        if not hasattr(self._local, 'data'):
            return False
        return key in self._local.data

    def get_all(self) -> Dict[str, Any]:
        """Get all key-value pairs (values only, not metadata)."""
        if not hasattr(self._local, 'data'):
            return {}
        return {k: v["value"] for k, v in self._local.data.items()}

    def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a key (set time, access count, etc.)."""
        if not hasattr(self._local, 'data') or key not in self._local.data:
            return None

        entry = self._local.data[key].copy()
        entry.pop("value")  # Don't include actual value in metadata
        return entry

    def get_keys(self) -> List[str]:
        """Get list of all keys in working memory."""
        if not hasattr(self._local, 'data'):
            return []
        return list(self._local.data.keys())

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return self._stats.copy()

    def debug_info(self) -> Dict[str, Any]:
        """Get detailed debug information about current memory state."""
        info = {
            "stats": self.get_stats(),
            "has_data": hasattr(self._local, 'data'),
            "keys": self.get_keys() if hasattr(self._local, 'data') else [],
            "key_count": len(self.get_keys()) if hasattr(self._local, 'data') else 0,
        }

        if hasattr(self._local, 'created_at'):
            info["created_at"] = self._local.created_at.isoformat()

        if hasattr(self._local, 'request_id'):
            info["request_id"] = self._local.request_id

        return info

    def cleanup_expired(self, max_age_seconds: int = 3600):
        """
        Clean up old entries (for potential future use).
        Currently all entries are request-scoped and cleared manually.
        """
        # In a request-scoped design, cleanup happens via clear() calls
        # This could be extended for time-based cleanup in multi-request scenarios
        pass

    # Specialized helper methods for common agent patterns

    def append_to_list(self, key: str, value: Any):
        """Append a value to a list in working memory."""
        current_list = self.get(key, [])
        if not isinstance(current_list, list):
            current_list = [current_list]
        current_list.append(value)
        self.set(key, current_list)

    def increment_counter(self, key: str, increment: int = 1):
        """Increment a counter in working memory."""
        current_value = self.get(key, 0)
        if not isinstance(current_value, (int, float)):
            current_value = 0
        self.set(key, current_value + increment)

    def set_if_not_exists(self, key: str, value: Any) -> bool:
        """Set a value only if the key doesn't exist."""
        if self.exists(key):
            return False
        self.set(key, value)
        return True

    def get_request_context(self) -> Dict[str, Any]:
        """Get context information about the current request."""
        return {
            "request_id": getattr(self._local, 'request_id', None),
            "created_at": getattr(self._local, 'created_at', None),
            "key_count": len(self.get_keys()) if hasattr(self._local, 'data') else 0,
        }

    def health_check(self) -> bool:
        """Check if working memory is operational."""
        try:
            # Test basic functionality
            self.set("test_key", "test_value")
            retrieved = self.get("test_key")
            self.clear()
            return retrieved == "test_value"
        except Exception:
            return False
