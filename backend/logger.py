__module_name__ = "logger"

import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

def setup_agent_logger():
    """Setup a minimal logger for tracking agent actions and state changes."""
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log file with timestamp
    log_filename = f"agent_actions_{datetime.now().strftime('%Y%m%d')}.log"
    log_filepath = os.path.join(log_dir, log_filename)
    
    # Configure logger
    logger = logging.getLogger("agent_tracker")
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()
    
    # Create file handler
    file_handler = logging.FileHandler(log_filepath, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Create simple formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    return logger

# Global logger instance
_logger = None

def get_logger():
    """Get the agent logger instance."""
    global _logger
    if _logger is None:
        _logger = setup_agent_logger()
    return _logger

def log_agent_action(agent_name: str, action: str, state_changes: Optional[Dict[str, Any]] = None, user_input: Optional[str] = None):
    """Log an agent action with state changes."""
    logger = get_logger()
    
    # Build log message
    parts = [f"{agent_name.upper()}: {action}"]
    
    if user_input:
        # Truncate long user input
        truncated_input = user_input[:50] + "..." if len(user_input) > 50 else user_input
        parts.append(f"Input: '{truncated_input}'")
    
    if state_changes:
        # Log key state changes
        changes = []
        for key, value in state_changes.items():
            if isinstance(value, bool):
                changes.append(f"{key}={value}")
            elif isinstance(value, str) and value:
                changes.append(f"{key}='{value[:30]}...' " if len(value) > 30 else f"{key}='{value}'")
            elif value is not None:
                changes.append(f"{key}=<set>")
        
        if changes:
            parts.append(f"Changes: {', '.join(changes)}")
    
    logger.info(" | ".join(parts))

def log_router_decision(current_action: str, user_input: str, key_state_flags: Dict[str, Any]):
    """Log router routing decisions."""
    logger = get_logger()
    
    # Build state summary
    flags = []
    for key, value in key_state_flags.items():
        if isinstance(value, bool) and value:
            flags.append(key)
        elif value is not None and not isinstance(value, bool):
            flags.append(f"{key}='{str(value)[:20]}'")
    
    state_summary = f"State: [{', '.join(flags)}]" if flags else "State: [initial]"
    
    truncated_input = user_input[:40] + "..." if len(user_input) > 40 else user_input
    
    logger.info(f"ROUTER: Decision -> {current_action} | Input: '{truncated_input}' | {state_summary}")

def log_error(agent_name: str, error_msg: str, context: Optional[str] = None):
    """Log an error with context."""
    logger = get_logger()
    
    parts = [f"{agent_name.upper()}: ERROR - {error_msg}"]
    if context:
        parts.append(f"Context: {context}")
    
    logger.error(" | ".join(parts))