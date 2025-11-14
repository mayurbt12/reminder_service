"""FastAPI REST API server for Reminder Service.

This module provides HTTP endpoints for managing reminders.
Designed for frontend/external application access.

IMPORTANT: Pydantic automatically converts ISO datetime strings to datetime objects.
"""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional

import crud
import schemas
import database
from config import settings
from logger_config import setup_logger

logger = setup_logger(__name__, 'api.log')

# Create FastAPI application
app = FastAPI(
    title="Reminder Service API",
    description="Context-aware reminder service with mobile-based user identification and datetime storage",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Allow your frontend origin
origins = [
    "http://localhost:1800",      # OneCall frontend (default)
    "http://localhost:3000",      # Alternative frontend port
    "http://3.6.152.132:3000",    # Public IP for your frontend
    "http://3.6.152.132:1800",    # Public IP for OneCall frontend
]

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Root endpoint - service information"""
    return {
        "service": "Reminder Service API",
        "version": "1.0.0",
        "status": "healthy",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "reminders": "/reminders"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "reminder_service",
        "database": settings.DATABASE_URL.split("://")[0]
    }


@app.post("/reminders", response_model=schemas.ReminderResponse, status_code=201)
def create_reminder(
    reminder: schemas.ReminderCreate,
    db: Session = Depends(database.get_db)
):
    """Create a new reminder.

    Request body example:
    ```json
    {
        "user_mobile": "+1234567890",
        "title": "Doctor Appointment",
        "due_datetime": "2025-10-26T15:00:00Z",
        "description": "Annual checkup",
        "priority": "high",
        "destination_mobile": "+9876543210",
        "context": {"location": "123 Main St"}
    }
    ```

    Pydantic automatically parses ISO datetime string to datetime object.
    """
    try:
        # Pydantic has already validated and converted due_datetime to datetime object
        reminder_data = reminder.model_dump()
        return crud.create_reminder(db, reminder_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating reminder: {str(e)}")


@app.get("/reminders", response_model=List[schemas.ReminderResponse])
def list_reminders(
    user_mobile: str = Query(..., description="User's mobile number"),
    status: Optional[str] = Query(None, pattern="^(pending|completed|cancelled)$", description="Filter by status"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of results"),
    db: Session = Depends(database.get_db)
):
    """List all reminders for a user.

    Query parameters:
    - user_mobile: Required - User's mobile number
    - status: Optional - Filter by status (pending, completed, cancelled)
    - limit: Optional - Maximum results (1-1000, default 50)

    Returns list of reminders with datetime objects (serialized to ISO in JSON).
    """
    return crud.get_reminders_by_user(db, user_mobile, status, limit)


@app.get("/reminders/due/now", response_model=List[schemas.ReminderResponse])
def check_due_reminders(
    user_mobile: str = Query(..., description="User's mobile number"),
    db: Session = Depends(database.get_db)
):
    """Get all reminders that are currently due.

    Returns pending reminders where due_datetime <= current time.
    Uses datetime comparison internally.
    """
    return crud.get_due_reminders(db, user_mobile)


@app.get("/reminders/search", response_model=List[schemas.ReminderResponse])
def search_reminders(
    user_mobile: str = Query(..., description="User's mobile number"),
    query: str = Query(..., min_length=1, description="Search query"),
    db: Session = Depends(database.get_db)
):
    """Search reminders by title or description.

    Query parameters:
    - user_mobile: User's mobile number
    - query: Search term to match in title or description

    Returns matching reminders with datetime objects.
    """
    return crud.search_reminders(db, user_mobile, query)


@app.get("/reminders/{reminder_id}", response_model=schemas.ReminderResponse)
def get_reminder(
    reminder_id: str,
    user_mobile: str = Query(..., description="User's mobile number"),
    db: Session = Depends(database.get_db)
):
    """Get a specific reminder by ID.

    Path parameters:
    - reminder_id: Reminder UUID

    Query parameters:
    - user_mobile: User's mobile number (for security)

    Returns reminder with datetime objects (serialized to ISO in JSON).
    """
    reminder = crud.get_reminder(db, reminder_id, user_mobile)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder


@app.put("/reminders/{reminder_id}", response_model=schemas.ReminderResponse)
def update_reminder(
    reminder_id: str,
    user_mobile: str = Query(..., description="User's mobile number"),
    updates: schemas.ReminderUpdate = ...,
    db: Session = Depends(database.get_db)
):
    """Update an existing reminder.

    Request body example:
    ```json
    {
        "title": "Updated Title",
        "due_datetime": "2025-10-27T16:00:00Z",
        "status": "completed"
    }
    ```

    Only provided fields will be updated.
    Pydantic automatically converts due_datetime from ISO string to datetime object.
    """
    try:
        # Pydantic has already validated and converted datetime
        update_dict = updates.model_dump(exclude_unset=True)
        reminder = crud.update_reminder(db, reminder_id, user_mobile, update_dict)
        if not reminder:
            raise HTTPException(status_code=404, detail="Reminder not found")
        return reminder
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating reminder: {str(e)}")


@app.delete("/reminders/{reminder_id}", status_code=200)
def delete_reminder(
    reminder_id: str,
    user_mobile: str = Query(..., description="User's mobile number"),
    db: Session = Depends(database.get_db)
):
    """Delete a reminder.

    Path parameters:
    - reminder_id: Reminder UUID

    Query parameters:
    - user_mobile: User's mobile number (for security)
    """
    success = crud.delete_reminder(db, reminder_id, user_mobile)
    if not success:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"message": "Reminder deleted successfully", "reminder_id": reminder_id}


@app.get("/reminders/stats/{user_mobile}")
def get_user_stats(
    user_mobile: str,
    db: Session = Depends(database.get_db)
):
    """Get statistics for a user's reminders.

    Returns counts by status and total count.
    """
    total = crud.get_reminders_count(db, user_mobile)
    pending = len(crud.get_reminders_by_user(db, user_mobile, "pending", 10000))
    completed = len(crud.get_reminders_by_user(db, user_mobile, "completed", 10000))
    cancelled = len(crud.get_reminders_by_user(db, user_mobile, "cancelled", 10000))
    due_now = len(crud.get_due_reminders(db, user_mobile))

    return {
        "user_mobile": user_mobile,
        "total": total,
        "by_status": {
            "pending": pending,
            "completed": completed,
            "cancelled": cancelled
        },
        "due_now": due_now
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="info"
    )
