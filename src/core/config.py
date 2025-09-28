"""
Stage 1 Implementation - SQLite Foundation Only
DO NOT IMPLEMENT BEYOND STAGE 1 SCOPE
"""

import os
from pathlib import Path

# Database path configuration
DB_PATH = os.getenv("DB_PATH", "./data/memory.db")

# Debug flag is now a function to be dynamic
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# Vector system configuration (Stage 2 - default disabled)
VECTOR_ENABLED = os.getenv("VECTOR_ENABLED", "false").lower() == "true"
VECTOR_PROVIDER = os.getenv("VECTOR_PROVIDER", "memory")  # memory|faiss
EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "hash")  # hash|custom
SEARCH_API_ENABLED = os.getenv("SEARCH_API_ENABLED", "false").lower() == "true"

# Heartbeat system configuration (Stage 3 - default disabled)
HEARTBEAT_ENABLED = os.getenv("HEARTBEAT_ENABLED", "false").lower() == "true"
HEARTBEAT_INTERVAL_SEC = int(os.getenv("HEARTBEAT_INTERVAL_SEC", "60"))
CORRECTION_MODE = os.getenv("CORRECTION_MODE", "propose")  # off|propose|apply
DRIFT_RULESET = os.getenv("DRIFT_RULESET", "strict")  # strict|lenient

# Approval workflow and schema validation configuration (Stage 4 - default disabled)
APPROVAL_ENABLED = os.getenv("APPROVAL_ENABLED", "false").lower() == "true"
APPROVAL_MODE = os.getenv("APPROVAL_MODE", "manual")  # manual|auto
APPROVAL_TIMEOUT_SEC = int(os.getenv("APPROVAL_TIMEOUT_SEC", "3600"))
SCHEMA_VALIDATION_STRICT = os.getenv("SCHEMA_VALIDATION_STRICT", "false").lower() == "true"

# Operations dashboard configuration (Stage 5 - default disabled)
DASHBOARD_ENABLED = os.getenv("DASHBOARD_ENABLED", "false").lower() == "true"
DASHBOARD_TYPE = os.getenv("DASHBOARD_TYPE", "tui")  # tui|web
DASHBOARD_AUTH_TOKEN = os.getenv("DASHBOARD_AUTH_TOKEN")  # Required when enabled
DASHBOARD_SENSITIVE_ACCESS = os.getenv("DASHBOARD_SENSITIVE_ACCESS", "false").lower() == "true"
DASHBOARD_MAINTENANCE_MODE = os.getenv("DASHBOARD_MAINTENANCE_MODE", "false").lower() == "true"

# Privacy and Maintenance Controls (Stage 6 - default disabled)
PRIVACY_ENFORCEMENT_ENABLED = os.getenv("PRIVACY_ENFORCEMENT_ENABLED", "false").lower() == "true"
PRIVACY_AUDIT_LEVEL = os.getenv("PRIVACY_AUDIT_LEVEL", "standard")  # minimal|standard|verbose
BACKUP_ENABLED = os.getenv("BACKUP_ENABLED", "false").lower() == "true"
BACKUP_ENCRYPTION_ENABLED = os.getenv("BACKUP_ENCRYPTION_ENABLED", "true").lower() == "true"  # Default true when backup enabled
BACKUP_INCLUDE_SENSITIVE = os.getenv("BACKUP_INCLUDE_SENSITIVE", "false").lower() == "true"
MAINTENANCE_ENABLED = os.getenv("MAINTENANCE_ENABLED", "false").lower() == "true"
MAINTENANCE_SCHEDULE_SEC = int(os.getenv("MAINTENANCE_SCHEDULE_SEC", "86400"))  # Daily maintenance (24 hours)

