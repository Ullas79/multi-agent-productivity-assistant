"""
backend/utils.py – Shared utility functions.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional


def is_valid_uuid(value: str) -> bool:
    """Return True if value is a valid UUID string."""
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False


def parse_natural_date(text: str) -> Optional[str]:
    """
    Very simple natural-language date resolver.
    Returns ISO 8601 string or None if not recognised.
    """
    now = datetime.now(timezone.utc)
    text = text.lower().strip()

    mapping = {
        "today":       now.replace(hour=9, minute=0, second=0, microsecond=0),
        "tomorrow":    now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1),
        "next week":   now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(weeks=1),
        "next month":  now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=30),
        "this friday": _next_weekday(now, 4),
        "this monday": _next_weekday(now, 0),
    }
    return mapping[text].isoformat() if text in mapping else None


def _next_weekday(ref: datetime, weekday: int) -> datetime:
    """Return the next occurrence of weekday (0=Mon … 6=Sun) at 09:00."""
    days_ahead = weekday - ref.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return (ref + timedelta(days=days_ahead)).replace(
        hour=9, minute=0, second=0, microsecond=0
    )


def truncate(text: str, max_len: int = 200, suffix: str = "…") -> str:
    """Truncate a string to max_len characters."""
    return text if len(text) <= max_len else text[: max_len - len(suffix)] + suffix


def clean_tags(raw: str | list | None) -> list[str]:
    """Normalise tags from a comma-separated string or list."""
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = raw.split(",")
    return [t.strip().lower() for t in raw if t.strip()]


def generate_session_id() -> str:
    """Generate a URL-safe session identifier."""
    return str(uuid.uuid4())


def format_duration(seconds: float) -> str:
    """Human-readable duration from seconds: '2m 30s'."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"
