"""
Utility functions and protocol helpers for the TCP Chat Application.
"""

import os
import sys
import logging
from datetime import datetime

# ANSI Color codes for terminal styling
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"

def get_timestamp() -> str:
    """Returns formatted current timestamp string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def setup_logger(name: str, log_file: str, level=logging.INFO) -> logging.Logger:
    """
    Sets up a thread-safe logger that writes both to a file and returns the logger instance.
    """
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers if called multiple times
    if not logger.handlers:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_format = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s", 
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
        
    return logger

def format_chat_message(sender: str, message: str, is_private: bool = False, recipient: str = "") -> str:
    """Formats a message for chat logging and display."""
    time_str = datetime.now().strftime("%H:%M:%S")
    if is_private:
        return f"[{time_str}] (Private {sender} -> {recipient}): {message}"
    return f"[{time_str}] {sender}: {message}"
