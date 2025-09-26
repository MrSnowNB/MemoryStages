"""
Stage 1 Implementation - SQLite Foundation Only
DO NOT IMPLEMENT BEYOND STAGE 1 SCOPE
"""

import os
from pathlib import Path

# Database path configuration
DB_PATH = os.getenv("DB_PATH", "./data/memory.db")

# Debug flag
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# Version string
VERSION = "1.0.0-stage1"

def ensure_db_directory():
    """Ensure the database directory exists."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
