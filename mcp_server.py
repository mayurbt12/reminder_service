"""MCP Server for Reminder Service.

This module provides MCP tools for AI agents to manage reminders.
Uses the same database as the REST API for data consistency.

IMPORTANT: Tools receive ISO datetime strings and convert to datetime objects.

Transport Support:
- stdio: Standard input/output (local process communication)
- sse: Server-Sent Events over HTTP (network access, scalable)
"""

from mcp.server.fastmcp import FastMCP
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import os
import crud
import database
from config import settings
from logger_config import setup_logger

logger = setup_logger(__name__, 'mcp.log')
logger.info("MCP Server initialized")

# Create FastMCP server with host and port from settings
mcp = FastMCP(
    "ReminderService",
    host=settings.MCP_HOST,
    port=settings.MCP_PORT
)


def parse_datetime_to_utc(datetime_str: str) -> datetime:
    """Parse ISO datetime string and convert to UTC.

    Handles multiple formats:
    - ISO with timezone: "2025-11-06T15:00:00+05:30" → converts to UTC
    - ISO with Z: "2025-11-06T15:00:00Z" → already UTC
    - Naive ISO: "2025-11-06T15:00:00" → assumes IST, converts to UTC

    Args:
        datetime_str: ISO format datetime string

    Returns:
        Timezone-aware datetime in UTC
    """
    logger.info(f"⏰ Received: {datetime_str}")

    # Parse ISO datetime (handle 'Z' as UTC marker)
    dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))

    # If naive (no timezone), assume Indian Standard Time (IST)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo('Asia/Kolkata'))

    # Convert to UTC for consistent storage
    dt_utc = dt.astimezone(timezone.utc)
    logger.info(f"⏰ Stored as: {dt_utc.isoformat()}")

    return dt_utc


@mcp.tool()
def create_reminder(
    user_mobile: str,
    title: str,
    due_datetime: str,
    destination_mobile: str = None,
    description: str = "",
    priority: str = "medium",
    context: dict = None
) -> str:
    """Create a new reminder for a user.

    Args:
        user_mobile: User's mobile number (e.g., "+1234567890")
        title: Reminder title
        due_datetime: When reminder is due - ISO format (e.g., "2025-10-26T15:00:00Z")
        destination_mobile: Optional destination mobile number for notification
        description: Optional detailed description
        priority: Priority level - "low", "medium", or "high" (default: "medium")
        context: Optional context dictionary with additional metadata

    Returns:
        Success message with reminder ID and due datetime, or error message
    """
    db = database.SessionLocal()
    try:
        logger.info(f"📝 Creating reminder: {title} | Due: {due_datetime}")

        # Parse ISO datetime string and convert to UTC
        due_dt = parse_datetime_to_utc(due_datetime)

        # Default destination_mobile to user_mobile if not provided
        if not destination_mobile:
            destination_mobile = user_mobile

        reminder_data = {
            'user_mobile': user_mobile,
            'destination_mobile': destination_mobile,
            'title': title,
            'description': description,
            'due_datetime': due_dt,  # datetime object
            'priority': priority,
            'context': context or {}
        }

        reminder = crud.create_reminder(db, reminder_data)
        return (
            f"✓ Reminder created successfully!\n"
            f"ID: {reminder.id}\n"
            f"Title: {reminder.title}\n"
            f"Due: {reminder.due_datetime.isoformat()}\n"
            f"Priority: {reminder.priority.value}"
        )
    except Exception as e:
        return f"✗ Error creating reminder: {str(e)}"
    finally:
        db.close()


@mcp.tool()
def list_reminders(
    user_mobile: str,
    status: str = None,
    limit: int = 50
) -> str:
    """List reminders for a user.

    Args:
        user_mobile: User's mobile number
        status: Optional status filter - "pending", "completed", or "cancelled"
        limit: Maximum number of results (default: 50, max: 1000)

    Returns:
        Formatted list of reminders or message if none found
    """
    db = database.SessionLocal()
    try:
        if limit > 1000:
            limit = 1000

        reminders = crud.get_reminders_by_user(db, user_mobile, status, limit)

        if not reminders:
            filter_text = f" with status '{status}'" if status else ""
            return f"No reminders found{filter_text}."

        result = [f"Found {len(reminders)} reminder(s):\n"]
        for r in reminders:
            due_str = r.due_datetime.strftime("%Y-%m-%d %H:%M %Z")
            result.append(
                f"\n• [{r.status.value.upper()}] {r.title}\n"
                f"  ID: {r.id}\n"
                f"  Due: {due_str}\n"
                f"  Priority: {r.priority.value}"
            )
            if r.description:
                result.append(f"  Description: {r.description}")
            if r.destination_mobile:
                result.append(f"  Destination: {r.destination_mobile}")

        return "\n".join(result)
    finally:
        db.close()


