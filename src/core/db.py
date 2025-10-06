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

        # Create kv table with user scoping
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kv (
                user_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                casing TEXT,
                source TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sensitive BOOLEAN DEFAULT FALSE,
                PRIMARY KEY (user_id, key)
            )
        ''')

        # Create episodic table with Stage 5 temporal memory support
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS episodic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id TEXT,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT,  -- 'user', 'ai', 'system' for semantic clarity
                message TEXT,     -- actual message content for temporal memory
                summary TEXT,     -- AI-generated summary for session recall
                sensitive BOOLEAN DEFAULT FALSE, -- privacy flag for temporal compliance
                actor TEXT,       -- keep for backward compatibility
                action TEXT,      -- keep for backward compatibility
                payload TEXT      -- keep for backward compatibility
            )
        ''')

        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_episodic_user_id_ts ON episodic(user_id, ts DESC)')

        conn.commit()

def migrate_to_user_scoping():
    """Migrate existing global data to user-scoped with default user."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if migration is needed (old schema detection)
        cursor.execute("PRAGMA table_info(kv)")
        kv_columns = [col[1] for col in cursor.fetchall()]

        if 'user_id' not in kv_columns:
            print("🚀 Migrating database to per-user scoping...")

            # Migrate kv table - assume existing data belongs to 'default' user
            try:
                # Create new kv table with user_id
                cursor.execute('''
                    CREATE TABLE kv_new (
                        user_id TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT,
                        casing TEXT,
                        source TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        sensitive BOOLEAN DEFAULT FALSE,
                        PRIMARY KEY (user_id, key)
                    )
                ''')

                # Copy existing data to default user
                cursor.execute('''
                    INSERT INTO kv_new (user_id, key, value, casing, source, updated_at, sensitive)
                    SELECT 'default', key, value, casing, source, updated_at, sensitive
                    FROM kv
                ''')

                # Swap tables
                cursor.execute('DROP TABLE kv')
                cursor.execute('ALTER TABLE kv_new RENAME TO kv')

                print("✅ Migrated kv table")

            except Exception as e:
                print(f"❌ KV migration error: {e}")
                conn.rollback()
                return False

            # Migrate episodic table
            try:
                # Create new episodic table with user_id
                cursor.execute('''
                    CREATE TABLE episodic_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL DEFAULT 'default',
                        ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        actor TEXT,
                        action TEXT,
                        payload TEXT
                    )
                ''')

                # Copy existing data to default user
                cursor.execute('''
                    INSERT INTO episodic_new (id, user_id, ts, actor, action, payload)
                    SELECT id, 'default', ts, actor, action, payload
                    FROM episodic
                ''')

                # Swap tables
                cursor.execute('DROP TABLE episodic')
                cursor.execute('ALTER TABLE episodic_new RENAME TO episodic')

                # Recreate index
                cursor.execute('CREATE INDEX idx_episodic_user_id_ts ON episodic(user_id, ts DESC)')

                print("✅ Migrated episodic table")

            except Exception as e:
                print(f"❌ Episodic migration error: {e}")
                conn.rollback()
                return False

            conn.commit()
            print("🎉 Database migration to per-user scoping complete!")
            return True

        else:
            print("📋 Database already uses per-user scoping - no migration needed")
            return True

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
