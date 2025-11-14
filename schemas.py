"""Pydantic schemas for Reminder Service.

This module defines request and response schemas for API validation.
IMPORTANT: Pydantic automatically parses ISO datetime strings to datetime objects.
"""

from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional, Dict


class ReminderCreate(BaseModel):
    """Schema for creating a new reminder.

    Pydantic automatically validates and parses:
    - ISO datetime strings to datetime objects
    - Mobile number format
    - Priority and other enums
    """

    user_mobile: str = Field(
        ...,
        pattern=r'^\+?[1-9]\d{1,14}$',
        description="User's mobile number (E.164 format, e.g., +1234567890)",
        examples=["+1234567890", "+919876543210"]
    )

    destination_mobile: Optional[str] = Field(
        None,
        pattern=r'^\+?[1-9]\d{1,14}$',
        description="Optional destination mobile number for notification"
    )

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Reminder title",
        examples=["Doctor Appointment", "Team Meeting"]
    )

    description: Optional[str] = Field(
        default="",
        description="Optional detailed description"
    )

    # IMPORTANT: Pydantic auto-parses ISO datetime strings to datetime object!
    # Examples: "2025-10-26T15:00:00Z", "2025-10-26T15:00:00+05:30"
    due_datetime: datetime = Field(
        ...,
        description="When the reminder is due (ISO 8601 format)",
        examples=["2025-10-26T15:00:00Z", "2025-10-26T15:00:00+05:30"]
    )

    priority: str = Field(
        default="medium",
        pattern="^(low|medium|high)$",
        description="Priority level: low, medium, or high"
    )

    recurrence: Optional[str] = Field(
        None,
        description="Optional recurrence pattern (e.g., 'daily', 'weekly')"
    )

    context: Optional[Dict] = Field(
        default_factory=dict,
        description="Additional context as key-value pairs"
    )


class ReminderUpdate(BaseModel):
    """Schema for updating an existing reminder.

    All fields are optional - only provided fields will be updated.
    """

    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Updated reminder title"
    )

    description: Optional[str] = Field(
        None,
        description="Updated description"
    )

    # Pydantic auto-parses ISO datetime to datetime object
    due_datetime: Optional[datetime] = Field(
        None,
        description="Updated due datetime (ISO 8601 format)"
    )

    destination_mobile: Optional[str] = Field(
        None,
        pattern=r'^\+?[1-9]\d{1,14}$',
        description="Updated destination mobile"
    )

    priority: Optional[str] = Field(
        None,
        pattern="^(low|medium|high)$",
        description="Updated priority level"
    )

    status: Optional[str] = Field(
        None,
        pattern="^(pending|completed|cancelled)$",
        description="Updated status"
    )

    context: Optional[Dict] = Field(
        None,
        description="Updated context dictionary"
    )


class ReminderResponse(BaseModel):
    """Schema for reminder responses.

    CRITICAL: datetime fields are datetime objects that get
    automatically serialized to ISO strings in JSON responses.
    """

    id: str = Field(..., description="Unique reminder ID")
    user_mobile: str = Field(..., description="User's mobile number")
    destination_mobile: Optional[str] = Field(None, description="Destination mobile number")
    title: str = Field(..., description="Reminder title")
    description: str = Field(..., description="Reminder description")

    # CRITICAL: This is a datetime object, automatically serialized to ISO string in JSON
    due_datetime: datetime = Field(..., description="When the reminder is due")

    priority: str = Field(..., description="Priority level")
    status: str = Field(..., description="Current status")
    context: Dict = Field(..., description="Additional context")
    recurrence: Optional[str] = Field(None, description="Recurrence pattern")

    # CRITICAL: These are also datetime objects
    created_at: datetime = Field(..., description="When the reminder was created")
    updated_at: datetime = Field(..., description="When the reminder was last updated")

    class Config:
        """Pydantic configuration"""
        from_attributes = True  # Enable ORM mode for SQLAlchemy models

        # CRITICAL: Ensure all datetime fields include UTC timezone in JSON responses
        # This prevents JavaScript from misinterpreting datetime as local time
        json_encoders = {
            datetime: lambda v: (
                v.replace(tzinfo=timezone.utc).isoformat()
                if v and not v.tzinfo
                else v.isoformat()
            ) if v else None
        }

        json_schema_extra = {
            "example": {
                "id": "abc-123-def-456",
                "user_mobile": "+1234567890",
                "destination_mobile": "+9876543210",
                "title": "Doctor Appointment",
                "description": "Annual checkup with Dr. Smith",
                "due_datetime": "2025-10-26T15:00:00+00:00",
                "priority": "high",
                "status": "pending",
                "context": {"location": "123 Main St", "doctor": "Dr. Smith"},
                "recurrence": None,
                "created_at": "2025-10-25T10:30:00+00:00",
                "updated_at": "2025-10-25T10:30:00+00:00"
            }
        }