@mcp.tool()
def get_reminder(reminder_id: str, user_mobile: str) -> str:
    """Get detailed information about a specific reminder.

    Args:
        reminder_id: Reminder UUID
        user_mobile: User's mobile number

    Returns:
        Detailed reminder information or error message
    """
    db = database.SessionLocal()
    try:
        reminder = crud.get_reminder(db, reminder_id, user_mobile)
        if not reminder:
            return "✗ Reminder not found."

        return (
            f"Reminder Details:\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"ID: {reminder.id}\n"
            f"Title: {reminder.title}\n"
            f"Description: {reminder.description or 'N/A'}\n"
            f"Due: {reminder.due_datetime.isoformat()}\n"
            f"Priority: {reminder.priority.value}\n"
            f"Status: {reminder.status.value}\n"
            f"User Mobile: {reminder.user_mobile}\n"
            f"Destination Mobile: {reminder.destination_mobile or 'N/A'}\n"
            f"Recurrence: {reminder.recurrence or 'None'}\n"
            f"Created: {reminder.created_at.isoformat()}\n"
            f"Updated: {reminder.updated_at.isoformat()}\n"
            f"Context: {reminder.context if reminder.context else '{}'}"
        )
    finally:
        db.close()


@mcp.tool()
def update_reminder(
    reminder_id: str,
    user_mobile: str,
    title: str = None,
    due_datetime: str = None,
    description: str = None,
    priority: str = None,
    status: str = None,
    destination_mobile: str = None
) -> str:
    """Update an existing reminder.

    Args:
        reminder_id: Reminder UUID
        user_mobile: User's mobile number
        title: Optional new title
        due_datetime: Optional new due datetime - ISO format (e.g., "2025-10-27T16:00:00Z")
        description: Optional new description
        priority: Optional new priority - "low", "medium", or "high"
        status: Optional new status - "pending", "completed", or "cancelled"
        destination_mobile: Optional new destination mobile

    Returns:
        Success message with updated details or error message
    """
    db = database.SessionLocal()
    try:
        updates = {}
        if title:
            updates['title'] = title
        if description is not None:
            updates['description'] = description
        if priority:
            updates['priority'] = priority
        if status:
            updates['status'] = status
        if destination_mobile is not None:
            updates['destination_mobile'] = destination_mobile

        # Parse ISO datetime if provided and convert to UTC
        if due_datetime:
            logger.info(f"📝 Updating due_datetime: {due_datetime}")
            updates['due_datetime'] = parse_datetime_to_utc(due_datetime)

        reminder = crud.update_reminder(db, reminder_id, user_mobile, updates)
        if not reminder:
            return "✗ Reminder not found."

        return (
            f"✓ Reminder updated successfully!\n"
            f"ID: {reminder.id}\n"
            f"Title: {reminder.title}\n"
            f"Due: {reminder.due_datetime.isoformat()}\n"
            f"Status: {reminder.status.value}\n"
            f"Priority: {reminder.priority.value}"
        )
    except Exception as e:
        return f"✗ Error updating reminder: {str(e)}"
    finally:
        db.close()


@mcp.tool()
def delete_reminder(reminder_id: str, user_mobile: str) -> str:
    """Delete a reminder.

    Args:
        reminder_id: Reminder UUID
        user_mobile: User's mobile number

    Returns:
        Success or error message
    """
    db = database.SessionLocal()
    try:
        success = crud.delete_reminder(db, reminder_id, user_mobile)
        if success:
            return f"✓ Reminder {reminder_id} deleted successfully."
        else:
            return "✗ Reminder not found."
    finally:
        db.close()


@mcp.tool()
def check_due_reminders(user_mobile: str) -> str:
    """Check for reminders that are currently due.

    Args:
        user_mobile: User's mobile number

    Returns:
        List of reminders that are due now (where due_datetime <= current time)
    """
    db = database.SessionLocal()
    try:
        reminders = crud.get_due_reminders(db, user_mobile)

        if not reminders:
            return "No reminders due right now. ✓"

        result = [f"⏰ {len(reminders)} reminder(s) due now:\n"]
        for r in reminders:
            result.append(
                f"\n• {r.title}\n"
                f"  ID: {r.id}\n"
                f"  Due: {r.due_datetime.isoformat()}\n"
                f"  Priority: {r.priority.value}"
            )

        return "\n".join(result)
    finally:
        db.close()


@mcp.tool()
def search_reminders(user_mobile: str, query: str) -> str:
    """Search reminders by title or description.

    Args:
        user_mobile: User's mobile number
        query: Search term to match in title or description

    Returns:
        List of matching reminders or message if none found
    """
    db = database.SessionLocal()
    try:
        reminders = crud.search_reminders(db, user_mobile, query)

        if not reminders:
            return f"No reminders found matching '{query}'."

        result = [f"Found {len(reminders)} match(es) for '{query}':\n"]
        for r in reminders:
            due_str = r.due_datetime.strftime("%Y-%m-%d %H:%M")
            result.append(
                f"\n• {r.title}\n"
                f"  ID: {r.id}\n"
                f"  Due: {due_str}\n"
                f"  Status: {r.status.value}"
            )

        return "\n".join(result)
    finally:
        db.close()


if __name__ == "__main__":
    # Get transport from environment or config
    transport = os.getenv("MCP_TRANSPORT", settings.MCP_TRANSPORT).lower()

    if transport == "sse":
        # Run MCP server with SSE transport for network access
        # This allows remote connections and horizontal scaling
        host = settings.MCP_HOST
        port = settings.MCP_PORT

        print(f"Starting MCP server with SSE transport on {host}:{port}")
        print(f"SSE endpoint: http://{host}:{port}/sse")

        mcp.run(transport="sse")
    else:
        # Run MCP server with stdio transport for local process communication
        print("Starting MCP server with stdio transport")
        mcp.run(transport="stdio")
