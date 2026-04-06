"""
tests/test_schemas.py – Unit tests for Pydantic schemas & validators.
No DB or HTTP client needed.
"""
import pytest
from datetime import datetime, timedelta, timezone
from pydantic import ValidationError

from backend.schemas import (
    ChatRequest,
    ClinicalTaskCreate, ClinicalTaskUpdate,
    AppointmentCreate, AppointmentUpdate,
    PatientRecordCreate, PatientRecordUpdate,
)


# ── ChatRequest ───────────────────────────────────────────────────────────────

def test_chat_request_strips_whitespace():
    req = ChatRequest(message="  hello world  ")
    assert req.message == "hello world"


def test_chat_request_empty_fails():
    with pytest.raises(ValidationError):
        ChatRequest(message="")


def test_chat_request_too_long_fails():
    with pytest.raises(ValidationError):
        ChatRequest(message="x" * 4001)


def test_chat_request_no_session_defaults_none():
    req = ChatRequest(message="hi")
    assert req.session_id is None


# ── ClinicalTaskCreate ────────────────────────────────────────────────────────

def test_task_create_valid():
    t = ClinicalTaskCreate(title="My Task", patient_name="John Doe", priority="high", tags=["work", "urgent"])
    assert t.title == "My Task"
    assert t.priority == "high"
    assert "work" in t.tags


def test_task_create_tags_normalised():
    t = ClinicalTaskCreate(title="T", tags=["  WORK  ", "Urgent", ""])
    assert t.tags == ["work", "urgent"]  # stripped, lowercased, empty removed


def test_task_create_invalid_priority():
    with pytest.raises(ValidationError):
        ClinicalTaskCreate(title="T", priority="critical")


def test_task_create_empty_title_fails():
    with pytest.raises(ValidationError):
        ClinicalTaskCreate(title="")


def test_task_update_all_optional():
    u = ClinicalTaskUpdate()
    assert u.title is None
    assert u.status is None


def test_task_update_invalid_status():
    with pytest.raises(ValidationError):
        ClinicalTaskUpdate(status="pending")


# ── AppointmentCreate ─────────────────────────────────────────────────────────

def test_event_create_valid():
    start = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    e = AppointmentCreate(patient_name="John", doctor_name="Dr. Smith", start_time=start, end_time=end)
    assert e.patient_name == "John"


def test_event_create_end_before_start_fails():
    start = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    with pytest.raises(ValidationError):
        AppointmentCreate(patient_name="John", doctor_name="Dr. Smith", start_time=start, end_time=end)


# ── PatientRecordCreate ───────────────────────────────────────────────────────

def test_note_create_valid():
    n = PatientRecordCreate(patient_name="John", content="Some content", is_pinned=True)
    assert n.is_pinned is True


def test_note_create_empty_content_fails():
    with pytest.raises(ValidationError):
        PatientRecordCreate(patient_name="John", content="")


def test_note_create_tags_normalised():
    n = PatientRecordCreate(patient_name="John", content="c", tags=["Tag1", " TAG2 ", ""])
    assert n.tags == ["tag1", "tag2"]


def test_note_update_all_optional():
    u = PatientRecordUpdate()
    assert u.patient_name is None
    assert u.content is None
    assert u.is_pinned is None
