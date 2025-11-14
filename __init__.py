"""Reminder Service - Context-aware reminder management with MCP integration.

This package provides both REST API and MCP server interfaces for managing reminders.

Features:
- Mobile number-based user identification
- Optional destination mobile for notifications
- DateTime-based due dates (not strings!)
- SQLite/PostgreSQL database storage
- Priority levels and status tracking
- Context metadata support
- Dual access: REST API and MCP server

Components:
- config: Application settings
- database: SQLAlchemy models and session management
- schemas: Pydantic validation schemas
- crud: Database CRUD operations
- api_server: FastAPI REST API
- mcp_server: MCP server with tools for AI agents

Usage:
    # Start REST API
    ./start_api.sh

    # Start MCP Server
    ./start_mcp.sh

    # Or run directly
    python api_server.py
    python mcp_server.py
"""

__version__ = "1.0.0"
__author__ = "Mayur"
__description__ = "Context-aware reminder service with MCP integration"
