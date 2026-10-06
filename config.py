"""
Configuration settings for the TCP Chat Application.
Computer Networks Lab (CNL) Project.
"""

# Network Connection Settings
DEFAULT_HOST = "127.0.0.1"  # Localhost (use "0.0.0.0" on server to listen on all interfaces)
DEFAULT_PORT = 5555         # Default listening port
BUFFER_SIZE = 4096          # Socket receive buffer size in bytes
ENCODING = "utf-8"          # Text encoding for socket transmission

# Administrative Credentials
ADMIN_NICKNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"

# System File Paths
LOG_DIR = "logs"
SERVER_LOG_FILE = "logs/server.log"
CHAT_LOG_FILE = "logs/chat_history.log"
BAN_LIST_FILE = "banned_users.json"

# Operational Limits
MAX_NICKNAME_LENGTH = 20
MAX_MESSAGE_LENGTH = 1000
MAX_QUEUED_CONNECTIONS = 10
