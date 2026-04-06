#!/usr/bin/env python3
"""
scripts/seed_data.py - Populates the HMS database with realistic medical demo data.
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from backend.database import crud
from backend.database.connection import AsyncSessionLocal, init_db

TASKS = [
    {
        "title": "Administer 50mg Ibuprofen",
        "patient_name": "John Doe",
        "description": "Oral administration for mild fever.",
        "priority": "high",
        "due_date": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "tags": ["medication", "urgent"],
    },
    {
        "title": "Check Vitals",
        "patient_name": "Jane Smith",
        "description": "Routine check: BP, Heart Rate, Temp.",
        "priority": "medium",
        "due_date": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        "tags": ["vitals", "routine"],
    },
    {
        "title": "Prepare Discharge Papers",
        "patient_name": "Robert Carlos",
        "description": "Patient cleared by Dr. Adams for discharge today.",
        "priority": "low",
        "due_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "tags": ["admin", "discharge"],
    },
]

EVENTS = [
    {
        "patient_name": "John Doe",
        "doctor_name": "Dr. Sarah Adams",
        "start_time": (
            datetime.now(timezone.utc).replace(
                hour=10, minute=0, second=0, microsecond=0
            )
            + timedelta(days=1)
        ).isoformat(),
        "end_time": (
            datetime.now(timezone.utc).replace(
                hour=10, minute=30, second=0, microsecond=0
            )
            + timedelta(days=1)
        ).isoformat(),
        "location": "Room 204",
        "reason": "Follow-up post surgery.",
    },
    {
        "patient_name": "Emily Chen",
        "doctor_name": "Dr. Mark Sloan",
        "start_time": (
            datetime.now(timezone.utc).replace(
                hour=14, minute=0, second=0, microsecond=0
            )
            + timedelta(days=2)
        ).isoformat(),
        "end_time": (
            datetime.now(timezone.utc).replace(
                hour=15, minute=0, second=0, microsecond=0
            )
            + timedelta(days=2)
        ).isoformat(),
        "location": "Consultation A",
        "reason": "New patient assessment - chronic migraines.",
    },
]

NOTES = [
    {
        "patient_name": "John Doe",
        "content": (
            "Patient recovering well. Incision site is clean with no signs of infection. "
            "Temp 98.6F. Continue current pain management protocol."
        ),
        "tags": ["surgery", "recovery", "stable"],
        "is_pinned": True,
    },
    {
        "patient_name": "Jane Smith",
        "content": (
            "Patient reported slight dizziness upon waking. Vitals are normal. "
            "Will monitor for 24 hours before making changes to medication."
        ),
        "tags": ["observation", "dizziness"],
        "is_pinned": False,
    },
]


async def seed():
    print("🌱 Seeding Hospital Management System database...")
    await init_db()

    async with AsyncSessionLocal() as db:
        for task in TASKS:
            await crud.create_task(db, **task)
        for event in EVENTS:
            await crud.create_event(db, **event)
        for note in NOTES:
            await crud.create_note(db, **note)

        await db.commit()

    print("✅ Seeded Hospital Data successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
