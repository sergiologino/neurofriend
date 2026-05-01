"""romantic dynamics state (v4.3 Stage C)

Revision ID: 20260426_7
Revises: 20260426_6
Create Date: 2026-05-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260426_7"
down_revision: str | None = "20260426_6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "internal_state_snapshots",
        sa.Column("affection", sa.Float(), nullable=False, server_default="0.35"),
    )
    op.add_column(
        "internal_state_snapshots",
        sa.Column("romantic_interest", sa.Float(), nullable=False, server_default="0.12"),
    )
    op.add_column(
        "internal_state_snapshots",
        sa.Column("flirt_comfort", sa.Float(), nullable=False, server_default="0.22"),
    )
    op.add_column(
        "internal_state_snapshots",
        sa.Column("emotional_intimacy", sa.Float(), nullable=False, server_default="0.18"),
    )
    op.add_column(
        "relationship_models",
        sa.Column("bond_type", sa.String(length=48), nullable=False, server_default="platonic"),
    )
    op.add_column(
        "relationship_models",
        sa.Column("affection_score", sa.Float(), nullable=False, server_default="0.35"),
    )
    op.add_column(
        "relationship_models",
        sa.Column("romantic_tension_score", sa.Float(), nullable=False, server_default="0.12"),
    )
    op.add_column(
        "relationship_models",
        sa.Column("emotional_intimacy_score", sa.Float(), nullable=False, server_default="0.18"),
    )


def downgrade() -> None:
    op.drop_column("relationship_models", "emotional_intimacy_score")
    op.drop_column("relationship_models", "romantic_tension_score")
    op.drop_column("relationship_models", "affection_score")
    op.drop_column("relationship_models", "bond_type")
    op.drop_column("internal_state_snapshots", "emotional_intimacy")
    op.drop_column("internal_state_snapshots", "flirt_comfort")
    op.drop_column("internal_state_snapshots", "romantic_interest")
    op.drop_column("internal_state_snapshots", "affection")
