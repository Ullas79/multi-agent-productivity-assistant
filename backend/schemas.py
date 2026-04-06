"""
backend/schemas.py – Pydantic v2 schemas for request validation and response serialisation.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
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
    type: str           # "text" | "done" | "error" | "session_id"
    content: Optional[str] = None
    session_id: Optional[str] = None


class SessionHistory(BaseModel):
    session_id: str
    messages: List[dict]


# ── Tasks ─────────────────────────────────────────────────────────────────────

VALID_PRIORITIES = {"low", "medium", "high"}
VALID_STATUSES = {"todo", "in_progress", "done"}


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
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


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    status: Optional[str] = Field(None, pattern="^(todo|in_progress|done)$")
    priority: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    due_date: Optional[str] = None
    tags: Optional[List[str]] = None


class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    status: str
    priority: str
    due_date: Optional[str]
    tags: List[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    completed_at: Optional[str]


class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    count: int


# ── Calendar Events ───────────────────────────────────────────────────────────

class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    start_time: str = Field(..., description="ISO 8601 datetime")
    end_time: str = Field(..., description="ISO 8601 datetime")
    description: str = Field("", max_length=5000)
    location: str = Field("", max_length=500)
    attendees: Optional[List[str]] = Field(default_factory=list)

    @field_validator("attendees", mode="before")
    @classmethod
    def clean_attendees(cls, v):
        if v is None:
            return []
        return [a.strip().lower() for a in v if a.strip()]

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, end: str, info) -> str:
        start = info.data.get("start_time")
        if start:
            try:
                start_dt = datetime.fromisoformat(start)
                end_dt = datetime.fromisoformat(end)
                if end_dt <= start_dt:
                    raise ValueError("end_time must be after start_time")
            except (ValueError, TypeError) as e:
                if "end_time must be after start_time" in str(e):
                    raise
        return end


class EventUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    description: Optional[str] = Field(None, max_length=5000)
    location: Optional[str] = Field(None, max_length=500)
    attendees: Optional[List[str]] = None


class EventResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    start_time: str
    end_time: str
    location: Optional[str]
    attendees: List[str]
    is_recurring: bool
    created_at: Optional[str]


class EventListResponse(BaseModel):
    events: List[EventResponse]
    count: int


# ── Notes ─────────────────────────────────────────────────────────────────────

class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1, max_length=50000)
    tags: Optional[List[str]] = Field(default_factory=list)
    is_pinned: bool = False

    @field_validator("tags", mode="before")
    @classmethod
    def clean_tags(cls, v):
        if v is None:
            return []
        return [t.strip().lower() for t in v if t.strip()]


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = Field(None, max_length=50000)
    tags: Optional[List[str]] = None
    is_pinned: Optional[bool] = None


class NoteResponse(BaseModel):
    id: str
    title: str
    content: str
    tags: List[str]
    is_pinned: bool
    created_at: Optional[str]
    updated_at: Optional[str]


class NoteListResponse(BaseModel):
    notes: List[dict]
    count: int


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    timestamp: str
    model: str
