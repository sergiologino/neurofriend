"""add biography and expertise profiles

Revision ID: 20260426_3
Revises: 20260413_2
Create Date: 2026-04-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260426_3"
down_revision: str | None = "20260413_2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "neurofriend_profiles",
        sa.Column("biography_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "neurofriend_profiles",
        sa.Column("expertise_profile_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "identity_cores",
        sa.Column("expertise_profile_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_table(
        "biography_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("neurofriend_id", sa.Uuid(), nullable=False),
        sa.Column("birth_context_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("family_background_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("education_path_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("work_path_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("important_events_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("habits_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("preferences_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("core_dates_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("relationship_history_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("current_life_stage", sa.String(length=240), nullable=False),
        sa.Column("biography_consistency_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["neurofriend_id"], ["neurofriend_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("neurofriend_id"),
    )
    op.create_index(op.f("ix_biography_profiles_neurofriend_id"), "biography_profiles", ["neurofriend_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_biography_profiles_neurofriend_id"), table_name="biography_profiles")
    op.drop_table("biography_profiles")
    op.drop_column("identity_cores", "expertise_profile_json")
    op.drop_column("neurofriend_profiles", "expertise_profile_version")
    op.drop_column("neurofriend_profiles", "biography_enabled")
