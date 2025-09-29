"""
Stage 1 Implementation - SQLite Foundation Only
Stage 4 Extension: Enhanced validation rules and approval models
DO NOT IMPLEMENT BEYOND STAGE 4 SCOPE
"""

from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class KVSetRequest(BaseModel):
    key: str
    value: str
    source: str
    casing: str
    sensitive: bool = False

    @field_validator('key')
    @classmethod
    def key_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('key cannot be empty')
        return v

    @field_validator('value')
    @classmethod
    def value_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('value cannot be empty')
        return v

    @field_validator('source')
    @classmethod
    def source_must_be_valid(cls, v):
        valid_sources = ['user', 'system', 'api', 'import']
        if v not in valid_sources:
            raise ValueError(f'source must be one of: {valid_sources}')
        return v

    @field_validator('casing')
    @classmethod
    def casing_must_be_valid(cls, v):
        valid_casings = ['lower', 'upper', 'mixed', 'preserve']
        if v not in valid_casings:
            raise ValueError(f'casing must be one of: {valid_casings}')
        return v

class KVResponse(BaseModel):
    success: bool
    key: str

class KVGetResponse(BaseModel):
    key: str
    value: str
    casing: str
    source: str
    updated_at: datetime
    sensitive: bool

class KVListResponse(BaseModel):
    keys: List[KVGetResponse]

class EpisodicRequest(BaseModel):
    actor: str
    action: str
    payload: str

    @field_validator('actor')
    @classmethod
    def actor_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('actor cannot be empty')
        return v

    @field_validator('action')
    @classmethod
    def action_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('action cannot be empty')
        return v

class EpisodicResponse(BaseModel):
    success: bool
    id: int

class EpisodicListResponse(BaseModel):
    events: List[dict]  # Will be filled with actual event data in response

class HealthResponse(BaseModel):
    status: str
    version: str
    db_health: bool
    kv_count: int

class DebugResponse(BaseModel):
    message: str
    timestamp: datetime

class SearchResult(BaseModel):
    key: str
    value: str
    score: float
    casing: str
    source: str
    updated_at: datetime

class SearchResponse(BaseModel):
    results: List[SearchResult]


# Stage 4: Enhanced error response models with detailed validation messages
class ValidationFieldError(BaseModel):
    field: str
    message: str
    value: Any

class ValidationErrorResponse(BaseModel):
    error_type: str = "VALIDATION_ERROR"
    message: str
    errors: List[ValidationFieldError]
    timestamp: datetime = None

    def __init__(self, **data):
        super().__init__(timestamp=datetime.now(), **data)

class ErrorResponse(BaseModel):
    error_type: str
    message: str
    timestamp: datetime = None
    details: Optional[Dict[str, Any]] = None

    def __init__(self, **data):
        super().__init__(timestamp=datetime.now(), **data)


# Stage 4: Approval workflow request/response models
class ApprovalRequestBase(BaseModel):
    type: str  # 'correction', 'sensitive_operation'
    payload: Dict[str, Any]
    requester: str

    @field_validator('type')
    @classmethod
    def type_must_be_valid(cls, v):
        valid_types = ['correction', 'sensitive_operation']
        if v not in valid_types:
            raise ValueError(f'type must be one of: {valid_types}')
        return v

    @field_validator('requester')
    @classmethod
    def requester_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('requester cannot be empty')
        return v

class ApprovalCreateRequest(ApprovalRequestBase):
    pass

class ApprovalResponse(BaseModel):
    success: bool
    request_id: str
    message: str

class ApprovalStatus(BaseModel):
    id: str
    type: str
    payload: Dict[str, Any]
    requester: str
    status: str  # pending, approved, rejected, expired
    created_at: datetime
    expires_at: datetime

class ApprovalDecisionRequest(BaseModel):
    approver: str
    reason: str = ""

    @field_validator('approver')
    @classmethod
    def approver_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('approver cannot be empty')
        return v

class ApprovalListResponse(BaseModel):
    pending_requests: List[ApprovalStatus]


# Stage 7: Chat API request/response models
class ChatMessageRequest(BaseModel):
    content: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None

    @field_validator('content')
    @classmethod
    def content_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('content cannot be empty')
        return v

    @field_validator('content')
    @classmethod
    def content_must_be_reasonable_length(cls, v):
        if len(v) > 2000:
            raise ValueError('content must be less than 2000 characters')
        return v

class MemoryProvenance(BaseModel):
    """
    Detailed provenance information for memory results in chat API responses.

    Includes the type of memory (KV, semantic, LLM), with associated scores
    and explanations for how the result was determined.
    """
    type: str  # "kv", "semantic", "llm"
    key: Optional[str] = None
    value: Optional[str] = None
    score: float
    explanation: str

class ChatMessageResponse(BaseModel):
    message_id: str
    content: str
    model_used: str
    timestamp: datetime
    confidence: float
    processing_time_ms: int
    orchestrator_type: str
    agents_consulted: List[str]
    validation_passed: bool
    memory_results: List[MemoryProvenance]  # Changed from memory_sources to provide detailed provenance
    session_id: Optional[str] = None

class ChatHealthResponse(BaseModel):
    status: str
    model: str
    agent_count: int
    orchestrator_type: str
    ollama_service_healthy: bool
    memory_adapter_enabled: bool
    timestamp: datetime

class ChatErrorResponse(ErrorResponse):
    session_id: Optional[str] = None
