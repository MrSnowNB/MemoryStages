"""SQLite database initialization and connection management."""

import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

from .config import config

logger = logging.getLogger(__name__)

def init_database() -> None:
    """Initialize SQLite database with schema and pragma settings."""
    config.ensure_data_dir()
    
    with get_connection() as conn:
        # Set pragma configurations for performance and integrity
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = -64000")  # 64MB cache
        
        # Create tables
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kv (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                casing TEXT NOT NULL,
                source TEXT CHECK(source IN ('user','system','import','test')) NOT NULL,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                sensitive INTEGER DEFAULT 0
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS episodic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                payload TEXT NOT NULL
            )
        """)
        
        # Create indices for episodic queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_episodic_ts ON episodic(ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_episodic_actor ON episodic(actor)")
        
        conn.commit()
        logger.info("Database initialized successfully")

@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Get database connection with proper cleanup."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
    try:
        yield conn
    finally:
        conn.close()

def check_db_health() -> bool:
    """Check if database is accessible and has expected tables."""
    try:
        with get_connection() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            required_tables = {'kv', 'episodic'}
            return required_tables.issubset(set(tables))
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False