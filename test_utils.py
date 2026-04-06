"""
tests/test_utils.py – Unit tests for backend/utils.py helpers.
Pure Python – no DB, no HTTP.
"""
import pytest
from backend.utils import (
    is_valid_uuid,
    truncate,
    clean_tags,
    generate_session_id,
    format_duration,
    parse_natural_date,
)


def test_is_valid_uuid_true():
    import uuid
    assert is_valid_uuid(str(uuid.uuid4())) is True


def test_is_valid_uuid_false():
    assert is_valid_uuid("not-a-uuid") is False
    assert is_valid_uuid("") is False
    assert is_valid_uuid("12345") is False


def test_truncate_short_unchanged():
    assert truncate("hello", 10) == "hello"


def test_truncate_long_shortened():
    result = truncate("hello world", max_len=8)
    assert len(result) <= 8
    assert result.endswith("…")


def test_clean_tags_from_string():
    result = clean_tags("Work, Urgent, ,  AI ")
    assert result == ["work", "urgent", "ai"]


def test_clean_tags_from_list():
    result = clean_tags(["PYTHON", " FastAPI ", ""])
    assert result == ["python", "fastapi"]


def test_clean_tags_none_returns_empty():
    assert clean_tags(None) == []


def test_generate_session_id_is_uuid():
    sid = generate_session_id()
    assert is_valid_uuid(sid)


def test_generate_session_id_unique():
    ids = {generate_session_id() for _ in range(100)}
    assert len(ids) == 100


def test_format_duration_seconds():
    assert format_duration(45) == "45s"


def test_format_duration_minutes():
    assert format_duration(150) == "2m 30s"


def test_format_duration_hours():
    assert format_duration(3700) == "1h 1m"


def test_parse_natural_date_today():
    result = parse_natural_date("today")
    assert result is not None
    assert "T09:00:00" in result


def test_parse_natural_date_tomorrow():
    from datetime import datetime, timedelta, timezone
    result = parse_natural_date("tomorrow")
    assert result is not None
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    assert result.startswith(tomorrow)


def test_parse_natural_date_unknown_returns_none():
    assert parse_natural_date("quarter past never") is None
