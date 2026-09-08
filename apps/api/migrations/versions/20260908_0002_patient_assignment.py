"""Add owned profile aliases and attempt-linked assignment history.

Revision ID: 20260908_0002
Revises: 20260721_0001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260908_0002"
down_revision = "20260721_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("profiles", "auth_identities", "ingestions", "extraction_attempts"):
        op.create_index(f"uq_{table}_id_account", table, ["id", "account_id"], unique=True)
    op.create_table(
        "profile_aliases",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("normalized_name", sa.String(480), nullable=False),
        sa.Column("created_by_identity_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_id", "account_id"], ["profiles.id", "profiles.account_id"]
        ),
        sa.ForeignKeyConstraint(
            ["created_by_identity_id", "account_id"],
            ["auth_identities.id", "auth_identities.account_id"],
        ),
        sa.UniqueConstraint("profile_id", "normalized_name", name="uq_profile_alias_name"),
    )
    op.create_index("ix_profile_aliases_account_id", "profile_aliases", ["account_id"])
    op.create_index("ix_profile_aliases_profile_id", "profile_aliases", ["profile_id"])
    op.create_table(
        "ingestion_assignments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("ingestion_id", sa.String(), nullable=False),
        sa.Column("attempt_id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=True),
        sa.Column("resolver_identity_id", sa.String(), nullable=True),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("match_version", sa.String(80), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("candidate_profile_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingestion_id", "account_id"], ["ingestions.id", "ingestions.account_id"]
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id", "account_id"],
            ["extraction_attempts.id", "extraction_attempts.account_id"],
        ),
        sa.ForeignKeyConstraint(
            ["profile_id", "account_id"], ["profiles.id", "profiles.account_id"]
        ),
        sa.ForeignKeyConstraint(
            ["resolver_identity_id", "account_id"],
            ["auth_identities.id", "auth_identities.account_id"],
        ),
        sa.CheckConstraint("method IN ('automatic', 'manual')", name="ck_assignment_method"),
    )
    op.create_index("ix_ingestion_assignments_account_id", "ingestion_assignments", ["account_id"])
    op.create_index(
        "ix_ingestion_assignments_ingestion_id", "ingestion_assignments", ["ingestion_id"]
    )


def downgrade() -> None:
    op.drop_table("ingestion_assignments")
    op.drop_table("profile_aliases")
    for table in ("profiles", "auth_identities", "ingestions", "extraction_attempts"):
        op.drop_index(f"uq_{table}_id_account", table_name=table)
