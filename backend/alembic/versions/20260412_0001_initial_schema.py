"""initial schema

Revision ID: 20260412_1
Revises:
Create Date: 2026-04-12
"""

from collections.abc import Sequence

from alembic import op

from app.core.database import Base

# Import model modules so metadata is populated
from app.models import (  # noqa: F401
    ConversationThread,
    EventLog,
    IdentityCore,
    InternalStateSnapshot,
    Message,
    NeuroFriendProfile,
    RelationshipModel,
    User,
)

revision: str = "20260412_1"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
