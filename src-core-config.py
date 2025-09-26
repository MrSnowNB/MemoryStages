"""Configuration management for bot-swarm memory system."""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration from environment variables."""
    
    DB_PATH: str = os.getenv("DB_PATH", "./data/memory.db")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    VERSION: str = "1.0.0-stage1"
    
    @classmethod
    def ensure_data_dir(cls) -> None:
        """Ensure data directory exists for database file."""
        db_dir = os.path.dirname(cls.DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

config = Config()