# MVP Swarm Configuration - SINGLE POINT OF CONTROL (Stage 7)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "liquid-rag:latest")
SWARM_ENABLED = os.getenv("SWARM_ENABLED", "false").lower() == "true"
SWARM_AGENT_COUNT = int(os.getenv("SWARM_AGENT_COUNT", "4"))
SWARM_ORCHESTRATOR_TYPE = os.getenv("SWARM_ORCHESTRATOR_TYPE", "rule_based")  # rule_based|llm_based
RESPONSE_VALIDATION_STRICT = os.getenv("RESPONSE_VALIDATION_STRICT", "true").lower() == "true"

# Bot Activation Configuration - ALWAYS CREATE AGENTS
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "true").lower() == "true"  # Default True for development
SWARM_FORCE_MOCK = os.getenv("SWARM_FORCE_MOCK", "true").lower() == "true"  # Default True for development
CHAT_API_ENABLED = os.getenv("CHAT_API_ENABLED", "true").lower() == "true"  # Default True for testing

# Version string
VERSION = "1.0.0-stage1"

def get_vector_store():
    """Get configured vector store implementation. Returns None if vector features disabled."""
    if not are_vector_features_enabled():
        return None

    if VECTOR_PROVIDER == "memory":
        from src.vector.index import SimpleInMemoryVectorStore
        return SimpleInMemoryVectorStore()
    elif VECTOR_PROVIDER == "faiss":
        try:
            from src.vector.faiss_store import FaissVectorStore
            return FaissVectorStore()
        except ImportError:
            # Gracefully degrade to memory store if FAISS not available
            from src.vector.index import SimpleInMemoryVectorStore
            return SimpleInMemoryVectorStore()
    else:
        # Default to memory store for unknown providers
        from src.vector.index import SimpleInMemoryVectorStore
        return SimpleInMemoryVectorStore()


def get_embedding_provider():
    """Get configured embedding provider implementation. Returns None if vector features disabled."""
    if not are_vector_features_enabled():
        return None

    if EMBED_PROVIDER == "hash":
        from src.vector.embeddings import DeterministicHashEmbedding
        return DeterministicHashEmbedding()
    elif EMBED_PROVIDER == "custom":
        # TODO: Implement custom embedding provider in future slice
        from src.vector.embeddings import DeterministicHashEmbedding
        return DeterministicHashEmbedding()
    else:
        from src.vector.embeddings import DeterministicHashEmbedding
        return DeterministicHashEmbedding()


def are_vector_features_enabled():
    """Check if vector features are enabled."""
    return os.getenv("VECTOR_ENABLED", "false").lower() == "true"


def debug_enabled():
    """Check if debug mode is enabled."""
    return os.getenv("DEBUG", "true").lower() == "true"


def ensure_db_directory():
    """Ensure the database directory exists."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


def is_heartbeat_enabled():
    """Check if heartbeat system is enabled."""
    return HEARTBEAT_ENABLED


def are_heartbeat_features_enabled():
    """Check if heartbeat requires vector features enabled (since it audits vector vs SQLite)."""
    return HEARTBEAT_ENABLED and are_vector_features_enabled()


def get_heartbeat_interval():
    """Get heartbeat interval in seconds."""
    return HEARTBEAT_INTERVAL_SEC


def get_correction_mode():
    """Get correction mode (off|propose|apply)."""
    return CORRECTION_MODE


def get_drift_ruleset():
    """Get drift ruleset (strict|lenient)."""
    return DRIFT_RULESET


def validate_heartbeat_config():
    """Validate heartbeat configuration and return any issues."""
    issues = []

    if HEARTBEAT_ENABLED and not are_vector_features_enabled():
        issues.append("HEARTBEAT_ENABLED requires VECTOR_ENABLED=true")

    if CORRECTION_MODE not in ["off", "propose", "apply"]:
        issues.append(f"Invalid CORRECTION_MODE: {CORRECTION_MODE}")

    if DRIFT_RULESET not in ["strict", "lenient"]:
        issues.append(f"Invalid DRIFT_RULESET: {DRIFT_RULESET}")

    if HEARTBEAT_INTERVAL_SEC < 1:
        issues.append("HEARTBEAT_INTERVAL_SEC must be >= 1")

    return issues
