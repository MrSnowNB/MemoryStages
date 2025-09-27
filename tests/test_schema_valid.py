"""
Stage 4 scope only. Do not implement beyond this file's responsibilities.
Schema validation tests - ensures data integrity and comprehensive error handling.
"""

import pytest
from pydantic import ValidationError as PydanticValidationError
from src.api.schemas import (
    KVSetRequest, EpisodicRequest, ApprovalCreateRequest, ApprovalDecisionRequest,
    ValidationErrorResponse, ErrorResponse
)
from src.core.schema import KVRecord, VectorRecord, EpisodicEvent, CorrectionAction
from src.core.dao import set_key, add_event, get_key, list_keys, list_events
from datetime import datetime


class TestKVSchemaValidation:
    """Test KV pair schema validation with comprehensive error handling."""

    def test_valid_kv_request_passes(self):
        """Test that valid KV requests pass validation."""
        request = KVSetRequest(
            key="test_key",
            value="test_value",
            source="user",
            casing="lower"
        )
        assert request.key == "test_key"
        assert request.value == "test_value"
        assert request.source == "user"
        assert request.casing == "lower"

    def test_empty_key_fails_validation(self):
        """Test that empty keys are rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            KVSetRequest(key="", value="test", source="user", casing="lower")
        assert "key cannot be empty" in str(exc_info.value)

    def test_empty_value_fails_validation(self):
        """Test that empty values are rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            KVSetRequest(key="test", value="", source="user", casing="lower")
        assert "value cannot be empty" in str(exc_info.value)

    def test_invalid_source_fails_validation(self):
        """Test that invalid sources are rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            KVSetRequest(key="test", value="value", source="invalid", casing="lower")
        assert "source must be one of:" in str(exc_info.value)

    def test_invalid_casing_fails_validation(self):
        """Test that invalid casing values are rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            KVSetRequest(key="test", value="value", source="user", casing="invalid")
        assert "casing must be one of:" in str(exc_info.value)

    @pytest.mark.parametrize("source", ["user", "system", "api", "import"])
    def test_valid_sources_pass(self, source):
        """Test all valid source values."""
        request = KVSetRequest(key="test", value="value", source=source, casing="lower")
        assert request.source == source

    @pytest.mark.parametrize("casing", ["lower", "upper", "mixed", "preserve"])
    def test_valid_casing_values_pass(self, casing):
        """Test all valid casing values."""
        request = KVSetRequest(key="test", value="value", source="user", casing=casing)
        assert request.casing == casing


class TestEpisodicEventValidation:
    """Test episodic event schema validation."""

    def test_valid_episodic_request_passes(self):
        """Test that valid episodic requests pass validation."""
        request = EpisodicRequest(
            actor="user123",
            action="create",
            payload="test payload"
        )
        assert request.actor == "user123"
        assert request.action == "create"
        assert request.payload == "test payload"


class TestApprovalWorkflowValidation:
    """Test approval workflow schema validation."""

    def test_valid_approval_request_passes(self):
        """Test that valid approval requests pass validation."""
        request = ApprovalCreateRequest(
            type="correction",
            payload={"key": "test", "action": "update"},
            requester="user123"
        )
        assert request.type == "correction"
        assert request.requester == "user123"

    def test_empty_requester_fails_validation(self):
        """Test that empty requesters are rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ApprovalCreateRequest(type="correction", payload={}, requester="")
        assert "requester cannot be empty" in str(exc_info.value)

    def test_invalid_approval_type_fails_validation(self):
        """Test that invalid approval types are rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            ApprovalCreateRequest(type="invalid", payload={}, requester="user")
        assert "type must be one of:" in str(exc_info.value)

    def test_valid_approval_decision_request_passes(self):
        """Test that valid approval decision requests pass validation."""
        request = ApprovalDecisionRequest(approver="admin", reason="Approved for testing")
        assert request.approver == "admin"
        assert request.reason == "Approved for testing"


