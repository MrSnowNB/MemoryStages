"""Structured logging utility for bot-swarm memory system."""

import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional

class StructuredLogger:
    """Structured logger with consistent formatting."""
    
    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Create console handler with structured format
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        
        # Structured format with timestamp, level, module, and message
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        if not self.logger.handlers:
            self.logger.addHandler(handler)
    
    def log_operation(self, operation: str, status: str = "success", 
                     duration_ms: Optional[float] = None, 
                     details: Optional[Dict[str, Any]] = None):
        """Log structured operation with status and timing."""
        message_parts = [f"operation={operation}", f"status={status}"]
        
        if duration_ms is not None:
            message_parts.append(f"duration_ms={duration_ms:.2f}")
        
        if details:
            detail_str = " ".join([f"{k}={v}" for k, v in details.items()])
            message_parts.append(detail_str)
        
        message = " | ".join(message_parts)
        
        if status == "success":
            self.logger.info(message)
        elif status == "error":
            self.logger.error(message)
        else:
            self.logger.warning(message)
    
    def log_kv_operation(self, operation: str, key: str, source: str = None, 
                        status: str = "success", duration_ms: float = None):
        """Log KV-specific operations."""
        details = {"key": key}
        if source:
            details["source"] = source
        
        self.log_operation(f"kv_{operation}", status, duration_ms, details)
    
    def log_episodic_operation(self, actor: str, action: str, event_id: int = None, 
                              status: str = "success", duration_ms: float = None):
        """Log episodic-specific operations."""
        details = {"actor": actor, "action": action}
        if event_id:
            details["event_id"] = event_id
        
        self.log_operation("episodic_add", status, duration_ms, details)
    
    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)
    
    def error(self, message: str):
        """Log error message."""
        self.logger.error(message)
    
    def warning(self, message: str):
        """Log warning message."""
        self.logger.warning(message)

def get_logger(name: str, level: int = logging.INFO) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name, level)