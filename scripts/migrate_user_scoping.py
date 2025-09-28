#!/usr/bin/env python3
"""
Database migration script for Track A: Per-user scoping.

This script migrates existing global KV and episodic data to user-scoped tables.
Existing data will be assigned to user_id='default' for backward compatibility.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.db import migrate_to_user_scoping

if __name__ == "__main__":
    print("🚀 Starting database migration to per-user scoping...")
    print("📋 This will migrate all existing KV and episodic data to user 'default'")
    print("⚠️  If you have important data, please back it up before proceeding!")

    try:
        success = migrate_to_user_scoping()
        if success:
            print("✅ Migration completed successfully!")
            print("🎉 Your database now supports per-user memory scoping.")
            print("📝 Existing data is available under user_id='default'")
        else:
            print("❌ Migration failed!")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Migration error: {e}")
        sys.exit(2)
