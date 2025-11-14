"""Configuration module for Reminder Service.

This module provides configuration settings using Pydantic Settings.
Environment variables can be used to override default values.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings for Reminder Service.

    All settings can be overridden via environment variables.
    Example: export DATABASE_URL="postgresql://..."
    """

    # Database Configuration
    DATABASE_URL: str = "sqlite:///./reminders.db"
    """Database connection URL. Default: SQLite file in current directory"""

    # API Server Configuration
    API_HOST: str = "0.0.0.0"
    """API server host address"""

    API_PORT: int = 8005
    """API server port (unique to avoid conflicts)"""

    # MCP Server Configuration
    MCP_HOST: str = "127.0.0.1"
    """MCP server host address"""

    MCP_PORT: int = 8006
    """MCP server port for SSE transport (separate from REST API)"""

    MCP_TRANSPORT: str = "sse"
    """MCP transport type: 'stdio' for local, 'sse' for network access"""

    # General Configuration
    TIMEZONE: str = "UTC"
    """Default timezone for datetime operations"""

    MAX_REMINDERS_PER_USER: int = 1000
    """Maximum number of reminders allowed per user"""

    # Background Worker Configuration
    WORKER_ENABLED: bool = True
    """Enable/disable background worker for outgoing calls"""

    WORKER_CHECK_INTERVAL: int = 60
    """Interval in seconds for checking due reminders (default: 60 seconds)"""

    OUTGOING_CALL_API_URL: str = "http://127.0.0.1:1801"
    """Base URL for OneCall API (default backend port 1801)"""

    class Config:
        """Pydantic config"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
