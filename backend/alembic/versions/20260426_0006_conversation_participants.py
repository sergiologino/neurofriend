"""add conversation participants

Revision ID: 20260426_6
Revises: 20260426_5
Create Date: 2026-04-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.types import jsonb_type

revision: str = "20260426_6"
down_revision: str | None = "20260426_5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversation_participants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("neurofriend_id", sa.Uuid(), nullable=False),
        sa.Column("person_ref", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("participant_kind", sa.String(length=32), nullable=False, server_default="known_user"),
        sa.Column("voiceprint_json", jsonb_type, nullable=True),
        sa.Column("voiceprint_confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("consent_status", sa.String(length=32), nullable=False, server_default="implicit_conversation"),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("turns_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["neurofriend_id"], ["neurofriend_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("neurofriend_id", "person_ref", name="uq_conversation_participant_ref"),
    )
    op.create_index(op.f("ix_conversation_participants_neurofriend_id"), "conversation_participants", ["neurofriend_id"])
    op.create_index(op.f("ix_conversation_participants_participant_kind"), "conversation_participants", ["participant_kind"])
    op.create_index(op.f("ix_conversation_participants_person_ref"), "conversation_participants", ["person_ref"])


def downgrade() -> None:
    op.drop_index(op.f("ix_conversation_participants_person_ref"), table_name="conversation_participants")
    op.drop_index(op.f("ix_conversation_participants_participant_kind"), table_name="conversation_participants")
    op.drop_index(op.f("ix_conversation_participants_neurofriend_id"), table_name="conversation_participants")
    op.drop_table("conversation_participants")
