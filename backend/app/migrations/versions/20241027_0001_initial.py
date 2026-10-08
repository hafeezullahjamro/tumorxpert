"""initial schema

Revision ID: 20241027_0001
Revises:
Create Date: 2025-10-27 17:48:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20241027_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    study_status = sa.Enum("UPLOADED", "PROCESSING", "DONE", "FAILED", name="study_status")
    file_kind = sa.Enum(
        "T1",
        "T1CE",
        "T2",
        "FLAIR",
        "NIFTI",
        "DICOM_ZIP",
        "SEG_NIFTI",
        "SEG_DICOM",
        "PDF",
        "JSON",
        "STL",
        "PNG",
        name="file_kind",
    )
    #/study_status.create(op.get_bind(), checkfirst=True)
    #/file_kind.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "studies",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", study_status, nullable=False),
        sa.Column("sequences_present", sa.JSON(), nullable=False),
        sa.Column("qc_flags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "files",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("study_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", file_kind, nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["study_id"], ["studies.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("study_id", "path", name="uq_file_study_path"),
    )

    op.create_table(
        "metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("study_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("wt_ml", sa.Float(), nullable=False),
        sa.Column("tc_ml", sa.Float(), nullable=False),
        sa.Column("et_ml", sa.Float(), nullable=False),
        sa.Column("edema_core_ratio", sa.Float(), nullable=False),
        sa.Column("hd95_mock", sa.Float(), nullable=False),
        sa.Column("dice_mock", sa.Float(), nullable=False),
        sa.Column("confidence_score_mock", sa.Float(), nullable=False),
        sa.Column("runtime_sec", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["study_id"], ["studies.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("study_id", name="uq_metrics_study"),
    )

    op.create_table(
        "comparisons",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("study_a_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("study_b_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("volume_a_ml", sa.Float(), nullable=False),
        sa.Column("volume_b_ml", sa.Float(), nullable=False),
        sa.Column("pct_change", sa.Float(), nullable=False),
        sa.Column("rano_label", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["study_a_id"], ["studies.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["study_b_id"], ["studies.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("study_a_id <> study_b_id", name="ck_distinct_studies"),
    )


def downgrade() -> None:
    op.drop_table("comparisons")
    op.drop_table("metrics")
    op.drop_table("files")
    op.drop_table("studies")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS study_status")
    op.execute("DROP TYPE IF EXISTS file_kind")
