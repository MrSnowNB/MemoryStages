"""
Stage 1 Implementation - SQLite Foundation Only
Stage 4 Extension: Schema validation and typed results
DO NOT IMPLEMENT BEYOND STAGE 4 SCOPE
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Tuple, Union, Dict, Any
from pydantic import ValidationError
from .db import get_db, init_db
from .config import debug_enabled, get_vector_store, get_embedding_provider, are_vector_features_enabled, SCHEMA_VALIDATION_STRICT
from .schema import KVRecord, VectorRecord, EpisodicEvent as SchemaEpisodicEvent
from ..api.schemas import KVSetRequest, EpisodicRequest

# Initialize database on module import
init_db()

# Import logger safely to avoid circular imports
try:
    from ..util.logging import logger
except ImportError:
    # Fallback for direct module execution
    import logging
    logger = logging.getLogger("dao_fallback")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(logging.StreamHandler())

# Import privacy enforcer safely
try:
    from .privacy import validate_sensitive_access, PRIVACY_ENFORCEMENT_ENABLED
except ImportError:
    # Fallback if privacy not available yet
    def validate_sensitive_access(accessor: str, data_type: str, reason: str) -> bool:
        return True
    PRIVACY_ENFORCEMENT_ENABLED = False

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

                # Privacy check: Validate access to sensitive data
                if sensitive and PRIVACY_ENFORCEMENT_ENABLED:
                    access_granted = validate_sensitive_access(
                        accessor="dao_get_key",
                        data_type="kv_sensitive_value",
                        reason=f"Retrieve sensitive KV value for key {key} (user: {user_id})"
                    )
                    if not access_granted:
                        logger.warning(f"Privacy access denied for sensitive key {key}")
                        return None
                    logger.info(f"Privacy access granted for sensitive key {key}")

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
            updated_at = datetime.now()
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
                    metadata={"source": source, "casing": casing, "user_id": user_id, "updated_at": updated_at.isoformat()}
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
                print(f"DEBUG: Logger type: {type(logger)}, has log_vector_operation: {hasattr(logger, 'log_vector_operation')}")
                try:
                    logger.log_vector_operation("added", vector_key, {
                        "provider": vector_store.__class__.__name__,
                        "dimension": len(embedding),
                        "operation": "update" if existing else "create"
                    })
                    print("DEBUG: Vector operation logged successfully")
                except AttributeError as e:
                    print(f"DEBUG: Vector operation logging failed: {e}")
                    logger.info(f"Vector operation: added {vector_key} to {vector_store.__class__.__name__} (dimension: {len(embedding)})")

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

                # Privacy check: Validate access to sensitive data in list operations
                if sensitive and PRIVACY_ENFORCEMENT_ENABLED:
                    access_granted = validate_sensitive_access(
                        accessor="dao_list_keys",
                        data_type="kv_sensitive_list",
                        reason=f"List operation including sensitive key {key_val} (user: {user_id})"
                    )
                    if not access_granted:
                        logger.warning(f"Privacy access denied for sensitive key {key_val}")
                        continue  # Skip this sensitive record
                    logger.info(f"Privacy access granted for sensitive key {key_val} in list operation")

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

    # Privacy logging: Log access to potentially sensitive episodic event data
    if PRIVACY_ENFORCEMENT_ENABLED:
        try:
            import json
            parsed_payload = json.loads(payload) if payload else {}
            # Check if payload contains sensitive indicators
            payload_text = str(parsed_payload).lower()
            sensitive_indicators = ['value', 'data', 'secret', 'password', 'token', 'auth', 'credentials']

            if any(indicator in payload_text for indicator in sensitive_indicators):
                validate_sensitive_access(
                    accessor="dao_add_event",
                    data_type="episodic_sensitive_payload",
                    reason=f"Episodic event with potentially sensitive payload (user: {user_id}, action: {action})"
                )
        except (json.JSONDecodeError, ValueError):
            # If payload parsing fails, treat as raw text
            if any(word in payload.lower() for word in ['sensitive', 'value', 'secret', 'password']):
                validate_sensitive_access(
                    accessor="dao_add_event",
                    data_type="episodic_raw_sensitive",
                    reason=f"Episodic event with raw potentially sensitive content (user: {user_id}, action: {action})"
                )

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

                # Privacy check: Validate access to potentially sensitive event payload data
                skip_event = False
                if PRIVACY_ENFORCEMENT_ENABLED:
                    try:
                        import json
                        parsed_payload = json.loads(payload) if payload else {}
                        # Check if payload contains sensitive indicators
                        payload_text = str(parsed_payload).lower()
                        sensitive_indicators = ['value', 'data', 'secret', 'password', 'token', 'auth', 'credentials']

                        if any(indicator in payload_text for indicator in sensitive_indicators):
                            access_granted = validate_sensitive_access(
                                accessor="dao_list_events",
                                data_type="episodic_sensitive_payload",
                                reason=f"Event list operation including potentially sensitive payload (user: {user_id}, action: {action})"
                            )
                            if not access_granted:
                                logger.warning(f"Privacy access denied for event {event_id} with sensitive payload")
                                skip_event = True
                            else:
                                logger.info(f"Privacy access granted for event {event_id}")

                    except (json.JSONDecodeError, ValueError):
                        # If payload parsing fails, check raw payload
                        if any(word in payload.lower() for word in ['sensitive', 'value', 'secret', 'password']) if payload else False:
                            access_granted = validate_sensitive_access(
                                accessor="dao_list_events",
                                data_type="episodic_raw_sensitive",
                                reason=f"Event list operation including raw potentially sensitive content (user: {user_id}, action: {action})"
                            )
                            if not access_granted:
                                logger.warning(f"Privacy access denied for event {event_id} with raw sensitive payload")
                                skip_event = True
                            else:
                                logger.info(f"Privacy access granted for event {event_id}")

                if skip_event:
                    continue

                # Parse payload as dict for final result
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

def get_memory_insights(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Educational function: Get memory entries enriched with agent interaction history.
    Correlates KV entries with episodic events to show which agents processed each entry.
    """
    try:
        # Get recent KV entries for the user
        kv_entries = list_keys(user_id)
        if not kv_entries:
            return []

        # Sort KV entries by updated_at (most recent first)
        kv_entries.sort(key=lambda x: x.updated_at, reverse=True)
        kv_entries = kv_entries[:limit]

        # Get recent episodic events (increased limit to capture all relevant actions)
        events = list_events(user_id, limit=200)  # Get more events to correlate properly

        # Convert events to dict format for easier processing
        event_dicts = []
        for event in events:
            try:
                import json
                payload_parsed = json.loads(event.payload) if isinstance(event.payload, str) and event.payload else event.payload
            except (json.JSONDecodeError, ValueError):
                payload_parsed = {"raw_data": str(event.payload)}

            event_dicts.append({
                "id": event.id,
                "ts": event.ts,
                "actor": event.actor,
                "action": event.action,
                "payload": payload_parsed
            })

        insights = []

        for kv_entry in kv_entries:
            # Find correlated episodic events for this KV entry
            correlated_events = []

            # Look for events within a time window around the KV update
            kv_time = kv_entry.updated_at
            time_window_minutes = 30  # Look at events within 30 minutes of KV update

            for event in event_dicts:
                if isinstance(event["payload"], dict):
                    # Check if event mentions this key in payload or action
                    try:
                        if isinstance(event["ts"], datetime):
                            event_time = event["ts"]
                        else:
                            event_time = datetime.fromisoformat(event["ts"].replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        continue  # Skip events with invalid timestamps

                    # Time correlation: events within window
                    time_diff = abs((event_time - kv_time).total_seconds())
                    time_match = time_diff <= (time_window_minutes * 60)

                    # Content correlation: check if event relates to this key
                    content_match = False
                    if "key" in event["payload"] and event["payload"]["key"] == kv_entry.key:
                        content_match = True
                    elif kv_entry.key in str(event["payload"]):
                        content_match = True
                    elif kv_entry.key in str(event.get("action", "")):
                        content_match = True

                    # Actor-based correlation: certain actors definitely interact with KV
                    actor_kv_related = event["actor"] in ["memory_adapter", "api", "dao", "orchestrator"]

                    if time_match and (content_match or actor_kv_related):
                        correlated_events.append({
                            "event_id": event["id"],
                            "timestamp": event_time,
                            "agent": _map_actor_to_agent(event["actor"]),
                            "action": event["action"],
                            "details": event["payload"],
                            "correlation_type": "content_match" if content_match else "actor_related"
                        })

            # Sort events by timestamp
            correlated_events.sort(key=lambda x: x["timestamp"])

            # Generate agent action summaries
            agent_summaries = _summarize_agent_actions(kv_entry.key, kv_entry.value, correlated_events)

            insights.append({
                "key": kv_entry.key,
                "value": kv_entry.value,
                "updated_at": kv_entry.updated_at.isoformat(),
                "source": kv_entry.source,
                "casing": kv_entry.casing,
                "sensitive": kv_entry.sensitive,
                "agent_interactions": agent_summaries,
                "raw_events": len(correlated_events)
            })

        return insights

    except Exception as e:
        logger.error(f"Failed to get memory insights for user '{user_id}': {e}")
        return []

def _map_actor_to_agent(actor: str) -> Dict[str, str]:
    """Map episodic event actors to agent information."""
    agent_mapping = {
        "ollama_agent": {
            "name": "Ollama Agent",
            "role": "LLM Generation",
            "code": "src/agents/ollama_agent.py"
        },
        "orchestrator": {
            "name": "Rule-Based Orchestrator",
            "role": "Swarm Coordinator",
            "code": "src/agents/orchestrator.py"
        },
        "memory_adapter": {
            "name": "Memory Adapter",
            "role": "Canonical Memory",
            "code": "src/agents/memory_adapter.py"
        },
        "api": {
            "name": "API Layer",
            "role": "HTTP Interface",
            "code": "src/api/main.py"
        },
        "dao": {
            "name": "Data Access Object",
            "role": "Database Layer",
            "code": "src/core/dao.py"
        },
        "chat_api": {
            "name": "Chat API",
            "role": "Conversation Interface",
            "code": "src/api/chat.py"
        }
    }

    return agent_mapping.get(actor, {
        "name": actor.title(),
        "role": "System Component",
        "code": "unknown"
    })

def _summarize_agent_actions(key: str, value: str, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Summarize what each agent did for this memory entry."""
    agent_actions = {}

    for event in events:
        agent = event["agent"]
        agent_key = f"{agent['name']}_{agent['role']}"

        if agent_key not in agent_actions:
            agent_actions[agent_key] = {
                "agent": agent,
                "actions": [],
                "technical_details": []
            }

        # Categorize the action
        action = event["action"]
        details = event["details"]

        if action == "kv_write" or action == "set_key":
            description = f"Wrote '{key}' = '{value}' to SQLite database"
            sql_query = f"INSERT INTO kv (user_id, key, value, source, casing) VALUES ('user_id', '{key}', '{value}', 'source', 'case')"
            agent_actions[agent_key]["technical_details"].append({
                "type": "sql_write",
                "query": sql_query,
                "table": "kv",
                "operation": "INSERT/UPDATE"
            })
        elif action == "kv_read" or action == "get_key":
            description = f"Retrieved value for key '{key}' from SQLite"
            sql_query = f"SELECT value FROM kv WHERE user_id='user_id' AND key='{key}'"
            agent_actions[agent_key]["technical_details"].append({
                "type": "sql_read",
                "query": sql_query,
                "table": "kv",
                "operation": "SELECT"
            })
        elif action.startswith("validation"):
            description = f"Validated memory entry '{key}' for accuracy"
            agent_actions[agent_key]["technical_details"].append({
                "type": "validation",
                "method": "canonical_memory_check",
                "status": event.get("correlation_type", "unknown")
            })
        elif action == "orchestrator_started":
            description = f"Initialized multi-agent swarm coordinator"
            agent_actions[agent_key]["technical_details"].append({
                "type": "initialization",
                "components": ["agent_registry", "memory_adapter", "swarm_configuration"]
            })
        else:
            description = f"Processed '{key}' with action: {action}"

        agent_actions[agent_key]["actions"].append({
            "description": description,
            "timestamp": event["timestamp"].isoformat(),
            "correlation": event["correlation_type"]
        })

    return list(agent_actions.values())
