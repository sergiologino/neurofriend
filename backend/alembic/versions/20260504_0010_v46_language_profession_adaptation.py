"""v4.6 Language & profession adaptation (user language/domain + social learning)

Revision ID: 20260504_10
Revises: 20260503_9
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260504_10"
down_revision: str | None = "20260503_9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_language_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("detected_professions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("primary_profession_confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("lexical_markers_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("favorite_phrases_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("discourse_style_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("jargon_tolerance", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("profanity_tolerance", sa.Float(), nullable=False, server_default="0"),
        sa.Column("humor_style_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("professional_domains_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("domain_lexicon_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("last_updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_language_profiles_user_id"), "user_language_profiles", ["user_id"], unique=True)

    op.create_table(
        "user_domain_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("domain_name", sa.String(length=64), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("active_vocabulary_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("topic_frequency_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("thinking_style", sa.String(length=64), nullable=True),
        sa.Column("metaphor_style", sa.String(length=64), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "domain_name", name="uq_user_domain_name"),
    )
    op.create_index(op.f("ix_user_domain_profiles_domain_name"), "user_domain_profiles", ["domain_name"])
    op.create_index(op.f("ix_user_domain_profiles_user_id"), "user_domain_profiles", ["user_id"])

    op.create_table(
        "social_learning_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("neurofriend_id", sa.Uuid(), nullable=False),
        sa.Column("jargon_adoption_rate", sa.Float(), nullable=False, server_default="0.35"),
        sa.Column("domain_lexicon_adoption_rate", sa.Float(), nullable=False, server_default="0.4"),
        sa.Column("professional_style_alignment", sa.Float(), nullable=False, server_default="0.3"),
        sa.Column("max_jargon_density", sa.Float(), nullable=False, server_default="0.18"),
        sa.Column(
            "forbidden_domain_imitation_patterns",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.ForeignKeyConstraint(["neurofriend_id"], ["neurofriend_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_social_learning_profiles_neurofriend_id"),
        "social_learning_profiles",
        ["neurofriend_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_social_learning_profiles_neurofriend_id"), table_name="social_learning_profiles")
    op.drop_table("social_learning_profiles")
    op.drop_index(op.f("ix_user_domain_profiles_user_id"), table_name="user_domain_profiles")
    op.drop_index(op.f("ix_user_domain_profiles_domain_name"), table_name="user_domain_profiles")
    op.drop_table("user_domain_profiles")
    op.drop_index(op.f("ix_user_language_profiles_user_id"), table_name="user_language_profiles")
    op.drop_table("user_language_profiles")