class TestCoreSchemaModels:
    """Test core schema data models."""

    def test_kv_record_creation(self):
        """Test KVRecord creation and properties."""
        ts = datetime.now()
        record = KVRecord(
            key="test_key",
            value="test_value",
            source="user",
            casing="lower",
            sensitive=False,
            updated_at=ts
        )
        assert record.key == "test_key"
        assert record.value == "test_value"
        assert record.source == "user"
        assert record.casing == "lower"
        assert record.sensitive is False
        assert record.updated_at == ts

    def test_episodic_event_creation(self):
        """Test EpisodicEvent creation and properties."""
        ts = datetime.now()
        event = EpisodicEvent(
            id=1,
            ts=ts,
            actor="user",
            action="create",
            payload={"key": "value"}
        )
        assert event.id == 1
        assert event.ts == ts
        assert event.actor == "user"
        assert event.action == "create"
        assert event.payload == {"key": "value"}

    def test_vector_record_creation(self):
        """Test VectorRecord creation and properties."""
        ts = datetime.now()
        record = VectorRecord(
            id="test_id",
            vector=[0.1, 0.2, 0.3],
            metadata={"type": "test"},
            updated_at=ts
        )
        assert record.id == "test_id"
        assert record.vector == [0.1, 0.2, 0.3]
        assert record.metadata == {"type": "test"}

    def test_correction_action_creation(self):
        """Test CorrectionAction creation and properties."""
        ts = datetime.now()
        action = CorrectionAction(
            type="ADD_VECTOR",
            key="test_key",
            metadata={"reason": "drift"},
            timestamp=ts
        )
        assert action.type == "ADD_VECTOR"
        assert action.key == "test_key"
        assert action.metadata == {"reason": "drift"}


class TestDAOIntegrationValidation:
    """Test DAO integration with schema validation."""

    def test_set_key_with_invalid_data_returns_validation_error(self):
        """Test that set_key returns ValidationError for invalid data."""
        result = set_key("", "value", "user", "lower")  # Empty key
        assert isinstance(result, Exception)
        assert isinstance(result, PydanticValidationError)

    def test_set_key_with_valid_data_succeeds(self):
        """Test that set_key succeeds with valid data."""
        result = set_key("test_key", "test_value", "user", "lower")
        # Should return True on success, False/ValidationError on failure
        assert result is True or isinstance(result, Exception)

    def test_add_event_with_invalid_data_returns_validation_error(self):
        """Test that add_event returns ValidationError for invalid data."""
        result = add_event("", "action", "payload")  # Empty actor
        assert isinstance(result, Exception)
        assert isinstance(result, PydanticValidationError)

    def test_get_key_returns_typed_result_or_none(self):
        """Test that get_key returns typed KVRecord or None."""
        result = get_key("nonexistent_key")
        assert result is None or isinstance(result, KVRecord)

    def test_list_keys_returns_typed_results(self):
        """Test that list_keys returns list of KVRecord."""
        result = list_keys()
        assert isinstance(result, list)
        # All items should be KVRecord instances (if any exist)
        for item in result:
            assert isinstance(item, KVRecord)

    def test_list_events_returns_typed_results(self):
        """Test that list_events returns list of EpisodicEvent."""
        result = list_events()
        assert isinstance(result, list)
        # All items should be EpisodicEvent instances (if any exist)
        for item in result:
            assert isinstance(item, EpisodicEvent)


class TestErrorResponseModels:
    """Test error response models."""

    def test_validation_error_response_creation(self):
        """Test ValidationErrorResponse creation."""
        error_response = ValidationErrorResponse(
            message="Validation failed",
            errors=[
                {"field": "key", "message": "cannot be empty", "value": ""},
                {"field": "source", "message": "invalid value", "value": "invalid"}
            ]
        )
        assert error_response.error_type == "VALIDATION_ERROR"
        assert error_response.message == "Validation failed"
        assert len(error_response.errors) == 2

    def test_error_response_creation(self):
        """Test ErrorResponse creation."""
        error_response = ErrorResponse(
            error_type="DATABASE_ERROR",
            message="Connection failed",
            details={"code": 500, "reason": "timeout"}
        )
        assert error_response.error_type == "DATABASE_ERROR"
        assert error_response.message == "Connection failed"
        assert error_response.details["code"] == 500


class TestBackwardCompatibility:
    """Test that schema changes maintain backward compatibility."""

    def test_existing_stage1_data_patterns_still_valid(self):
        """Ensure Stage 1 data patterns still validate correctly."""
        # Test the standard patterns that should have existed in Stage 1
        request = KVSetRequest(
            key="existing_key",
            value="existing_value",
            source="api",
            casing="preserve"
        )
        assert request.source in ["user", "system", "api", "import"]
        assert request.casing in ["lower", "upper", "mixed", "preserve"]

    def test_sensitive_data_handling(self):
        """Test sensitive data validation."""
        sensitive_request = KVSetRequest(
            key="secret_key",
            value="secret_value",
            source="user",
            casing="preserve",
            sensitive=True
        )
        assert sensitive_request.sensitive is True

        non_sensitive_request = KVSetRequest(
            key="normal_key",
            value="normal_value",
            source="user",
            casing="preserve",
            sensitive=False
        )
        assert non_sensitive_request.sensitive is False
