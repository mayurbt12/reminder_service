"""CRUD operations for Reminder Service.

This module provides database operations for reminders.
IMPORTANT: All datetime parameters and return values are datetime objects, NOT strings.
"""

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import List, Optional
import uuid
from datetime import datetime, timezone

from database import Reminder, StatusEnum, PriorityEnum
from logger_config import setup_logger

logger = setup_logger(__name__, 'crud.log')


def create_reminder(db: Session, reminder_data: dict) -> Reminder:
    """Create a new reminder in the database.

    Args:
        db: Database session
        reminder_data: Dictionary with reminder fields
            - user_mobile: str
            - title: str
            - due_datetime: datetime (MUST be datetime object!)
            - destination_mobile: Optional[str]
            - description: Optional[str]
            - priority: Optional[str]
            - context: Optional[dict]
            - recurrence: Optional[str]

    Returns:
        Reminder: Created reminder object with datetime fields

    Raises:
        SQLAlchemyError: On database errors
    """
    reminder_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Convert string priority to enum if needed
    priority = reminder_data.get('priority', 'medium')
    if isinstance(priority, str):
        priority = PriorityEnum[priority.upper()]

    # Default destination_mobile to user_mobile if not provided
    destination_mobile = reminder_data.get('destination_mobile')
    if not destination_mobile:
        destination_mobile = reminder_data['user_mobile']

    # Ensure due_datetime has UTC timezone
    due_dt = reminder_data['due_datetime']
    if due_dt.tzinfo is None:
        due_dt = due_dt.replace(tzinfo=timezone.utc)

    db_reminder = Reminder(
        id=reminder_id,
        user_mobile=reminder_data['user_mobile'],
        destination_mobile=destination_mobile,
        title=reminder_data['title'],
        description=reminder_data.get('description', ''),
        due_datetime=due_dt,  # MUST be datetime object with UTC timezone!
        priority=priority,
        status=StatusEnum.PENDING,
        context=reminder_data.get('context', {}),
        recurrence=reminder_data.get('recurrence'),
        created_at=now,  # datetime object
        updated_at=now   # datetime object
    )

    db.add(db_reminder)
    db.commit()
    db.refresh(db_reminder)
    return db_reminder


def get_reminders_by_user(
    db: Session,
    user_mobile: str,
    status: Optional[str] = None,
    limit: int = 50
) -> List[Reminder]:
    """Get reminders for a specific user.

    Args:
        db: Database session
        user_mobile: User's mobile number
        status: Optional status filter (pending, completed, cancelled)
        limit: Maximum number of results (default: 50)

    Returns:
        List[Reminder]: List of reminder objects with datetime fields
    """
    query = db.query(Reminder).filter(Reminder.user_mobile == user_mobile)

    if status:
        status_enum = StatusEnum[status.upper()]
        query = query.filter(Reminder.status == status_enum)

    return query.order_by(Reminder.due_datetime.desc()).limit(limit).all()


def get_reminder(db: Session, reminder_id: str, user_mobile: str) -> Optional[Reminder]:
    """Get a specific reminder by ID.

    Args:
        db: Database session
        reminder_id: Reminder UUID
        user_mobile: User's mobile number (for security)

    Returns:
        Optional[Reminder]: Reminder object if found, None otherwise
    """
    return db.query(Reminder).filter(
        Reminder.id == reminder_id,
        Reminder.user_mobile == user_mobile
    ).first()


def update_reminder(
    db: Session,
    reminder_id: str,
    user_mobile: str,
    updates: dict
) -> Optional[Reminder]:
    """Update an existing reminder.

    Args:
        db: Database session
        reminder_id: Reminder UUID
        user_mobile: User's mobile number (for security)
        updates: Dictionary of fields to update
            - due_datetime: datetime (if provided, MUST be datetime object!)
            - title, description, priority, status, etc.

    Returns:
        Optional[Reminder]: Updated reminder object if found, None otherwise

    Raises:
        SQLAlchemyError: On database errors
    """
    reminder = get_reminder(db, reminder_id, user_mobile)
    if not reminder:
        return None

    # Store original due_datetime for comparison
    original_due_datetime = reminder.due_datetime

    # Update fields
    for key, value in updates.items():
        if value is not None:
            # Convert string enums to enum objects
            if key == 'priority' and isinstance(value, str):
                value = PriorityEnum[value.upper()]
            elif key == 'status' and isinstance(value, str):
                value = StatusEnum[value.upper()]
            # Ensure due_datetime has UTC timezone
            elif key == 'due_datetime' and isinstance(value, datetime) and value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)

            setattr(reminder, key, value)

            # CRITICAL: Flag JSON columns as modified for SQLAlchemy change tracking
            # Without this, in-place dict modifications are not detected!
            if key == 'context':
                flag_modified(reminder, 'context')

    # Clear context if due_datetime was updated to a different future time
    if 'due_datetime' in updates and updates['due_datetime'] is not None:
        new_due_datetime = reminder.due_datetime  # Already updated by setattr above
        now = datetime.now(timezone.utc)
        # If rescheduled to future time and it's different from original
        if new_due_datetime > now and new_due_datetime != original_due_datetime:
            reminder.context = {}
            flag_modified(reminder, 'context')

    # Update timestamp
    reminder.updated_at = datetime.now(timezone.utc)  # datetime object
    
    db.commit()
    db.refresh(reminder)
    return reminder


