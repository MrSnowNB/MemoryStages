"""
Stage 1 Implementation - SQLite Foundation Only
Stage 4 Extension: Schema validation and typed results
DO NOT IMPLEMENT BEYOND STAGE 4 SCOPE
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Tuple, Union
from pydantic import ValidationError
from .db import get_db, init_db
from .config import debug_enabled, get_vector_store, get_embedding_provider, are_vector_features_enabled, SCHEMA_VALIDATION_STRICT
from .schema import KVRecord, VectorRecord, EpisodicEvent as SchemaEpisodicEvent
from ..api.schemas import KVSetRequest, EpisodicRequest

# Initialize database on module import
init_db()

# Import logger safely to avoid circular imports
try:
    from ...util.logging import logger
except ImportError:
    # Fallback for direct module execution
    import logging
    logger = logging.getLogger("dao_fallback")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(logging.StreamHandler())

class KVPair:
    """Data class for key-value pairs."""
    def __init__(self, key: str, value: str, casing: str, source: str, 
                 updated_at: datetime, sensitive: bool = False):
        self.key = key
        self.value = value
        self.casing = casing
        self.source = source
        self.updated_at = updated_at
        self.sensitive = sensitive

class EpisodicEvent:
    """Data class for episodic events."""
    def __init__(self, id: int, ts: datetime, actor: str, action: str, payload: str):
        self.id = id
        self.ts = ts
        self.actor = actor
        self.action = action
        self.payload = payload

def get_key(user_id: str, key: str) -> Optional[KVRecord]:
    """Get a key-value pair by user_id and key with typed result."""
    try:
        if not user_id or not user_id.strip() or not key or not key.strip():
            return None

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT key, value, casing, source, updated_at, sensitive FROM kv WHERE user_id = ? AND key = ?",
                (user_id.strip(), key.strip())
            )
            row = cursor.fetchone()

            if row:
                key_val, value, casing, source, updated_at, sensitive = row
                return KVRecord(
                    key=key_val,
                    value=value,
                    source=source,
                    casing=casing,
                    sensitive=sensitive,
                    updated_at=updated_at
                )
            return None
    except Exception as e:
        logger.error(f"Failed to get key '{key}' for user '{user_id}': {e}")
        return None

def set_key(user_id: str, key: str, value: str, source: str, casing: str, sensitive: bool = False) -> Union[bool, Exception]:
    """Set a key-value pair with conditional schema validation."""
    if SCHEMA_VALIDATION_STRICT:
        try:
            # Validate input using pydantic model when strict validation enabled
            kv_request = KVSetRequest(key=key, value=value, source=source, casing=casing, sensitive=sensitive)
        except ValidationError as e:
            logger.error(f"Schema validation failed for KV set operation: {e}")
            return e

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Check if the key already exists for this user
            existing = get_key(user_id, key)
            if existing:
                # Update existing record
                cursor.execute(
                    "UPDATE kv SET value = ?, casing = ?, source = ?, updated_at = CURRENT_TIMESTAMP, sensitive = ? WHERE user_id = ? AND key = ?",
                    (value, casing, source, sensitive, user_id, key)
                )
            else:
                # Insert new record
                cursor.execute(
                    "INSERT INTO kv (user_id, key, value, casing, source, sensitive) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, key, value, casing, source, sensitive)
                )

            conn.commit()

    except Exception as db_error:
        logger.error(f"Database error during set_key operation for user '{user_id}': {db_error}")
        return db_error

    # For vector operations, continue trying even if database write failed
    # Vector operations (Stage 2) - conditionally embed non-sensitive keys
    if not sensitive and are_vector_features_enabled():
        try:
            vector_store = get_vector_store()
            embedding_provider = get_embedding_provider()

            if vector_store and embedding_provider:
                # Generate embedding for the content (combine key and value for context)
                # Use user-scoped key for vector operations to avoid conflicts
                vector_key = f"{user_id}:{key}"
                content_to_embed = f"{key}: {value}"
                embedding = embedding_provider.embed_text(content_to_embed)

                # Create vector record and store
                from ..vector.types import VectorRecord
                vector_record = VectorRecord(
                    id=vector_key,
                    vector=embedding,
                    metadata={"source": source, "casing": casing, "user_id": user_id}
                )

                # Check if we need to update existing vector or add new one
                if existing:
                    # Remove old vector first (FAISS doesn't support direct updates)
                    try:
                        vector_store.delete(vector_key)
                    except NotImplementedError:
                        pass  # OK for FAISS - will rebuild periodically

                # Add/update vector record
                vector_store.add(vector_record)

                # Log vector operation
                logger.log_vector_operation("added", vector_key, {
                    "provider": vector_store.__class__.__name__,
                    "dimension": len(embedding),
                    "operation": "update" if existing else "create"
                })

        except Exception as e:
            # Vector operations should never break SQLite functionality
            # Log error but continue with SQLite operation
            logger.warning(f"Vector operation failed for key '{key}' user '{user_id}': {e}")

    return True

def list_keys(user_id: str) -> List[KVRecord]:
    """List all non-tombstone key-value pairs for a user with typed results."""
    try:
        if not user_id or not user_id.strip():
            return []

        with get_db() as conn:
            cursor = conn.cursor()
            # Exclude tombstone entries (where value is empty)
            cursor.execute(
                "SELECT key, value, casing, source, updated_at, sensitive FROM kv WHERE user_id = ? AND value != ''",
                (user_id.strip(),)
            )
            rows = cursor.fetchall()

            records = []
            for row in rows:
                key_val, value, casing, source, updated_at, sensitive = row
                records.append(KVRecord(
                    key=key_val,
                    value=value,
                    source=source,
                    casing=casing,
                    sensitive=sensitive,
                    updated_at=updated_at
                ))
            return records
    except Exception as e:
        logger.error(f"Failed to list keys for user '{user_id}': {e}")
        return []

# Backward compatibility function for existing code
def list_all_keys() -> List[KVRecord]:
    """DEPRECATED: List all non-tombstone key-value pairs for all users (for migration compatibility)."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # Exclude tombstone entries (where value is empty)
            cursor.execute(
                "SELECT key, value, casing, source, updated_at, sensitive FROM kv WHERE value != ''"
            )
            rows = cursor.fetchall()

            records = []
            for row in rows:
                key_val, value, casing, source, updated_at, sensitive = row
                records.append(KVRecord(
                    key=key_val,
                    value=value,
                    source=source,
                    casing=casing,
                    sensitive=sensitive,
                    updated_at=updated_at
                ))
            return records
    except Exception as e:
        logger.error(f"Failed to list all keys: {e}")
        return []

