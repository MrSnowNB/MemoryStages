"""
Stage 1 Implementation - SQLite Foundation Only
DO NOT IMPLEMENT BEYOND STAGE 1 SCOPE
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Tuple
from .db import get_db, init_db
from .config import DEBUG

# Initialize database on module import
init_db()

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

def get_key(key: str) -> Optional[KVPair]:
    """Get a key-value pair by key."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT key, value, casing, source, updated_at, sensitive FROM kv WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        
        if row:
            return KVPair(*row)
        return None

def set_key(key: str, value: str, source: str, casing: str, sensitive: bool = False) -> bool:
    """Set a key-value pair."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if the key already exists
        existing = get_key(key)
        if existing:
            # Update existing record
            cursor.execute('''
                UPDATE kv 
                SET value = ?, casing = ?, source = ?, updated_at = CURRENT_TIMESTAMP, sensitive = ?
                WHERE key = ?
            ''', (value, casing, source, sensitive, key))
        else:
            # Insert new record
            cursor.execute('''
                INSERT INTO kv (key, value, casing, source, sensitive)
                VALUES (?, ?, ?, ?, ?)
            ''', (key, value, casing, source, sensitive))
        
        conn.commit()
        return True

def list_keys() -> List[KVPair]:
    """List all non-tombstone key-value pairs."""
    with get_db() as conn:
        cursor = conn.cursor()
        # Exclude tombstone entries (where value is empty)
        cursor.execute(
            "SELECT key, value, casing, source, updated_at, sensitive FROM kv WHERE value != ''"
        )
        rows = cursor.fetchall()
        
        return [KVPair(*row) for row in rows]

def delete_key(key: str) -> bool:
    """Delete a key by setting its value to empty string (tombstone)."""
    with get_db() as conn:
        cursor = conn.cursor()
        # Set value to empty string instead of deleting (tombstone approach)
        cursor.execute(
            "UPDATE kv SET value = '' WHERE key = ?",
            (key,)
        )
        conn.commit()
        return True

def add_event(actor: str, action: str, payload: str) -> bool:
    """Add an episodic event."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO episodic (actor, action, payload)
            VALUES (?, ?, ?)
        ''', (actor, action, payload))
        conn.commit()
        return True

def list_events(limit: int = 100) -> List[EpisodicEvent]:
    """List recent events."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, ts, actor, action, payload 
            FROM episodic 
            ORDER BY ts DESC 
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        
        return [EpisodicEvent(*row) for row in rows]

def get_kv_count() -> int:
    """Get count of non-tombstone KV entries."""
    with get_db() as conn:
        cursor = conn.cursor()
        # Count records where value is not empty
        cursor.execute("SELECT COUNT(*) FROM kv WHERE value != ''")
        result = cursor.fetchone()
        return result[0] if result else 0
