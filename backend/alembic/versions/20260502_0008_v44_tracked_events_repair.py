"""v4.4 TrackedEvent + repair initiative fields

Revision ID: 20260502_8
Revises: 20260426_7
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260502_8"
down_revision: str | None = "20260426_7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "internal_state_snapshots",
        sa.Column("conflict_peak", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "internal_state_snapshots",
        sa.Column("cooldown_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "internal_state_snapshots",
        sa.Column("repair_readiness", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "internal_state_snapshots",
        sa.Column("reconnection_need", sa.Float(), nullable=False, server_default="0"),
    )

    op.add_column(
        "relationship_models",
        sa.Column("unresolved_conflict", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "relationship_models",
        sa.Column("last_conflict_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "relationship_models",
        sa.Column("repair_attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "relationship_models",
        sa.Column("last_repair_attempt_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "relationship_models",
        sa.Column("repair_success_rate", sa.Float(), nullable=False, server_default="0.5"),
    )

    op.create_table(
        "tracked_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("neurofriend_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("title", sa.String(length=320), nullable=False),
        sa.Column("subject_person", sa.String(length=200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("event_time", sa.DateTime(), nullable=True),
        sa.Column("time_precision", sa.String(length=24), nullable=False, server_default="unknown"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("source_event_id", sa.Uuid(), nullable=True),
        sa.Column("needs_clarification", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("missing_fields_json", sa.JSON(), nullable=True),
        sa.Column("importance_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("follow_up_strategy", sa.String(length=48), nullable=False, server_default="soft_check_in"),
        sa.Column("related_memory_ids_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["neurofriend_id"], ["neurofriend_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tracked_events_neurofriend_id"), "tracked_events", ["neurofriend_id"], unique=False)
    op.create_index(op.f("ix_tracked_events_user_id"), "tracked_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_tracked_events_event_type"), "tracked_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_tracked_events_status"), "tracked_events", ["status"], unique=False)

    op.create_table(
        "tracked_event_reminders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tracked_event_id", sa.Uuid(), nullable=False),
        sa.Column("remind_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("hint", sa.String(length=400), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tracked_event_id"], ["tracked_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tracked_event_reminders_remind_at"),
        "tracked_event_reminders",
        ["remind_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tracked_event_reminders_tracked_event_id"),
        "tracked_event_reminders",
        ["tracked_event_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_tracked_event_reminders_tracked_event_id"), table_name="tracked_event_reminders")
    op.drop_index(op.f("ix_tracked_event_reminders_remind_at"), table_name="tracked_event_reminders")
    op.drop_table("tracked_event_reminders")
    op.drop_index(op.f("ix_tracked_events_status"), table_name="tracked_events")
    op.drop_index(op.f("ix_tracked_events_event_type"), table_name="tracked_events")
    op.drop_index(op.f("ix_tracked_events_user_id"), table_name="tracked_events")
    op.drop_index(op.f("ix_tracked_events_neurofriend_id"), table_name="tracked_events")
    op.drop_table("tracked_events")

    op.drop_column("relationship_models", "repair_success_rate")
    op.drop_column("relationship_models", "last_repair_attempt_at")
    op.drop_column("relationship_models", "repair_attempt_count")
    op.drop_column("relationship_models", "last_conflict_at")
    op.drop_column("relationship_models", "unresolved_conflict")

    op.drop_column("internal_state_snapshots", "reconnection_need")
    op.drop_column("internal_state_snapshots", "repair_readiness")
    op.drop_column("internal_state_snapshots", "cooldown_active")
    op.drop_column("internal_state_snapshots", "conflict_peak")
