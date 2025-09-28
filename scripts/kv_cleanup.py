#!/usr/bin/env python3
"""
KV Store Cleanup Script

Removes test artifacts and malformed keys from the memory database.
Run this when the KV store accumulates test data or invalid keys.
"""

import sys
import os
from pathlib import Path

# Add the src directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core import dao
from src.core.config import DB_PATH

def cleanup_kv_store():
    """
    Remove known test artifacts and malformed keys from KV store.

    This script handles the specific known problematic keys from the
    memory system's development and testing phases.
    """
    print("🧹 Starting KV Store Cleanup...")
    print(f"📍 Database: {DB_PATH}")

    # Keys to remove (known test artifacts and malformed entries)
    keys_to_remove = [
        "",                    # Empty key
        "what",               # String fragment from parsing error
        "displayname",        # Lowercase duplicate of displayName
        "test1",             # Generic test key
        "test2",             # Generic test key
        "test_key",          # Generic test key
        "loose_mode_key_1",  # Test scaffolding
        "loose_mode_key_2",  # Test scaffolding
        "loose_mode_key_3",  # Test scaffolding
        "lose_mode_key_*",   # Pattern for bulk removal
    ]

    removed_count = 0
    errors = []

    # Default user cleanup first
    user_id = "default"

    for key in keys_to_remove:
        try:
            # Try to delete the key
            success = dao.delete_key(user_id, key)
            if success:
                print(f"✅ Removed: {key}")
                removed_count += 1
            else:
                print(f"⚠️  Not found: {key}")
        except Exception as e:
            errors.append(f"Error removing {key}: {e}")

    # Check for pattern-based keys (like lose_mode_key_*)
    try:
        all_keys = dao.list_keys(user_id)
        pattern_keys = [k for k in all_keys if k.key.startswith("lose_mode_key_")]

        for key_obj in pattern_keys:
            try:
                success = dao.delete_key(user_id, key_obj.key)
                if success:
                    print(f"✅ Removed pattern match: {key_obj.key}")
                    removed_count += 1
            except Exception as e:
                errors.append(f"Error removing pattern key {key_obj.key}: {e}")

    except Exception as e:
        errors.append(f"Error during pattern cleanup: {e}")

    # Summary
    remaining_keys = len(dao.list_keys(user_id))
    print(f"\n📊 Cleanup Summary:")
    print(f"   Removed: {removed_count} keys")
    print(f"   Errors: {len(errors)}")
    print(f"   Remaining keys: {remaining_keys}")

    if errors:
        print(f"\n⚠️  Errors during cleanup:")
        for error in errors[:5]:  # Limit output
            print(f"   {error}")
        if len(errors) > 5:
            print(f"   ... and {len(errors) - 5} more")

    if remaining_keys > 20:
        print("\n🔍 Consider manual review - high key count suggests more cleanup needed")
    return removed_count, errors

if __name__ == "__main__":
    print("🧹 Memory Stages KV Store Cleanup Utility")
    print("=" * 50)

    try:
        removed, errors = cleanup_kv_store()

        if errors:
            print("\n❌ Completed with errors - check output above")
            sys.exit(1)
        else:
            print("\n✅ Cleanup completed successfully!")
            if removed > 0:
                print(f"🎯 {removed} problematic keys removed")
            else:
                print("✨ No problematic keys found")
            sys.exit(0)

    except Exception as e:
        print(f"\n❌ Critical error during cleanup: {e}")
        print("💡 Make sure the database is not locked by another process")
        sys.exit(1)
