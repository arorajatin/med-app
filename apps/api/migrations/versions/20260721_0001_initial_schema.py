"""Create the first-release family health schema.

Revision ID: 20260721_0001
Revises:
Create Date: 2026-07-21
"""

from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Frozen ownership graph for this undeployed baseline.
ACCOUNT_TABLES = (
    "appointment_checklist_items",
    "appointment_reviews",
    "appointments",
    "auth_identities",
    "document_metadata_candidates",
    "document_metadata_reviews",
    "extraction_attempts",
    "extraction_jobs",
    "ingestion_assignments",
    "ingestion_parts",
    "ingestions",
    "medical_records",
    "memory_candidate_reviews",
    "memory_candidates",
    "memory_facts",
    "metric_observations",
    "patient_evidence",
    "profile_aliases",
    "profile_health_context",
    "profiles",
    "source_references",
    "storage_cleanup_intents",
)
OWNERSHIP_LINKS = (
    (
        "appointment_checklist_items",
        "fk_owner_appointment_checklist_items_appointment_id",
        "appointment_id",
        "appointments",
    ),
    (
        "appointment_checklist_items",
        "fk_owner_appointment_checklist_items_profile_id",
        "profile_id",
        "profiles",
    ),
    (
        "appointment_checklist_items",
        "fk_owner_appointment_checklist_items_source_fact_id",
        "source_fact_id",
        "memory_facts",
    ),
    (
        "appointment_reviews",
        "fk_owner_appointment_reviews_appointment_id",
        "appointment_id",
        "appointments",
    ),
    ("appointment_reviews", "fk_owner_appointment_reviews_profile_id", "profile_id", "profiles"),
    ("appointments", "fk_owner_appointments_profile_id", "profile_id", "profiles"),
    (
        "document_metadata_candidates",
        "fk_owner_document_metadata_candidates_attempt_id",
        "attempt_id",
        "extraction_attempts",
    ),
    (
        "document_metadata_candidates",
        "fk_owner_document_metadata_candidates_ingestion_id",
        "ingestion_id",
        "ingestions",
    ),
    (
        "document_metadata_candidates",
        "fk_owner_document_metadata_candidates_profile_id",
        "profile_id",
        "profiles",
    ),
    (
        "document_metadata_candidates",
        "fk_owner_document_metadata_candidates_record_id",
        "record_id",
        "medical_records",
    ),
    (
        "document_metadata_reviews",
        "fk_owner_document_metadata_reviews_candidate_id",
        "candidate_id",
        "document_metadata_candidates",
    ),
    (
        "document_metadata_reviews",
        "fk_owner_document_metadata_reviews_reviewer_identity_id",
        "reviewer_identity_id",
        "auth_identities",
    ),
    ("extraction_attempts", "fk_owner_extraction_attempts_job_id", "job_id", "extraction_jobs"),
    ("extraction_jobs", "fk_owner_extraction_jobs_ingestion_id", "ingestion_id", "ingestions"),
    (
        "ingestion_parts",
        "fk_owner_ingestion_parts_actor_identity_id",
        "actor_identity_id",
        "auth_identities",
    ),
    ("ingestion_parts", "fk_owner_ingestion_parts_ingestion_id", "ingestion_id", "ingestions"),
    (
        "ingestions",
        "fk_owner_ingestions_provisional_profile_id",
        "provisional_profile_id",
        "profiles",
    ),
    (
        "ingestions",
        "fk_owner_ingestions_resolved_by_identity_id",
        "resolved_by_identity_id",
        "auth_identities",
    ),
    ("ingestions", "fk_owner_ingestions_resolved_profile_id", "resolved_profile_id", "profiles"),
    ("medical_records", "fk_owner_medical_records_ingestion_id", "ingestion_id", "ingestions"),
    ("medical_records", "fk_owner_medical_records_profile_id", "profile_id", "profiles"),
    (
        "memory_candidate_reviews",
        "fk_owner_memory_candidate_reviews_candidate_id",
        "candidate_id",
        "memory_candidates",
    ),
    (
        "memory_candidate_reviews",
        "fk_owner_memory_candidate_reviews_reviewer_identity_id",
        "reviewer_identity_id",
        "auth_identities",
    ),
    (
        "memory_candidates",
        "fk_owner_memory_candidates_attempt_id",
        "attempt_id",
        "extraction_attempts",
    ),
    ("memory_candidates", "fk_owner_memory_candidates_ingestion_id", "ingestion_id", "ingestions"),
    ("memory_candidates", "fk_owner_memory_candidates_profile_id", "profile_id", "profiles"),
    ("memory_candidates", "fk_owner_memory_candidates_record_id", "record_id", "medical_records"),
    (
        "memory_facts",
        "fk_owner_memory_facts_attested_by_identity_id",
        "attested_by_identity_id",
        "auth_identities",
    ),
    ("memory_facts", "fk_owner_memory_facts_profile_id", "profile_id", "profiles"),
    (
        "memory_facts",
        "fk_owner_memory_facts_source_candidate_id",
        "source_candidate_id",
        "memory_candidates",
    ),
    (
        "memory_facts",
        "fk_owner_memory_facts_source_record_id",
        "source_record_id",
        "medical_records",
    ),
    (
        "memory_facts",
        "fk_owner_memory_facts_source_reference_id",
        "source_reference_id",
        "source_references",
    ),
    ("memory_facts", "fk_owner_memory_facts_superseded_by_id", "superseded_by_id", "memory_facts"),
    (
        "metric_observations",
        "fk_owner_metric_observations_attempt_id",
        "attempt_id",
        "extraction_attempts",
    ),
    (
        "metric_observations",
        "fk_owner_metric_observations_ingestion_id",
        "ingestion_id",
        "ingestions",
    ),
    ("metric_observations", "fk_owner_metric_observations_profile_id", "profile_id", "profiles"),
    (
        "metric_observations",
        "fk_owner_metric_observations_record_id",
        "record_id",
        "medical_records",
    ),
    (
        "metric_observations",
        "fk_owner_metric_observations_superseded_by_id",
        "superseded_by_id",
        "metric_observations",
    ),
    (
        "patient_evidence",
        "fk_owner_patient_evidence_attempt_id",
        "attempt_id",
        "extraction_attempts",
    ),
    ("patient_evidence", "fk_owner_patient_evidence_ingestion_id", "ingestion_id", "ingestions"),
    (
        "profile_health_context",
        "fk_owner_profile_health_context_profile_id",
        "profile_id",
        "profiles",
    ),
    (
        "source_references",
        "fk_owner_source_references_memory_candidate_id",
        "memory_candidate_id",
        "memory_candidates",
    ),
    (
        "source_references",
        "fk_owner_source_references_metadata_candidate_id",
        "metadata_candidate_id",
        "document_metadata_candidates",
    ),
    (
        "source_references",
        "fk_owner_source_references_metric_observation_id",
        "metric_observation_id",
        "metric_observations",
    ),
    ("source_references", "fk_owner_source_references_part_id", "part_id", "ingestion_parts"),
    (
        "source_references",
        "fk_owner_source_references_patient_evidence_id",
        "patient_evidence_id",
        "patient_evidence",
    ),
)


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("onboarding_status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "auth_identities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("provider_subject", sa.String(length=255), nullable=False),
        sa.Column("upstream_provider", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider", "provider_subject", name="uq_auth_identity_provider_subject"
        ),
    )
    op.create_index(
        op.f("ix_auth_identities_account_id"), "auth_identities", ["account_id"], unique=False
    )
    op.create_table(
        "profiles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("relationship", sa.String(length=80), nullable=False),
        sa.Column("sex", sa.String(length=40), nullable=True),
        sa.Column("conditions_declared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("medications_declared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_profiles_account_id"), "profiles", ["account_id"], unique=False)
    op.create_index(
        "uq_profiles_one_self_per_account",
        "profiles",
        ["account_id"],
        unique=True,
        sqlite_where=sa.text("relationship = 'self'"),
        postgresql_where=sa.text("relationship = 'self'"),
    )
    op.create_table(
        "appointments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clinician_name", sa.String(length=200), nullable=True),
        sa.Column("location", sa.String(length=240), nullable=True),
        sa.Column("reason", sa.String(length=300), nullable=True),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_appointments_account_id"), "appointments", ["account_id"], unique=False
    )
    op.create_index(
        op.f("ix_appointments_profile_id"), "appointments", ["profile_id"], unique=False
    )
    op.create_table(
        "profile_health_context",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("reported_age", sa.Integer(), nullable=True),
        sa.Column("age_reported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entered_weight", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("weight_unit", sa.String(length=2), nullable=True),
        sa.Column("normalized_weight_kg", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("weight_reported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "weight_unit IS NULL OR weight_unit IN ('kg', 'lb')",
            name="ck_profile_health_context_weight_unit",
        ),
        sa.CheckConstraint(
            "reported_age IS NOT NULL OR entered_weight IS NOT NULL",
            name="ck_profile_health_context_has_value",
        ),
        sa.CheckConstraint(
            "reported_age IS NULL OR (reported_age >= 0 AND reported_age <= 130)",
            name="ck_profile_health_context_age_range",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_profile_health_context_account_id"),
        "profile_health_context",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_profile_health_context_profile_id"),
        "profile_health_context",
        ["profile_id"],
        unique=False,
    )
    op.create_table(
        "appointment_reviews",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("appointment_id", sa.String(), nullable=False),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("stars >= 1 AND stars <= 5", name="ck_appointment_reviews_stars"),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_appointment_reviews_account_id"),
        "appointment_reviews",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_appointment_reviews_appointment_id"),
        "appointment_reviews",
        ["appointment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_appointment_reviews_profile_id"),
        "appointment_reviews",
        ["profile_id"],
        unique=False,
    )
    op.create_table(
        "ingestions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("provisional_profile_id", sa.String(), nullable=True),
        sa.Column("resolved_profile_id", sa.String(), nullable=True),
        sa.Column("resolved_by_identity_id", sa.String(), nullable=True),
        sa.Column("source_channel", sa.String(length=20), nullable=False),
        sa.Column("grouping_id", sa.String(), nullable=False),
        sa.Column("user_context", sa.Text(), nullable=True),
        sa.Column("display_filename", sa.String(length=260), nullable=True),
        sa.Column("user_renamed", sa.Boolean(), nullable=False),
        sa.Column("upload_state", sa.String(length=40), nullable=False),
        sa.Column("assignment_state", sa.String(length=40), nullable=False),
        sa.Column("extraction_state", sa.String(length=40), nullable=False),
        sa.Column("review_state", sa.String(length=40), nullable=False),
        sa.Column("patient_match_version", sa.String(length=80), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tombstoned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_channel IN ('direct_file', 'camera')", name="ck_ingestions_source_channel"
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["provisional_profile_id"],
            ["profiles.id"],
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_identity_id"],
            ["auth_identities.id"],
        ),
        sa.ForeignKeyConstraint(
            ["resolved_profile_id"],
            ["profiles.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ingestions_account_id"), "ingestions", ["account_id"], unique=False)
    op.create_index(
        op.f("ix_ingestions_provisional_profile_id"),
        "ingestions",
        ["provisional_profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ingestions_resolved_profile_id"),
        "ingestions",
        ["resolved_profile_id"],
        unique=False,
    )
    op.create_table(
        "extraction_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("ingestion_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("current_phase", sa.String(length=60), nullable=True),
        sa.Column("failure_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_id"],
            ["ingestions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_extraction_jobs_account_id"), "extraction_jobs", ["account_id"], unique=False
    )
    op.create_index(
        op.f("ix_extraction_jobs_ingestion_id"), "extraction_jobs", ["ingestion_id"], unique=False
    )
    op.create_table(
        "ingestion_parts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("ingestion_id", sa.String(), nullable=False),
        sa.Column("actor_identity_id", sa.String(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=260), nullable=False),
        sa.Column("detected_mime_type", sa.String(length=160), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_bucket", sa.String(length=120), nullable=False),
        sa.Column("object_key", sa.String(length=700), nullable=False),
        sa.Column("authorization_basis", sa.String(length=80), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["actor_identity_id"],
            ["auth_identities.id"],
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_id"],
            ["ingestions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ingestion_id", "ordinal", name="uq_ingestion_parts_ordinal"),
    )
    op.create_index(
        op.f("ix_ingestion_parts_account_id"), "ingestion_parts", ["account_id"], unique=False
    )
    op.create_index(
        op.f("ix_ingestion_parts_actor_identity_id"),
        "ingestion_parts",
        ["actor_identity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ingestion_parts_ingestion_id"), "ingestion_parts", ["ingestion_id"], unique=False
    )
    op.create_table(
        "medical_records",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("ingestion_id", sa.String(), nullable=False),
        sa.Column("display_filename", sa.String(length=260), nullable=False),
        sa.Column("record_type", sa.String(length=120), nullable=True),
        sa.Column("record_date", sa.Date(), nullable=True),
        sa.Column("issuer_name", sa.String(length=240), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_id"],
            ["ingestions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_medical_records_account_id"), "medical_records", ["account_id"], unique=False
    )
    op.create_index(
        op.f("ix_medical_records_ingestion_id"), "medical_records", ["ingestion_id"], unique=True
    )
    op.create_index(
        op.f("ix_medical_records_profile_id"), "medical_records", ["profile_id"], unique=False
    )
    op.create_table(
        "extraction_attempts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("internal_phase", sa.String(length=60), nullable=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("provider_components", sa.JSON(), nullable=False),
        sa.Column("processing_method", sa.String(length=40), nullable=True),
        sa.Column("routing_reason", sa.String(length=120), nullable=True),
        sa.Column("raw_output_bucket", sa.String(length=120), nullable=True),
        sa.Column("raw_output_object_key", sa.String(length=700), nullable=True),
        sa.Column("failure_code", sa.String(length=80), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["extraction_jobs.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "attempt_number", name="uq_extraction_attempt_number"),
    )
    op.create_index(
        op.f("ix_extraction_attempts_account_id"),
        "extraction_attempts",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_extraction_attempts_job_id"), "extraction_attempts", ["job_id"], unique=False
    )
    op.create_table(
        "document_metadata_candidates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("ingestion_id", sa.String(), nullable=False),
        sa.Column("record_id", sa.String(), nullable=True),
        sa.Column("profile_id", sa.String(), nullable=True),
        sa.Column("attempt_id", sa.String(), nullable=False),
        sa.Column("metadata_type", sa.String(length=60), nullable=False),
        sa.Column("original_value", sa.JSON(), nullable=False),
        sa.Column("submitted_value", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("review_status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["extraction_attempts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_id"],
            ["ingestions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
        ),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["medical_records.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_document_metadata_candidates_account_id"),
        "document_metadata_candidates",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_metadata_candidates_attempt_id"),
        "document_metadata_candidates",
        ["attempt_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_metadata_candidates_ingestion_id"),
        "document_metadata_candidates",
        ["ingestion_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_metadata_candidates_record_id"),
        "document_metadata_candidates",
        ["record_id"],
        unique=False,
    )
    op.create_table(
        "memory_candidates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("ingestion_id", sa.String(), nullable=False),
        sa.Column("record_id", sa.String(), nullable=True),
        sa.Column("profile_id", sa.String(), nullable=True),
        sa.Column("attempt_id", sa.String(), nullable=False),
        sa.Column("subtype", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=180), nullable=False),
        sa.Column("original_value", sa.JSON(), nullable=False),
        sa.Column("submitted_value", sa.JSON(), nullable=True),
        sa.Column("exact_condition_text", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("review_status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["extraction_attempts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_id"],
            ["ingestions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
        ),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["medical_records.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_memory_candidates_account_id"), "memory_candidates", ["account_id"], unique=False
    )
    op.create_index(
        op.f("ix_memory_candidates_attempt_id"), "memory_candidates", ["attempt_id"], unique=False
    )
    op.create_index(
        op.f("ix_memory_candidates_ingestion_id"),
        "memory_candidates",
        ["ingestion_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_memory_candidates_profile_id"), "memory_candidates", ["profile_id"], unique=False
    )
    op.create_index(
        op.f("ix_memory_candidates_record_id"), "memory_candidates", ["record_id"], unique=False
    )
    op.create_table(
        "metric_observations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("ingestion_id", sa.String(), nullable=False),
        sa.Column("record_id", sa.String(), nullable=True),
        sa.Column("profile_id", sa.String(), nullable=True),
        sa.Column("attempt_id", sa.String(), nullable=False),
        sa.Column("metric_identity", sa.String(length=160), nullable=False),
        sa.Column("label", sa.String(length=180), nullable=False),
        sa.Column("original_value", sa.JSON(), nullable=False),
        sa.Column("original_unit", sa.String(length=80), nullable=True),
        sa.Column("normalized_value", sa.JSON(), nullable=True),
        sa.Column("normalized_unit", sa.String(length=80), nullable=True),
        sa.Column("reference_range", sa.JSON(), nullable=True),
        sa.Column("flag", sa.String(length=40), nullable=True),
        sa.Column("observed_on", sa.Date(), nullable=True),
        sa.Column("body_system", sa.String(length=120), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("quality_state", sa.String(length=40), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("superseded_by_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["extraction_attempts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_id"],
            ["ingestions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
        ),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["medical_records.id"],
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_id"],
            ["metric_observations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_metric_observations_account_id"),
        "metric_observations",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_metric_observations_attempt_id"),
        "metric_observations",
        ["attempt_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_metric_observations_ingestion_id"),
        "metric_observations",
        ["ingestion_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_metric_observations_metric_identity"),
        "metric_observations",
        ["metric_identity"],
        unique=False,
    )
    op.create_index(
        op.f("ix_metric_observations_profile_id"),
        "metric_observations",
        ["profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_metric_observations_record_id"), "metric_observations", ["record_id"], unique=False
    )
    op.create_table(
        "patient_evidence",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("ingestion_id", sa.String(), nullable=False),
        sa.Column("attempt_id", sa.String(), nullable=False),
        sa.Column("extracted_name", sa.String(length=240), nullable=False),
        sa.Column("normalized_name", sa.String(length=240), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("patient_identifier", sa.String(length=160), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["extraction_attempts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_id"],
            ["ingestions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_patient_evidence_account_id"), "patient_evidence", ["account_id"], unique=False
    )
    op.create_index(
        op.f("ix_patient_evidence_attempt_id"), "patient_evidence", ["attempt_id"], unique=False
    )
    op.create_index(
        op.f("ix_patient_evidence_ingestion_id"), "patient_evidence", ["ingestion_id"], unique=False
    )
    op.create_index(
        op.f("ix_patient_evidence_normalized_name"),
        "patient_evidence",
        ["normalized_name"],
        unique=False,
    )
    op.create_table(
        "document_metadata_reviews",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=False),
        sa.Column("reviewer_identity_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("submitted_value", sa.JSON(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["document_metadata_candidates.id"],
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_identity_id"],
            ["auth_identities.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_document_metadata_reviews_account_id"),
        "document_metadata_reviews",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_metadata_reviews_candidate_id"),
        "document_metadata_reviews",
        ["candidate_id"],
        unique=False,
    )
    op.create_table(
        "memory_candidate_reviews",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=False),
        sa.Column("reviewer_identity_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("submitted_value", sa.JSON(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["memory_candidates.id"],
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_identity_id"],
            ["auth_identities.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_memory_candidate_reviews_account_id"),
        "memory_candidate_reviews",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_memory_candidate_reviews_candidate_id"),
        "memory_candidate_reviews",
        ["candidate_id"],
        unique=False,
    )
    op.create_table(
        "source_references",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("part_id", sa.String(), nullable=False),
        sa.Column("patient_evidence_id", sa.String(), nullable=True),
        sa.Column("metadata_candidate_id", sa.String(), nullable=True),
        sa.Column("metric_observation_id", sa.String(), nullable=True),
        sa.Column("memory_candidate_id", sa.String(), nullable=True),
        sa.Column("logical_page", sa.Integer(), nullable=False),
        sa.Column("native_word_ids", sa.JSON(), nullable=True),
        sa.Column("textract_block_ids", sa.JSON(), nullable=True),
        sa.Column("text_span", sa.Text(), nullable=False),
        sa.Column("bounding_polygon", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "(CASE WHEN patient_evidence_id IS NULL THEN 0 ELSE 1 END) + (CASE WHEN metadata_candidate_id IS NULL THEN 0 ELSE 1 END) + (CASE WHEN metric_observation_id IS NULL THEN 0 ELSE 1 END) + (CASE WHEN memory_candidate_id IS NULL THEN 0 ELSE 1 END) = 1",
            name="ck_source_references_one_item",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["memory_candidate_id"],
            ["memory_candidates.id"],
        ),
        sa.ForeignKeyConstraint(
            ["metadata_candidate_id"],
            ["document_metadata_candidates.id"],
        ),
        sa.ForeignKeyConstraint(
            ["metric_observation_id"],
            ["metric_observations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["part_id"],
            ["ingestion_parts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["patient_evidence_id"],
            ["patient_evidence.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_source_references_account_id"), "source_references", ["account_id"], unique=False
    )
    op.create_index(
        op.f("ix_source_references_memory_candidate_id"),
        "source_references",
        ["memory_candidate_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_references_metadata_candidate_id"),
        "source_references",
        ["metadata_candidate_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_references_metric_observation_id"),
        "source_references",
        ["metric_observation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_source_references_part_id"), "source_references", ["part_id"], unique=False
    )
    op.create_index(
        op.f("ix_source_references_patient_evidence_id"),
        "source_references",
        ["patient_evidence_id"],
        unique=False,
    )
    op.create_table(
        "memory_facts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("source_record_id", sa.String(), nullable=True),
        sa.Column("source_candidate_id", sa.String(), nullable=True),
        sa.Column("source_reference_id", sa.String(), nullable=True),
        sa.Column("attested_by_identity_id", sa.String(), nullable=True),
        sa.Column("provenance", sa.String(length=40), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("superseded_by_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["attested_by_identity_id"],
            ["auth_identities.id"],
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_candidate_id"],
            ["memory_candidates.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_record_id"],
            ["medical_records.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_reference_id"],
            ["source_references.id"],
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_id"],
            ["memory_facts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_memory_facts_account_id"), "memory_facts", ["account_id"], unique=False
    )
    op.create_index(
        op.f("ix_memory_facts_profile_id"), "memory_facts", ["profile_id"], unique=False
    )
    op.create_index(
        op.f("ix_memory_facts_source_candidate_id"),
        "memory_facts",
        ["source_candidate_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_memory_facts_source_record_id"), "memory_facts", ["source_record_id"], unique=False
    )
    op.create_table(
        "appointment_checklist_items",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), nullable=False),
        sa.Column("appointment_id", sa.String(), nullable=False),
        sa.Column("question", sa.String(length=500), nullable=False),
        sa.Column("source_fact_id", sa.String(), nullable=True),
        sa.Column("is_generic", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_fact_id"],
            ["memory_facts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_appointment_checklist_items_account_id"),
        "appointment_checklist_items",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_appointment_checklist_items_appointment_id"),
        "appointment_checklist_items",
        ["appointment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_appointment_checklist_items_profile_id"),
        "appointment_checklist_items",
        ["profile_id"],
        unique=False,
    )
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
    op.create_table(
        "storage_cleanup_intents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("object_key", sa.String(700), nullable=False, unique=True),
        sa.Column("storage_bucket", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reconcile_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
    )
    op.create_index(
        "ix_storage_cleanup_intents_account_id", "storage_cleanup_intents", ["account_id"]
    )
    op.create_index(
        "ix_storage_cleanup_intents_reconcile_after", "storage_cleanup_intents", ["reconcile_after"]
    )
    for table in ACCOUNT_TABLES:
        if table not in ("profiles", "auth_identities", "ingestions", "extraction_attempts"):
            op.create_index(f"uq_{table}_id_account", table, ["id", "account_id"], unique=True)
    for table, name, column, parent in OWNERSHIP_LINKS:
        with op.batch_alter_table(table) as batch:
            batch.create_foreign_key(name, parent, [column, "account_id"], ["id", "account_id"])
    if op.get_context().dialect.name == "postgresql":
        boundary_sql = (
            Path(__file__).resolve().parent.parent / "sql" / "20260721_private_boundary.sql"
        )
        op.execute(boundary_sql.read_text())
    # ### end Alembic commands ###


def downgrade() -> None:
    if op.get_context().dialect.name == "postgresql":
        op.execute("DROP SCHEMA IF EXISTS med_app_private CASCADE")
    for table, name, _column, _parent in reversed(OWNERSHIP_LINKS):
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(name, type_="foreignkey")
    for table in ACCOUNT_TABLES:
        if table not in ("profiles", "auth_identities", "ingestions", "extraction_attempts"):
            op.drop_index(f"uq_{table}_id_account", table_name=table)
    op.drop_table("storage_cleanup_intents")
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("ingestion_assignments")
    op.drop_table("profile_aliases")
    for table in ("profiles", "auth_identities", "ingestions", "extraction_attempts"):
        op.drop_index(f"uq_{table}_id_account", table_name=table)
    op.drop_index(
        op.f("ix_appointment_checklist_items_profile_id"), table_name="appointment_checklist_items"
    )
    op.drop_index(
        op.f("ix_appointment_checklist_items_appointment_id"),
        table_name="appointment_checklist_items",
    )
    op.drop_index(
        op.f("ix_appointment_checklist_items_account_id"), table_name="appointment_checklist_items"
    )
    op.drop_table("appointment_checklist_items")
    op.drop_index(op.f("ix_memory_facts_source_record_id"), table_name="memory_facts")
    op.drop_index(op.f("ix_memory_facts_source_candidate_id"), table_name="memory_facts")
    op.drop_index(op.f("ix_memory_facts_profile_id"), table_name="memory_facts")
    op.drop_index(op.f("ix_memory_facts_account_id"), table_name="memory_facts")
    op.drop_table("memory_facts")
    op.drop_index(op.f("ix_source_references_patient_evidence_id"), table_name="source_references")
    op.drop_index(op.f("ix_source_references_part_id"), table_name="source_references")
    op.drop_index(
        op.f("ix_source_references_metric_observation_id"), table_name="source_references"
    )
    op.drop_index(
        op.f("ix_source_references_metadata_candidate_id"), table_name="source_references"
    )
    op.drop_index(op.f("ix_source_references_memory_candidate_id"), table_name="source_references")
    op.drop_index(op.f("ix_source_references_account_id"), table_name="source_references")
    op.drop_table("source_references")
    op.drop_index(
        op.f("ix_memory_candidate_reviews_candidate_id"), table_name="memory_candidate_reviews"
    )
    op.drop_index(
        op.f("ix_memory_candidate_reviews_account_id"), table_name="memory_candidate_reviews"
    )
    op.drop_table("memory_candidate_reviews")
    op.drop_index(
        op.f("ix_document_metadata_reviews_candidate_id"), table_name="document_metadata_reviews"
    )
    op.drop_index(
        op.f("ix_document_metadata_reviews_account_id"), table_name="document_metadata_reviews"
    )
    op.drop_table("document_metadata_reviews")
    op.drop_index(op.f("ix_patient_evidence_normalized_name"), table_name="patient_evidence")
    op.drop_index(op.f("ix_patient_evidence_ingestion_id"), table_name="patient_evidence")
    op.drop_index(op.f("ix_patient_evidence_attempt_id"), table_name="patient_evidence")
    op.drop_index(op.f("ix_patient_evidence_account_id"), table_name="patient_evidence")
    op.drop_table("patient_evidence")
    op.drop_index(op.f("ix_metric_observations_record_id"), table_name="metric_observations")
    op.drop_index(op.f("ix_metric_observations_profile_id"), table_name="metric_observations")
    op.drop_index(op.f("ix_metric_observations_metric_identity"), table_name="metric_observations")
    op.drop_index(op.f("ix_metric_observations_ingestion_id"), table_name="metric_observations")
    op.drop_index(op.f("ix_metric_observations_attempt_id"), table_name="metric_observations")
    op.drop_index(op.f("ix_metric_observations_account_id"), table_name="metric_observations")
    op.drop_table("metric_observations")
    op.drop_index(op.f("ix_memory_candidates_record_id"), table_name="memory_candidates")
    op.drop_index(op.f("ix_memory_candidates_profile_id"), table_name="memory_candidates")
    op.drop_index(op.f("ix_memory_candidates_ingestion_id"), table_name="memory_candidates")
    op.drop_index(op.f("ix_memory_candidates_attempt_id"), table_name="memory_candidates")
    op.drop_index(op.f("ix_memory_candidates_account_id"), table_name="memory_candidates")
    op.drop_table("memory_candidates")
    op.drop_index(
        op.f("ix_document_metadata_candidates_record_id"), table_name="document_metadata_candidates"
    )
    op.drop_index(
        op.f("ix_document_metadata_candidates_ingestion_id"),
        table_name="document_metadata_candidates",
    )
    op.drop_index(
        op.f("ix_document_metadata_candidates_attempt_id"),
        table_name="document_metadata_candidates",
    )
    op.drop_index(
        op.f("ix_document_metadata_candidates_account_id"),
        table_name="document_metadata_candidates",
    )
    op.drop_table("document_metadata_candidates")
    op.drop_index(op.f("ix_extraction_attempts_job_id"), table_name="extraction_attempts")
    op.drop_index(op.f("ix_extraction_attempts_account_id"), table_name="extraction_attempts")
    op.drop_table("extraction_attempts")
    op.drop_index(op.f("ix_medical_records_profile_id"), table_name="medical_records")
    op.drop_index(op.f("ix_medical_records_ingestion_id"), table_name="medical_records")
    op.drop_index(op.f("ix_medical_records_account_id"), table_name="medical_records")
    op.drop_table("medical_records")
    op.drop_index(op.f("ix_ingestion_parts_ingestion_id"), table_name="ingestion_parts")
    op.drop_index(op.f("ix_ingestion_parts_actor_identity_id"), table_name="ingestion_parts")
    op.drop_index(op.f("ix_ingestion_parts_account_id"), table_name="ingestion_parts")
    op.drop_table("ingestion_parts")
    op.drop_index(op.f("ix_extraction_jobs_ingestion_id"), table_name="extraction_jobs")
    op.drop_index(op.f("ix_extraction_jobs_account_id"), table_name="extraction_jobs")
    op.drop_table("extraction_jobs")
    op.drop_index(op.f("ix_ingestions_resolved_profile_id"), table_name="ingestions")
    op.drop_index(op.f("ix_ingestions_provisional_profile_id"), table_name="ingestions")
    op.drop_index(op.f("ix_ingestions_account_id"), table_name="ingestions")
    op.drop_table("ingestions")
    op.drop_index(op.f("ix_appointment_reviews_profile_id"), table_name="appointment_reviews")
    op.drop_index(op.f("ix_appointment_reviews_appointment_id"), table_name="appointment_reviews")
    op.drop_index(op.f("ix_appointment_reviews_account_id"), table_name="appointment_reviews")
    op.drop_table("appointment_reviews")
    op.drop_index(op.f("ix_profile_health_context_profile_id"), table_name="profile_health_context")
    op.drop_index(op.f("ix_profile_health_context_account_id"), table_name="profile_health_context")
    op.drop_table("profile_health_context")
    op.drop_index(op.f("ix_appointments_profile_id"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_account_id"), table_name="appointments")
    op.drop_table("appointments")
    op.drop_index(
        "uq_profiles_one_self_per_account",
        table_name="profiles",
        sqlite_where=sa.text("relationship = 'self'"),
        postgresql_where=sa.text("relationship = 'self'"),
    )
    op.drop_index(op.f("ix_profiles_account_id"), table_name="profiles")
    op.drop_table("profiles")
    op.drop_index(op.f("ix_auth_identities_account_id"), table_name="auth_identities")
    op.drop_table("auth_identities")
    op.drop_table("accounts")
    # ### end Alembic commands ###
