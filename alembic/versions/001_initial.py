"""Initial migration – create all AgentFlow tables.

Revision ID: 001_initial
Create Date: 2025-06-01

NOTE: This migration must match the ORM models in backend/database/models.py.
Key differences from old version:
  - IDs use VARCHAR (not UUID) since we generate UUIDs in Python
  - tags/attendees use JSONB (not ARRAY/TEXT) for structured list storage
  - status/priority use VARCHAR (not ENUM) for simpler schema evolution
"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── tasks ──────────────────────────────────────────────────────────────────
    op.create_table(
        "tasks",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="todo"),
        sa.Column("priority", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("due_date", sa.DateTime, nullable=True),
        sa.Column("tags", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("NOW()")),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_priority", "tasks", ["priority"])
    op.create_index("ix_tasks_due_date", "tasks", ["due_date"])

    # ── calendar_events ────────────────────────────────────────────────────────
    op.create_table(
        "calendar_events",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("start_time", sa.DateTime, nullable=False),
        sa.Column("end_time", sa.DateTime, nullable=False),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("attendees", sa.JSON, nullable=True),
        sa.Column("is_recurring", sa.Boolean, server_default="false"),
        sa.Column("recurrence_rule", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_events_start_time", "calendar_events", ["start_time"])

    # ── notes ──────────────────────────────────────────────────────────────────
    op.create_table(
        "notes",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("tags", sa.JSON, nullable=True),
        sa.Column("is_pinned", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_notes_pinned", "notes", ["is_pinned"])

    # pgvector embedding column – added separately since it requires the extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column("notes", sa.Column("embedding", sa.LargeBinary, nullable=True))

    # ── agent_memory ────────────────────────────────────────────────────────────
    op.create_table(
        "agent_memory",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("session_id", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_memory_session_id", "agent_memory", ["session_id"])


def downgrade() -> None:
    op.drop_table("agent_memory")
    op.drop_table("notes")
    op.drop_table("calendar_events")
    op.drop_table("tasks")
