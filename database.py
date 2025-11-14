"""Database module for Reminder Service.

This module defines SQLAlchemy models and database session management.
IMPORTANT: due_datetime is stored as DateTime object, NOT string.
"""

from sqlalchemy import create_engine, Column, String, DateTime, JSON, Enum as SQLEnum, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
import enum

from config import settings

# SQLAlchemy Base
Base = declarative_base()


class PriorityEnum(enum.Enum):
    """Priority levels for reminders"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StatusEnum(enum.Enum):
    """Status values for reminders"""
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Reminder(Base):
    """Reminder model - stores all reminder data.

    CRITICAL: All datetime fields (due_datetime, created_at, updated_at)
    are DateTime objects with timezone support, NOT strings.
    """

    __tablename__ = "reminders"

    # Primary Key
    id = Column(String, primary_key=True, doc="Unique reminder ID (UUID)")

    # User Identification
    user_mobile = Column(String, nullable=False, index=True, doc="User's mobile number")
    destination_mobile = Column(String, nullable=True, doc="Optional destination mobile number")

    # Reminder Content
    title = Column(String, nullable=False, doc="Reminder title")
    description = Column(String, default="", doc="Optional detailed description")

    # CRITICAL: DateTime object, NOT string!
    due_datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="When the reminder is due (timezone-aware datetime object)"
    )

    # Metadata
    priority = Column(SQLEnum(PriorityEnum), default=PriorityEnum.MEDIUM, doc="Priority level")
    status = Column(SQLEnum(StatusEnum), default=StatusEnum.PENDING, index=True, doc="Current status")
    context = Column(JSON, default={}, doc="Additional context as JSON dictionary")
    recurrence = Column(String, nullable=True, doc="Optional recurrence pattern")

    # Timestamps - CRITICAL: DateTime objects, NOT strings!
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="When reminder was created (timezone-aware)"
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="When reminder was last updated (timezone-aware)"
    )

    # Composite indexes for query performance
    __table_args__ = (
        Index('idx_user_status', 'user_mobile', 'status'),
        Index('idx_due_datetime', 'due_datetime'),
        Index('idx_user_due', 'user_mobile', 'due_datetime'),
    )

    def __repr__(self):
        """String representation"""
        return (
            f"<Reminder(id={self.id}, user={self.user_mobile}, "
            f"title={self.title}, due={self.due_datetime}, status={self.status.value})>"
        )


# Database Engine Setup
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False  # Set to True for SQL debugging
)

# Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Database session dependency for FastAPI.

    Yields:
        Session: SQLAlchemy database session

    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            # Use db here
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create all tables
Base.metadata.create_all(bind=engine)
