"""v4.5 Romantic Style Profiles (IdentityCore + state + relationship)

Revision ID: 20260503_9
Revises: 20260502_8
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260503_9"
down_revision: str | None = "20260502_8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "identity_cores",
        sa.Column("romantic_style_id", sa.String(length=48), nullable=True),
    )
    op.add_column(
        "identity_cores",
        sa.Column("romantic_style_profile_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "identity_cores",
        sa.Column("romantic_variation_seed", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "identity_cores",
        sa.Column("romantic_style_locked", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index(
        op.f("ix_identity_cores_romantic_style_id"),
        "identity_cores",
        ["romantic_style_id"],
        unique=False,
    )

    op.add_column(
        "internal_state_snapshots",
        sa.Column("jealousy_activation", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "internal_state_snapshots",
        sa.Column("vulnerability_pressure", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "internal_state_snapshots",
        sa.Column("distance_pain", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "internal_state_snapshots",
        sa.Column("desire_for_reassurance", sa.Float(), nullable=False, server_default="0"),
    )

    op.add_column(
        "relationship_models",
        sa.Column("romantic_phase", sa.String(length=32), nullable=False, server_default="none"),
    )
    op.add_column(
        "relationship_models",
        sa.Column("confession_readiness", sa.Float(), nullable=False, server_default="0.08"),
    )
    op.add_column(
        "relationship_models",
        sa.Column("flirt_history_score", sa.Float(), nullable=False, server_default="0.1"),
    )
    op.add_column(
        "relationship_models",
        sa.Column("safety_for_vulnerability", sa.Float(), nullable=False, server_default="0.55"),
    )
    op.add_column(
        "relationship_models",
        sa.Column("romantic_misalignment_score", sa.Float(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("relationship_models", "romantic_misalignment_score")
    op.drop_column("relationship_models", "safety_for_vulnerability")
    op.drop_column("relationship_models", "flirt_history_score")
    op.drop_column("relationship_models", "confession_readiness")
    op.drop_column("relationship_models", "romantic_phase")

    op.drop_column("internal_state_snapshots", "desire_for_reassurance")
    op.drop_column("internal_state_snapshots", "distance_pain")
    op.drop_column("internal_state_snapshots", "vulnerability_pressure")
    op.drop_column("internal_state_snapshots", "jealousy_activation")

    op.drop_index(op.f("ix_identity_cores_romantic_style_id"), table_name="identity_cores")
    op.drop_column("identity_cores", "romantic_style_locked")
    op.drop_column("identity_cores", "romantic_variation_seed")
    op.drop_column("identity_cores", "romantic_style_profile_json")
    op.drop_column("identity_cores", "romantic_style_id")
