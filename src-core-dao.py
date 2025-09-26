"""Data Access Object for KV store and episodic logging."""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from .db import get_connection

logger = logging.getLogger(__name__)

class KVResult:
    """Typed result for KV operations."""
    def __init__(self, key: str, value: str, source: str, updated_at: str, 
                 casing: str, sensitive: int = 0):
        self.key = key
        self.value = value
        self.source = source
        self.updated_at = updated_at
        self.casing = casing
        self.sensitive = bool(sensitive)

class EpisodicResult:
    """Typed result for episodic events."""
    def __init__(self, id: int, ts: str, actor: str, action: str, payload: str):
        self.id = id
        self.ts = ts
        self.actor = actor
        self.action = action
        self.payload = payload

def get_key(key: str) -> Optional[KVResult]:
    """Get key from KV store with exact casing preserved."""
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT key, value, source, updated_at, casing, sensitive FROM kv WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            if row:
                return KVResult(
                    key=row['key'],
                    value=row['value'],
                    source=row['source'],
                    updated_at=row['updated_at'],
                    casing=row['casing'],
                    sensitive=row['sensitive']
                )
            return None
    except Exception as e:
        logger.error(f"Error getting key {key}: {e}")
        raise

def set_key(key: str, value: str, source: str = 'user', 
           casing: Optional[str] = None, sensitive: int = 0) -> Dict[str, Any]:
    """Set key in KV store, preserving exact casing and logging episodic event."""
    if casing is None:
        casing = key  # Preserve original casing by default
    
    try:
        with get_connection() as conn:
            # Upsert the key-value pair
            cursor = conn.execute(
                """INSERT OR REPLACE INTO kv (key, value, casing, source, updated_at, sensitive)
                   VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)""",
                (key, value, casing, source, sensitive)
            )
            
            # Get the updated timestamp
            cursor = conn.execute(
                "SELECT updated_at FROM kv WHERE key = ?", (key,)
            )
            updated_at = cursor.fetchone()['updated_at']
            
            # Log episodic event
            add_event(
                actor='memory_manager',
                action='kv_set',
                payload={
                    'key': key,
                    'value': value,
                    'source': source,
                    'sensitive': bool(sensitive)
                },
                conn=conn
            )
            
            conn.commit()
            logger.info(f"Set key '{key}' with source '{source}'")
            
            return {
                'key': key,
                'value': value,
                'updated_at': updated_at
            }
    except Exception as e:
        logger.error(f"Error setting key {key}: {e}")
        raise

def list_keys() -> List[Dict[str, Any]]:
    """List all keys in KV store."""
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT key, value, updated_at, sensitive FROM kv ORDER BY updated_at DESC"
            )
            return [
                {
                    'key': row['key'],
                    'value': row['value'],
                    'updated_at': row['updated_at'],
                    'sensitive': bool(row['sensitive'])
                }
                for row in cursor.fetchall()
            ]
    except Exception as e:
        logger.error(f"Error listing keys: {e}")
        raise

def delete_key(key: str) -> Dict[str, Any]:
    """Tombstone delete: set value to empty and log episodic event."""
    try:
        with get_connection() as conn:
            # Check if key exists
            cursor = conn.execute("SELECT 1 FROM kv WHERE key = ?", (key,))
            if not cursor.fetchone():
                raise ValueError(f"Key '{key}' not found")
            
            # Set to tombstone (empty value)
            cursor = conn.execute(
                "UPDATE kv SET value = '', updated_at = CURRENT_TIMESTAMP WHERE key = ?",
                (key,)
            )
            
            # Log episodic event
            add_event(
                actor='memory_manager',
                action='kv_delete',
                payload={'key': key},
                conn=conn
            )
            
            conn.commit()
            logger.info(f"Deleted key '{key}' (tombstone)")
            
            return {'key': key, 'deleted': True}
    except Exception as e:
        logger.error(f"Error deleting key {key}: {e}")
        raise

def add_event(actor: str, action: str, payload: Dict[str, Any], 
              conn=None) -> Dict[str, Any]:
    """Add event to episodic log."""
    payload_json = json.dumps(payload)
    
    try:
        if conn:
            # Use existing connection (for transactions)
            cursor = conn.execute(
                "INSERT INTO episodic (actor, action, payload) VALUES (?, ?, ?)",
                (actor, action, payload_json)
            )
            event_id = cursor.lastrowid
            cursor = conn.execute(
                "SELECT ts FROM episodic WHERE id = ?", (event_id,)
            )
            ts = cursor.fetchone()['ts']
        else:
            # Create new connection
            with get_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO episodic (actor, action, payload) VALUES (?, ?, ?)",
                    (actor, action, payload_json)
                )
                event_id = cursor.lastrowid
                cursor = conn.execute(
                    "SELECT ts FROM episodic WHERE id = ?", (event_id,)
                )
                ts = cursor.fetchone()['ts']
                conn.commit()
        
        logger.info(f"Added episodic event: {actor} -> {action}")
        return {'id': event_id, 'ts': ts}
    except Exception as e:
        logger.error(f"Error adding episodic event: {e}")
        raise

def list_events(limit: int = 50) -> List[EpisodicResult]:
    """List recent episodic events."""
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, ts, actor, action, payload FROM episodic ORDER BY ts DESC LIMIT ?",
                (limit,)
            )
            return [
                EpisodicResult(
                    id=row['id'],
                    ts=row['ts'],
                    actor=row['actor'],
                    action=row['action'],
                    payload=row['payload']
                )
                for row in cursor.fetchall()
            ]
    except Exception as e:
        logger.error(f"Error listing events: {e}")
        raise

def get_kv_count() -> int:
    """Get count of KV entries (excluding tombstones)."""
    try:
        with get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM kv WHERE value != ''")
            return cursor.fetchone()['count']
    except Exception as e:
        logger.error(f"Error getting KV count: {e}")
        return 0