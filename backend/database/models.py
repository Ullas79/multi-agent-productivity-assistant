"""
backend/database/models.py – SQLAlchemy ORM models for AgentFlow.

Optimised for AlloyDB (PostgreSQL-compatible) with indexes on
frequently-queried columns.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, Index
from sqlalchemy.orm import DeclarativeBase

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    Vector = None
    HAS_PGVECTOR = False


class Base(DeclarativeBase):
    pass


def _utcnow():
    return datetime.now(timezone.utc)


class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="todo", index=True)
    priority = Column(String(10), nullable=False, default="medium", index=True)
    due_date = Column(DateTime, nullable=True)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Composite index for common filtered queries on AlloyDB
    __table_args__ = (
        Index("ix_tasks_status_priority", "status", "priority"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "tags": self.tags or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    id = Column(String, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    location = Column(String(500), nullable=True)
    attendees = Column(JSON, default=list)
    is_recurring = Column(Boolean, default=False)
    recurrence_rule = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # Composite index for time-range queries on AlloyDB
    __table_args__ = (
        Index("ix_events_time_range", "start_time", "end_time"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "location": self.location,
            "attendees": self.attendees or [],
            "is_recurring": self.is_recurring or False,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Note(Base):
    __tablename__ = "notes"
    id = Column(String, primary_key=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(JSON, default=list)
    is_pinned = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    if HAS_PGVECTOR:
        embedding = Column(Vector(768), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "content": self.content,
            "tags": self.tags or [], "is_pinned": self.is_pinned or False,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AgentMemory(Base):
    __tablename__ = "agent_memory"
    id = Column(String, primary_key=True)
    session_id = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    agent_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "session_id": self.session_id, "role": self.role,
            "content": self.content, "agent_name": self.agent_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }