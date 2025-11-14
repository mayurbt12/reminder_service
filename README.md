# Reminder Service - MCP Server Implementation

A reliable, intelligent, and context-aware Reminder Service that integrates seamlessly with Model Context Protocol (MCP) clients and provides a REST API for frontend applications.

## Features

✓ **Mobile-based User Identification**: User mobile number as primary ID
✓ **Optional Destination Mobile**: Send reminders to different numbers
✓ **DateTime Storage**: Proper datetime objects (not strings!) throughout
✓ **Database Persistence**: SQLite with SQLAlchemy ORM
✓ **Dual Access**: Both REST API and MCP server interfaces
✓ **Context-Aware**: Store additional metadata with each reminder
✓ **Priority Levels**: Low, medium, high
✓ **Status Tracking**: Pending, completed, cancelled
✓ **Full CRUD**: Create, read, update, delete operations
✓ **Search**: Find reminders by title or description

## Architecture

```
reminder_service/
├── config.py              # Settings and configuration
├── database.py            # SQLAlchemy models (DateTime columns)
├── schemas.py             # Pydantic validation schemas
├── crud.py                # Database CRUD operations
├── api_server.py          # FastAPI REST API (port 8001)
├── mcp_server.py          # MCP server (stdio transport)
├── start_api.sh           # Start REST API
├── start_mcp.sh           # Start MCP server
├── requirements.txt       # Python dependencies
└── reminders.db           # SQLite database (auto-created)
```

## Quick Start

### 1. Install Dependencies

```bash
cd /home/mayurbt/PycharmProjects/one_call/one_call_demo/mcp_Servers/reminder_service
pip install -r requirements.txt
```

### 2. Start the REST API

```bash
./start_api.sh
```

API will be available at: `http://127.0.0.1:8005`
API Documentation: `http://127.0.0.1:8005/docs`

### 3. Start the MCP Server

```bash
./start_mcp.sh
```

MCP server runs in stdio mode for AI agent integration.

### 4. Run Tests

```bash
python3 test_reminder.py
```

## REST API Usage

### Create a Reminder

```bash
curl -X POST http://127.0.0.1:8005/reminders \
  -H "Content-Type: application/json" \
  -d '{
    "user_mobile": "+1234567890",
    "title": "Doctor Appointment",
    "due_datetime": "2025-10-26T15:00:00Z",
    "description": "Annual checkup",
    "priority": "high",
    "destination_mobile": "+9876543210",
    "context": {"location": "123 Main St"}
  }'
```

### List Reminders

```bash
curl "http://127.0.0.1:8005/reminders?user_mobile=+1234567890&status=pending"
```

### Get Specific Reminder

```bash
curl "http://127.0.0.1:8005/reminders/{reminder_id}?user_mobile=+1234567890"
```

### Update Reminder

```bash
curl -X PUT "http://127.0.0.1:8005/reminders/{reminder_id}?user_mobile=+1234567890" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "due_datetime": "2025-10-27T16:00:00Z",
    "status": "completed"
  }'
```

### Delete Reminder

```bash
curl -X DELETE "http://127.0.0.1:8005/reminders/{reminder_id}?user_mobile=+1234567890"
```

### Check Due Reminders

```bash
curl "http://127.0.0.1:8005/reminders/due/now?user_mobile=+1234567890"
```

### Search Reminders

```bash
curl "http://127.0.0.1:8005/reminders/search?user_mobile=+1234567890&query=meeting"
```

## MCP Server Usage

The MCP server is registered in the main MCP registry and provides these tools:

1. **create_reminder** - Create a new reminder
2. **list_reminders** - List reminders for a user
3. **get_reminder** - Get specific reminder details
4. **update_reminder** - Update an existing reminder
5. **delete_reminder** - Delete a reminder
6. **check_due_reminders** - Get reminders that are due now
7. **search_reminders** - Search reminders by title/description

### Example MCP Tool Calls

```python
# Create reminder
create_reminder(
    user_mobile="+1234567890",
    title="Team Meeting",
    due_datetime="2025-10-26T15:00:00Z",
    priority="high"
)

# List reminders
list_reminders(
    user_mobile="+1234567890",
    status="pending",
    limit=10
)

# Check due reminders
check_due_reminders(user_mobile="+1234567890")
```

## DateTime Handling

**IMPORTANT**: All datetime fields are datetime objects, NOT strings!

**Input**: ISO format datetime strings
**Processing**: Pydantic auto-parses to datetime objects
**Storage**: SQLite DateTime column stores datetime objects
**Output**: JSON serializes to ISO format strings

Example:
```json
{
  "due_datetime": "2025-10-26T15:00:00Z",  // Input/Output
  // Internally stored as datetime.datetime(2025, 10, 26, 15, 0, 0, tzinfo=timezone.utc)
}
```

## Database Schema

```sql
CREATE TABLE reminders (
    id TEXT PRIMARY KEY,
    user_mobile TEXT NOT NULL,
    destination_mobile TEXT,
    title TEXT NOT NULL,
    description TEXT,
    due_datetime DATETIME NOT NULL,  -- DateTime object!
    priority TEXT,
    status TEXT,
    context JSON,
    recurrence TEXT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
```

## Configuration

Edit `config.py` or use environment variables:

```bash
export DATABASE_URL="sqlite:///./reminders.db"
export API_HOST="127.0.0.1"
export API_PORT="8005"
export TIMEZONE="UTC"
export MAX_REMINDERS_PER_USER="1000"
```

## Frontend Integration

The REST API is CORS-enabled and ready for frontend integration:

- **Base URL**: `http://127.0.0.1:8005`
- **API Docs**: `http://127.0.0.1:8005/docs`
- **Health Check**: `http://127.0.0.1:8005/health`

All responses use ISO datetime format for easy JavaScript parsing:
```javascript
const reminder = await fetch('http://127.0.0.1:8005/reminders/...');
const data = await reminder.json();
const dueDate = new Date(data.due_datetime);  // Auto-parsed!
```

## Testing

Run the comprehensive test suite:

```bash
python3 test_reminder.py
```

Tests verify:
- ✓ Reminder creation with datetime objects
- ✓ List and retrieve operations
- ✓ Update operations
- ✓ Search functionality
- ✓ Due reminder checks
- ✓ Delete operations
- ✓ DateTime type validation

## MCP Integration

The service is registered in:
```
one_call/tutor/modules/mcp/mcp_servers_registry.json
```

Enabled by default and ready for AI agent integration through the main application's MCP connection manager.

## Troubleshooting

### Database locked error
If you get "database is locked", ensure only one process accesses the database at a time.

### Port already in use
Change API_PORT in config.py if port 8005 is already in use.

### DateTime parsing errors
Ensure datetime strings are in ISO format: `YYYY-MM-DDTHH:MM:SSZ` or with timezone: `YYYY-MM-DDTHH:MM:SS+HH:MM`

## Development

### Project Structure
- Simple, clean architecture
- No custom date parsing needed (Pydantic handles it)
- Consistent datetime handling throughout
- Database-backed for reliability
- Dual interfaces for flexibility

### Future Enhancements
- Notification system (SMS, email)
- Recurring reminders
- Reminder groups
- Time zone support per user
- Push notifications
- Reminder templates

## License

Part of the OneCall voice calling system.

## Author

Mayur - Built with FastMCP and FastAPI
