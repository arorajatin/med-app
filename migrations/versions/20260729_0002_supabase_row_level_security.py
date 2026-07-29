"""Enforce Supabase ownership policies on user-owned tables.

Revision ID: 20260729_0002
Revises: 20260721_0001
Create Date: 2026-07-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260729_0002"
down_revision: str | Sequence[str] | None = "20260721_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


USER_OWNED_TABLES = (
    "profiles",
    "medical_records",
    "record_files",
    "extraction_jobs",
    "extracted_fields",
    "memory_facts",
    "appointments",
    "appointment_checklist_items",
    "appointment_reviews",
)


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgresql():
        return

    op.execute("GRANT USAGE ON SCHEMA public TO authenticated")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.alembic_version FROM anon, PUBLIC")
    op.execute("GRANT SELECT ON TABLE public.alembic_version TO authenticated")

    for table_name in USER_OWNED_TABLES:
        policy_name = f"{table_name}_owner_access"
        op.execute(f"REVOKE ALL PRIVILEGES ON TABLE public.{table_name} FROM anon, PUBLIC")
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.{table_name} TO authenticated"
        )
        op.execute(f"ALTER TABLE public.{table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table_name} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {policy_name}
            ON public.{table_name}
            FOR ALL
            TO authenticated
            USING (
                user_id = (SELECT auth.uid())::text
            )
            WITH CHECK (
                user_id = (SELECT auth.uid())::text
            )
            """
        )


def downgrade() -> None:
    if not _is_postgresql():
        return

    for table_name in reversed(USER_OWNED_TABLES):
        policy_name = f"{table_name}_owner_access"
        op.execute(f"DROP POLICY IF EXISTS {policy_name} ON public.{table_name}")
        op.execute(f"ALTER TABLE public.{table_name} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table_name} DISABLE ROW LEVEL SECURITY")
