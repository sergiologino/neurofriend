"""add boundary state fields

Revision ID: 20260426_5
Revises: 20260426_4
Create Date: 2026-04-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260426_5"
down_revision: str | None = "20260426_4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("internal_state_snapshots", sa.Column("friction", sa.Float(), nullable=False, server_default="0"))
    op.add_column("internal_state_snapshots", sa.Column("respect_signal", sa.Float(), nullable=False, server_default="0.5"))
    op.add_column("internal_state_snapshots", sa.Column("self_respect_activation", sa.Float(), nullable=False, server_default="0"))
    op.add_column("internal_state_snapshots", sa.Column("boundary_alert", sa.Float(), nullable=False, server_default="0"))
    op.add_column("relationship_models", sa.Column("conflict_memory_score", sa.Float(), nullable=False, server_default="0"))
    op.add_column("relationship_models", sa.Column("repair_receptivity", sa.Float(), nullable=False, server_default="0.5"))
    op.add_column("relationship_models", sa.Column("respect_baseline", sa.Float(), nullable=False, server_default="0.5"))
    op.add_column("relationship_models", sa.Column("boundary_safety_score", sa.Float(), nullable=False, server_default="0.7"))


def downgrade() -> None:
    op.drop_column("relationship_models", "boundary_safety_score")
    op.drop_column("relationship_models", "respect_baseline")
    op.drop_column("relationship_models", "repair_receptivity")
    op.drop_column("relationship_models", "conflict_memory_score")
    op.drop_column("internal_state_snapshots", "boundary_alert")
    op.drop_column("internal_state_snapshots", "self_respect_activation")
    op.drop_column("internal_state_snapshots", "respect_signal")
    op.drop_column("internal_state_snapshots", "friction")
