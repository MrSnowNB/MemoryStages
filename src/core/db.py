"""
Stage 1 Implementation - SQLite Foundation Only
DO NOT IMPLEMENT BEYOND STAGE 1 SCOPE
"""

import sqlite3
from contextlib import contextmanager
from typing import Generator
from .config import DB_PATH, ensure_db_directory

# Ensure database directory exists
ensure_db_directory()

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Get a SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize the database with required tables."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Create kv table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kv (
                key TEXT PRIMARY KEY,
                value TEXT,
                casing TEXT,
                source TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sensitive BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Create episodic table  
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS episodic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                actor TEXT,
                action TEXT,
                payload TEXT
            )
        ''')
        
        conn.commit()

def health_check():
    """Check database health."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            # Check if required tables exist
            table_names = [table[0] for table in tables]
            required_tables = ['kv', 'episodic']
            
            if all(table in table_names for table in required_tables):
                return True
            else:
                return False
    except Exception:
        return False
