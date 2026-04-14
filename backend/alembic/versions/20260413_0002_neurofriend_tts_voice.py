"""add neurofriend_profiles.tts_voice

Revision ID: 20260413_2
Revises: 20260412_1
Create Date: 2026-04-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260413_2"
down_revision: str | None = "20260412_1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "neurofriend_profiles",
        sa.Column("tts_voice", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("neurofriend_profiles", "tts_voice")