def delete_key(user_id: str, key: str) -> bool:
    """Delete a key by setting its value to empty string (tombstone) for a specific user."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # Set value to empty string instead of deleting (tombstone approach)
            cursor.execute(
                "UPDATE kv SET value = '' WHERE user_id = ? AND key = ?",
                (user_id, key)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Database error during delete_key operation for user '{user_id}': {e}")
        return False

    # Vector operations (Stage 2) - remove from vector index on tombstone
    if are_vector_features_enabled():
        try:
            vector_store = get_vector_store()
            if vector_store:
                # Try to delete from vector store
                # Use user-scoped key for vector operations
                vector_key = f"{user_id}:{key}"
                try:
                    vector_store.delete(vector_key)
                    # Log vector operation
                    logger.log_vector_operation("deleted", vector_key, {
                        "provider": vector_store.__class__.__name__,
                        "reason": "tombstone"
                    })
                except NotImplementedError:
                    # FAISS doesn't support direct deletion - log but continue
                    logger.log_vector_operation("delete_skipped", vector_key, {
                        "provider": vector_store.__class__.__name__,
                        "reason": "not_implemented"
                    })
                except Exception as e:
                    # Log other vector deletion errors but don't fail
                    logger.log_vector_operation("delete_failed", vector_key, {
                        "provider": vector_store.__class__.__name__,
                        "error": str(e)[:100]
                    })

        except Exception as e:
            # Vector operations should never break SQLite functionality
            logger.warning(f"Vector deletion failed for key '{key}' user '{user_id}': {e}")

    return True

def add_event(user_id: str, actor: str, action: str, payload: str) -> Union[bool, Exception]:
    """Add an episodic event with user_id scoping."""
    if SCHEMA_VALIDATION_STRICT:
        try:
            # Validate input using pydantic model when strict validation enabled
            event_request = EpisodicRequest(actor=actor, action=action, payload=payload)
        except ValidationError as e:
            logger.error(f"Schema validation failed for episodic event operation: {e}")
            return e

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO episodic (user_id, actor, action, payload) VALUES (?, ?, ?, ?)",
                (user_id, actor, action, payload)
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Database error during add_event operation for user '{user_id}': {e}")
        return e

def list_events(user_id: str, limit: int = 100) -> List[SchemaEpisodicEvent]:
    """List recent events for a user with typed results."""
    try:
        if limit <= 0 or not user_id or not user_id.strip():
            return []

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, ts, actor, action, payload
                FROM episodic
                WHERE user_id = ?
                ORDER BY ts DESC
                LIMIT ?
            ''', (user_id.strip(), limit))
            rows = cursor.fetchall()

            events = []
            for row in rows:
                event_id, ts, actor, action, payload = row
                # Parse payload as dict, default to empty dict if not valid JSON
                try:
                    import json
                    parsed_payload = json.loads(payload) if payload else {}
                except (json.JSONDecodeError, ValueError):
                    parsed_payload = {"raw_data": payload}

                events.append(SchemaEpisodicEvent(
                    id=event_id,
                    ts=ts,
                    actor=actor,
                    action=action,
                    payload=parsed_payload
                ))
            return events
    except Exception as e:
        logger.error(f"Failed to list events for user '{user_id}': {e}")
        return []

def get_kv_count(user_id: str = None) -> int:
    """Get count of non-tombstone KV entries for a user or all users."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            if user_id and user_id.strip():
                # Count for specific user
                cursor.execute("SELECT COUNT(*) FROM kv WHERE user_id = ? AND value != ''", (user_id.strip(),))
            else:
                # Count for all users (for admin/stats)
                cursor.execute("SELECT COUNT(*) FROM kv WHERE value != ''")
            result = cursor.fetchone()
            return result[0] if result else 0
    except Exception as e:
        logger.error(f"Failed to get KV count{' for user ' + user_id if user_id else ''}: {e}")
        return 0

# Stage 4 stub function for audit testing
def set_key_with_validation(request: KVSetRequest) -> Union[bool, Exception]:
    """Stub function for Stage 4 audit testing - wraps set_key with validation."""
    return set_key(request.key, request.value, request.source, request.casing, request.sensitive)
