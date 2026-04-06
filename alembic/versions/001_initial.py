"""Initial migration – create all HMS tables.

Revision ID: 001_initial
Create Date: 2025-06-01

This migration matches the HMS ORM models in backend/database/models.py.
"""

import sqlalchemy as sa

from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── clinical_tasks ─────────────────────────────────────────────────────────
    op.create_table(
        "clinical_tasks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("patient_name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="todo"
        ),
        sa.Column(
            "priority", sa.String(length=10), nullable=False, server_default="medium"
        ),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=True, server_default=sa.text("NOW()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=True, server_default=sa.text("NOW()")
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_clinical_tasks_status", "clinical_tasks", ["status"])
    op.create_index("ix_clinical_tasks_priority", "clinical_tasks", ["priority"])
    op.create_index("ix_clinical_tasks_created_at", "clinical_tasks", ["created_at"])
    op.create_index(
        "ix_ctasks_status_priority",
        "clinical_tasks",
        ["status", "priority"],
    )

    # ── appointments ───────────────────────────────────────────────────────────
    op.create_table(
        "appointments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("patient_name", sa.String(length=255), nullable=False),
        sa.Column("doctor_name", sa.String(length=255), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("location", sa.String(length=500), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=True, server_default=sa.text("NOW()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=True, server_default=sa.text("NOW()")
        ),
    )
    op.create_index("ix_appointments_start_time", "appointments", ["start_time"])
    op.create_index("ix_appointments_end_time", "appointments", ["end_time"])
    op.create_index(
        "ix_appt_time_range",
        "appointments",
        ["start_time", "end_time"],
    )

    # ── patient_records ────────────────────────────────────────────────────────
    op.create_table(
        "patient_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("patient_name", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column(
            "is_pinned", sa.Boolean(), nullable=True, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=True, server_default=sa.text("NOW()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=True, server_default=sa.text("NOW()")
        ),
    )
    op.create_index("ix_patient_records_is_pinned", "patient_records", ["is_pinned"])
    op.create_index("ix_patient_records_created_at", "patient_records", ["created_at"])

    # pgvector embedding support (optional at runtime)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column(
        "patient_records", sa.Column("embedding", sa.LargeBinary(), nullable=True)
    )

    # ── agent_memory ───────────────────────────────────────────────────────────
    op.create_table(
        "agent_memory",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=True, server_default=sa.text("NOW()")
        ),
    )
    op.create_index("ix_agent_memory_session_id", "agent_memory", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_memory_session_id", table_name="agent_memory")
    op.drop_table("agent_memory")

    op.drop_index("ix_patient_records_created_at", table_name="patient_records")
    op.drop_index("ix_patient_records_is_pinned", table_name="patient_records")
    op.drop_column("patient_records", "embedding")
    op.drop_table("patient_records")

    op.drop_index("ix_appt_time_range", table_name="appointments")
    op.drop_index("ix_appointments_end_time", table_name="appointments")
    op.drop_index("ix_appointments_start_time", table_name="appointments")
    op.drop_table("appointments")

    op.drop_index("ix_ctasks_status_priority", table_name="clinical_tasks")
    op.drop_index("ix_clinical_tasks_created_at", table_name="clinical_tasks")
    op.drop_index("ix_clinical_tasks_priority", table_name="clinical_tasks")
    op.drop_index("ix_clinical_tasks_status", table_name="clinical_tasks")
    op.drop_table("clinical_tasks")