def delete_reminder(db: Session, reminder_id: str, user_mobile: str) -> bool:
    """Delete a reminder.

    Args:
        db: Database session
        reminder_id: Reminder UUID
        user_mobile: User's mobile number (for security)

    Returns:
        bool: True if deleted, False if not found
    """
    reminder = get_reminder(db, reminder_id, user_mobile)
    if not reminder:
        return False

    db.delete(reminder)
    db.commit()
    return True


def get_due_reminders(db: Session, user_mobile: str) -> List[Reminder]:
    """Get all pending reminders that are currently due.

    Args:
        db: Database session
        user_mobile: User's mobile number

    Returns:
        List[Reminder]: List of due reminders (datetime comparison)
    """
    now = datetime.now(timezone.utc)  # datetime object
    return db.query(Reminder).filter(
        Reminder.user_mobile == user_mobile,
        Reminder.status == StatusEnum.PENDING,
        Reminder.due_datetime <= now  # Comparing datetime objects
    ).order_by(Reminder.due_datetime).all()


def search_reminders(db: Session, user_mobile: str, query: str) -> List[Reminder]:
    """Search reminders by title or description.

    Args:
        db: Database session
        user_mobile: User's mobile number
        query: Search string

    Returns:
        List[Reminder]: List of matching reminders
    """
    search_pattern = f"%{query}%"
    return db.query(Reminder).filter(
        Reminder.user_mobile == user_mobile,
        (
            Reminder.title.like(search_pattern) |
            Reminder.description.like(search_pattern)
        )
    ).order_by(Reminder.due_datetime.desc()).all()


def get_reminders_count(db: Session, user_mobile: str) -> int:
    """Get total number of reminders for a user.

    Args:
        db: Database session
        user_mobile: User's mobile number

    Returns:
        int: Total count of reminders
    """
    return db.query(Reminder).filter(
        Reminder.user_mobile == user_mobile
    ).count()


def get_due_reminders_for_calls(db: Session) -> List[Reminder]:
    """Get pending reminders that are due and eligible for outgoing calls.

    This function returns reminders that meet ALL of the following criteria:
    - Status is PENDING
    - due_datetime is less than or equal to current time
    - destination_mobile is not None (has a phone number to call)
    - Has NOT been processed yet (context doesn't contain 'call_initiated')

    Args:
        db: Database session

    Returns:
        List[Reminder]: List of reminders eligible for outgoing calls
    """
    now = datetime.now(timezone.utc)

    # Get all pending reminders that are due and have a destination mobile
    all_due = db.query(Reminder).filter(
        Reminder.status == StatusEnum.PENDING,
        Reminder.due_datetime <= now,
        Reminder.destination_mobile.isnot(None)
    ).all()

    # Filter out reminders that have already been processed or permanently failed
    # Exclude if:
    # - call_initiated is True (successfully called)
    # - call_failed is True (failed after 3 retries)
    eligible_reminders = []
    for reminder in all_due:
        context = reminder.context or {}

        # Skip if call already initiated successfully
        if context.get('call_initiated', False):
            continue

        # Skip if call permanently failed (3+ attempts)
        if context.get('call_failed', False):
            # Log when we skip a failed reminder
            logger.info(f"[FILTER DEBUG] Skipping reminder {reminder.id} - call_failed=True in context")
            continue

        # Include reminder (no attempts yet OR retry count < 3)
        eligible_reminders.append(reminder)

    return eligible_reminders
