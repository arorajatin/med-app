"""Create the initial medical records schema.

Revision ID: 20260721_0001
Revises:
Create Date: 2026-07-21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260721_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("relationship", sa.String(length=80), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("sex", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_profiles_user_id", "profiles", ["user_id"], unique=False)

    op.create_table(
        "appointments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clinician_name", sa.String(length=200), nullable=True),
        sa.Column("location", sa.String(length=240), nullable=True),
        sa.Column("reason", sa.String(length=300), nullable=True),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_appointments_profile_id", "appointments", ["profile_id"], unique=False)
    op.create_index("ix_appointments_user_id", "appointments", ["user_id"], unique=False)

    op.create_table(
        "appointment_checklist_items",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("appointment_id", sa.String(), nullable=False),
        sa.Column("question", sa.String(length=500), nullable=False),
        sa.Column("source_fact_id", sa.String(), nullable=True),
        sa.Column("is_generic", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_appointment_checklist_items_appointment_id",
        "appointment_checklist_items",
        ["appointment_id"],
        unique=False,
    )
    op.create_index(
        "ix_appointment_checklist_items_profile_id",
        "appointment_checklist_items",
        ["profile_id"],
        unique=False,
    )
    op.create_index(
        "ix_appointment_checklist_items_user_id",
        "appointment_checklist_items",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "appointment_reviews",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("appointment_id", sa.String(), nullable=False),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_appointment_reviews_appointment_id",
        "appointment_reviews",
        ["appointment_id"],
        unique=False,
    )
    op.create_index(
        "ix_appointment_reviews_profile_id",
        "appointment_reviews",
        ["profile_id"],
        unique=False,
    )
    op.create_index(
        "ix_appointment_reviews_user_id",
        "appointment_reviews",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "medical_records",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("record_type", sa.String(length=120), nullable=True),
        sa.Column("record_date", sa.Date(), nullable=True),
        sa.Column("provider_name", sa.String(length=240), nullable=True),
        sa.Column("ai_processing_consent", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_medical_records_profile_id", "medical_records", ["profile_id"], unique=False
    )
    op.create_index("ix_medical_records_user_id", "medical_records", ["user_id"], unique=False)

    op.create_table(
        "memory_facts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("source_record_id", sa.String(), nullable=False),
        sa.Column("source_field_id", sa.String(), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("body_system", sa.String(length=120), nullable=True),
        sa.Column("occurred_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memory_facts_profile_id", "memory_facts", ["profile_id"], unique=False)
    op.create_index(
        "ix_memory_facts_source_field_id", "memory_facts", ["source_field_id"], unique=False
    )
    op.create_index(
        "ix_memory_facts_source_record_id", "memory_facts", ["source_record_id"], unique=False
    )
    op.create_index("ix_memory_facts_user_id", "memory_facts", ["user_id"], unique=False)

    op.create_table(
        "record_files",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("record_id", sa.String(), nullable=False),
        sa.Column("filename", sa.String(length=260), nullable=False),
        sa.Column("mime_type", sa.String(length=160), nullable=False),
        sa.Column("storage_path", sa.String(length=600), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["record_id"], ["medical_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_record_files_profile_id", "record_files", ["profile_id"], unique=False)
    op.create_index("ix_record_files_record_id", "record_files", ["record_id"], unique=False)
    op.create_index("ix_record_files_user_id", "record_files", ["user_id"], unique=False)

    op.create_table(
        "extraction_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("record_id", sa.String(), nullable=False),
        sa.Column("file_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("raw_output", sa.JSON(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["file_id"], ["record_files.id"]),
        sa.ForeignKeyConstraint(["record_id"], ["medical_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_extraction_jobs_file_id", "extraction_jobs", ["file_id"], unique=False)
    op.create_index(
        "ix_extraction_jobs_profile_id", "extraction_jobs", ["profile_id"], unique=False
    )
    op.create_index(
        "ix_extraction_jobs_record_id", "extraction_jobs", ["record_id"], unique=False
    )
    op.create_index("ix_extraction_jobs_user_id", "extraction_jobs", ["user_id"], unique=False)

    op.create_table(
        "extracted_fields",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("record_id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("field_type", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=180), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("normalized_value", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source_reference", sa.String(length=240), nullable=True),
        sa.Column("confirmation_status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["extraction_jobs.id"]),
        sa.ForeignKeyConstraint(["record_id"], ["medical_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_extracted_fields_job_id", "extracted_fields", ["job_id"], unique=False
    )
    op.create_index(
        "ix_extracted_fields_profile_id", "extracted_fields", ["profile_id"], unique=False
    )
    op.create_index(
        "ix_extracted_fields_record_id", "extracted_fields", ["record_id"], unique=False
    )
    op.create_index(
        "ix_extracted_fields_user_id", "extracted_fields", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_extracted_fields_user_id", table_name="extracted_fields")
    op.drop_index("ix_extracted_fields_record_id", table_name="extracted_fields")
    op.drop_index("ix_extracted_fields_profile_id", table_name="extracted_fields")
    op.drop_index("ix_extracted_fields_job_id", table_name="extracted_fields")
    op.drop_table("extracted_fields")

    op.drop_index("ix_extraction_jobs_user_id", table_name="extraction_jobs")
    op.drop_index("ix_extraction_jobs_record_id", table_name="extraction_jobs")
    op.drop_index("ix_extraction_jobs_profile_id", table_name="extraction_jobs")
    op.drop_index("ix_extraction_jobs_file_id", table_name="extraction_jobs")
    op.drop_table("extraction_jobs")

    op.drop_index("ix_record_files_user_id", table_name="record_files")
    op.drop_index("ix_record_files_record_id", table_name="record_files")
    op.drop_index("ix_record_files_profile_id", table_name="record_files")
    op.drop_table("record_files")

    op.drop_index("ix_memory_facts_user_id", table_name="memory_facts")
    op.drop_index("ix_memory_facts_source_record_id", table_name="memory_facts")
    op.drop_index("ix_memory_facts_source_field_id", table_name="memory_facts")
    op.drop_index("ix_memory_facts_profile_id", table_name="memory_facts")
    op.drop_table("memory_facts")

    op.drop_index("ix_medical_records_user_id", table_name="medical_records")
    op.drop_index("ix_medical_records_profile_id", table_name="medical_records")
    op.drop_table("medical_records")

    op.drop_index("ix_appointment_reviews_user_id", table_name="appointment_reviews")
    op.drop_index("ix_appointment_reviews_profile_id", table_name="appointment_reviews")
    op.drop_index("ix_appointment_reviews_appointment_id", table_name="appointment_reviews")
    op.drop_table("appointment_reviews")

    op.drop_index(
        "ix_appointment_checklist_items_user_id", table_name="appointment_checklist_items"
    )
    op.drop_index(
        "ix_appointment_checklist_items_profile_id", table_name="appointment_checklist_items"
    )
    op.drop_index(
        "ix_appointment_checklist_items_appointment_id", table_name="appointment_checklist_items"
    )
    op.drop_table("appointment_checklist_items")

    op.drop_index("ix_appointments_user_id", table_name="appointments")
    op.drop_index("ix_appointments_profile_id", table_name="appointments")
    op.drop_table("appointments")

    op.drop_index("ix_profiles_user_id", table_name="profiles")
    op.drop_table("profiles")
