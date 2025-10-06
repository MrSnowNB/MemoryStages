"""
Stage 6: Key Normalization Tests
Tests for canonical key normalization and case-insensitive lookup.
"""

import pytest
from unittest.mock import patch

from src.core.dao import _normalize_key, set_key, get_key
from src.core.db import init_db
from src.core.privacy import configure_privacy_enforcement


class TestKeyNormalization:
    """Test key normalization functionality."""

    def setup_method(self):
        """Reset configuration before each test."""
        import src.core.config as config
        config.KEY_NORMALIZATION_STRICT = True
        configure_privacy_enforcement(enabled=False)

    def teardown_method(self):
        """Reset configuration after each test."""
        import src.core.config as config
        config.KEY_NORMALIZATION_STRICT = True
        configure_privacy_enforcement(enabled=False)

    @pytest.mark.parametrize("original,expected", [
        ("displayname", "displayName"),
        ("DisplayName", "displayName"),  # Should normalize even with mixed case input
        ("FIRSTNAME", "firstName"),
        ("favoritelanguage", "favoriteLanguage"),
        ("emailaddress", "emailAddress"),
        ("workaddress", "workAddress"),
        ("preferredname", "preferredName"),
        ("phonenumber", "phoneNumber"),
        ("companyname", "companyName"),
        ("jobtitle", "jobTitle"),
        ("maritalstatus", "maritalStatus"),
        ("occupation", "occupation"),
        ("unmapped_key", "unmapped_key"),  # Unmapped keys returned as-is
    ])
    def test_key_normalization_canonical_mapping(self, original, expected):
        """Test key normalization canonical mappings."""
        import src.core.config as config
        original_strict = config.KEY_NORMALIZATION_STRICT

        try:
            config.KEY_NORMALIZATION_STRICT = True
            result = _normalize_key(original)
            assert result == expected
        finally:
            config.KEY_NORMALIZATION_STRICT = original_strict

    def test_key_normalization_disabled(self):
        """Test key normalization returns original when disabled."""
        import src.core.config as config
        original_strict = config.KEY_NORMALIZATION_STRICT

        try:
            config.KEY_NORMALIZATION_STRICT = False
            result = _normalize_key("displayname")
            assert result == "displayname"  # Should return original
        finally:
            config.KEY_NORMALIZATION_STRICT = original_strict

    def test_key_normalization_write_storage(self):
        """Test key normalization during write operations."""
        from src.core.db import init_db

        # Initialize database and reset privacy
        init_db()
        configure_privacy_enforcement(enabled=False)

        user_id = "test_user"

        # Set a key that should be normalized
        result = set_key(user_id, "favoritelanguage", "python", "test", "preserve")
        assert result is True

        # Should be retrievable by canonical key
        record = get_key(user_id, "favoriteLanguage")
        assert record is not None
        assert record.key == "favoriteLanguage"
        assert record.value == "python"

    def test_key_normalization_case_insensitive_lookup(self):
        """Test case-insensitive key lookup with normalization."""
        init_db()
        configure_privacy_enforcement(enabled=False)

        user_id = "test_user"

        # Set key with canonical form
        result = set_key(user_id, "favoriteLanguage", "python", "test", "preserve")
        assert result is True

        # Should be retrievable by various case variations
        variations = ["favoritelanguage", "FavoriteLanguage", "FAVORITELANGUAGE", "favoriteLanguage"]
        for variation in variations:
            record = get_key(user_id, variation)
            assert record is not None, f"Failed for variation: {variation}"
            assert record.value == "python"

    @patch('util.logging.audit_event')
    def test_key_normalization_audit_logging(self, mock_audit_event):
        """Test key normalization audit logging."""
        configure_privacy_enforcement(enabled=False)

        # Set a key that gets normalized
        result = set_key("test_user", "displayname", "John Doe", "test", "preserve")
        assert result is True

        # Should have logged the normalization
        mock_audit_event.assert_called_once()
        call_args = mock_audit_event.call_args
        assert call_args[1]["event_type"] == "key_normalization_applied"
        assert call_args[1]["identifiers"]["original_key"] == "displayname"
        assert call_args[1]["identifiers"]["normalized_key"] == "displayName"
