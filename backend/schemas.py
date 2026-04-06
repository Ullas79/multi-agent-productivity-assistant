"""
backend/schemas.py – Pydantic v2 schemas for request validation and response serialisation.
Hospital Management System (HMS) Edition
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ── Chat ──────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = Field(None, description="Continue an existing session")

    @field_validator("message")
    @classmethod
    def strip_message(cls, v: str) -> str:
        return v.strip()


class ChatChunk(BaseModel):
    type: str
    content: Optional[str] = None
    session_id: Optional[str] = None


class SessionHistory(BaseModel):
    session_id: str
    messages: List[dict]


# ── Clinical Tasks ────────────────────────────────────────────────────────────
VALID_PRIORITIES = {"low", "medium", "high"}
VALID_STATUSES = {"todo", "in_progress", "done"}


class ClinicalTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    patient_name: Optional[str] = Field(None, max_length=255)
    description: str = Field("", max_length=5000)
    priority: str = Field("medium", pattern="^(low|medium|high)$")
    due_date: Optional[str] = Field(None, description="ISO 8601 datetime")
    tags: Optional[List[str]] = Field(default_factory=list)

    @field_validator("tags", mode="before")
    @classmethod
    def clean_tags(cls, v):
        if v is None:
            return []
        return [t.strip().lower() for t in v if t.strip()]


class ClinicalTaskUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    patient_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    status: Optional[str] = Field(None, pattern="^(todo|in_progress|done)$")
    priority: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    due_date: Optional[str] = None
    tags: Optional[List[str]] = None


class ClinicalTaskResponse(BaseModel):
    id: str
    title: str
    patient_name: Optional[str]
    description: Optional[str]
    status: str
    priority: str
    due_date: Optional[str]
    tags: List[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    completed_at: Optional[str]


# ── Appointments ──────────────────────────────────────────────────────────────
class AppointmentCreate(BaseModel):
    patient_name: str = Field(..., min_length=1, max_length=255)
    doctor_name: str = Field(..., min_length=1, max_length=255)
    start_time: str = Field(..., description="ISO 8601 datetime")
    end_time: str = Field(..., description="ISO 8601 datetime")
    reason: str = Field("", max_length=5000)
    location: str = Field("", max_length=500)

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, end: str, info) -> str:
        start = info.data.get("start_time")
        if start and end <= start:
            raise ValueError("end_time must be after start_time")
        return end


class AppointmentUpdate(BaseModel):
    patient_name: Optional[str] = Field(None, max_length=255)
    doctor_name: Optional[str] = Field(None, max_length=255)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    reason: Optional[str] = Field(None, max_length=5000)
    location: Optional[str] = Field(None, max_length=500)


class AppointmentResponse(BaseModel):
    id: str
    patient_name: str
    doctor_name: str
    reason: Optional[str]
    start_time: str
    end_time: str
    location: Optional[str]
    created_at: Optional[str]


# ── Patient Records (EHR) ────────────────────────────────────────────────────
class PatientRecordCreate(BaseModel):
    patient_name: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1, max_length=50000)
    tags: Optional[List[str]] = Field(default_factory=list)
    is_pinned: bool = False

    @field_validator("tags", mode="before")
    @classmethod
    def clean_tags(cls, v):
        if v is None:
            return []
        return [t.strip().lower() for t in v if t.strip()]


class PatientRecordUpdate(BaseModel):
    patient_name: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = Field(None, max_length=50000)
    tags: Optional[List[str]] = None
    is_pinned: Optional[bool] = None


class PatientRecordResponse(BaseModel):
    id: str
    patient_name: str
    content: str
    tags: List[str]
    is_pinned: bool
    created_at: Optional[str]
    updated_at: Optional[str]


# ── Health ────────────────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    timestamp: str
    model: str
