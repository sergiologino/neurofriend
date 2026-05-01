"""add memory items

Revision ID: 20260426_4
Revises: 20260426_3
Create Date: 2026-04-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260426_4"
down_revision: str | None = "20260426_3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "memory_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("neurofriend_id", sa.Uuid(), nullable=False),
        sa.Column("memory_type", sa.String(length=64), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("content_structured_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_event_ids_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("importance_score", sa.Float(), nullable=False),
        sa.Column("access_score", sa.Float(), nullable=False),
        sa.Column("decay_score", sa.Float(), nullable=False),
        sa.Column("retrieval_count", sa.Float(), nullable=False),
        sa.Column("person_refs_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("emotion_tags_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("topic_tags_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["neurofriend_id"], ["neurofriend_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_memory_items_neurofriend_id"), "memory_items", ["neurofriend_id"], unique=False)
    op.create_index(op.f("ix_memory_items_memory_type"), "memory_items", ["memory_type"], unique=False)
    op.create_index(op.f("ix_memory_items_importance_score"), "memory_items", ["importance_score"], unique=False)
    op.create_index(op.f("ix_memory_items_created_at"), "memory_items", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_memory_items_created_at"), table_name="memory_items")
    op.drop_index(op.f("ix_memory_items_importance_score"), table_name="memory_items")
    op.drop_index(op.f("ix_memory_items_memory_type"), table_name="memory_items")
    op.drop_index(op.f("ix_memory_items_neurofriend_id"), table_name="memory_items")
    op.drop_table("memory_items")
