"""
backend/database/models.py – HMS SQLAlchemy ORM models.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, Index, String, Text
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


class ClinicalTask(Base):
    __tablename__ = "clinical_tasks"

    id = Column(String, primary_key=True)
    title = Column(String(255), nullable=False)
    patient_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="todo", index=True)
    priority = Column(String(10), nullable=False, default="medium", index=True)
    due_date = Column(DateTime, nullable=True)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (Index("ix_ctasks_status_priority", "status", "priority"),)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "patient_name": self.patient_name,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "tags": self.tags or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
        }


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(String, primary_key=True)
    patient_name = Column(String(255), nullable=False)
    doctor_name = Column(String(255), nullable=False)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    location = Column(String(500), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (Index("ix_appt_time_range", "start_time", "end_time"),)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "patient_name": self.patient_name,
            "doctor_name": self.doctor_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "location": self.location,
            "reason": self.reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PatientRecord(Base):
    __tablename__ = "patient_records"

    id = Column(String, primary_key=True)
    patient_name = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(JSON, default=list)
    is_pinned = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    if HAS_PGVECTOR:
        embedding = Column(Vector(768), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "patient_name": self.patient_name,
            "content": self.content,
            "tags": self.tags or [],
            "is_pinned": self.is_pinned or False,
            "created_at": self.created_at.isoformat() if self.created_at else None,
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
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "agent_name": self.agent_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
