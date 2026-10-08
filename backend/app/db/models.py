from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    UUID,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    studies: Mapped[list["Study"]] = relationship(back_populates="owner")


StudyStatus = Enum(
    "UPLOADED",
    "PROCESSING",
    "DONE",
    "FAILED",
    name="study_status",
)


class Study(Base):
    __tablename__ = "studies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(StudyStatus, default="UPLOADED", nullable=False)
    sequences_present: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    qc_flags: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    owner: Mapped[Optional[User]] = relationship(back_populates="studies")
    files: Mapped[list["FileArtifact"]] = relationship(
        back_populates="study", cascade="all, delete-orphan"
    )
    metrics: Mapped[Optional["Metric"]] = relationship(
        back_populates="study", uselist=False, cascade="all, delete-orphan"
    )
    comparisons_a: Mapped[list["Comparison"]] = relationship(
        back_populates="study_a",
        cascade="all, delete-orphan",
        foreign_keys="[Comparison.study_a_id]",
    )
    comparisons_b: Mapped[list["Comparison"]] = relationship(
        back_populates="study_b",
        cascade="all, delete-orphan",
        foreign_keys="[Comparison.study_b_id]",
    )


class FileArtifact(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studies.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(
        Enum(
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
        ),
        nullable=False,
    )
    path: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    study: Mapped[Study] = relationship(back_populates="files")

    __table_args__ = (
        UniqueConstraint("study_id", "path", name="uq_file_study_path"),
    )


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    study_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studies.id", ondelete="CASCADE"), nullable=False
    )
    wt_ml: Mapped[float] = mapped_column(Float, nullable=False)
    tc_ml: Mapped[float] = mapped_column(Float, nullable=False)
    et_ml: Mapped[float] = mapped_column(Float, nullable=False)
    edema_core_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    hd95_mock: Mapped[float] = mapped_column(Float, nullable=False)
    dice_mock: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score_mock: Mapped[float] = mapped_column(Float, nullable=False)
    runtime_sec: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    study: Mapped[Study] = relationship(back_populates="metrics")

    __table_args__ = (
        UniqueConstraint("study_id", name="uq_metrics_study"),
    )


class Comparison(Base):
    __tablename__ = "comparisons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    study_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studies.id", ondelete="CASCADE"), nullable=False
    )
    study_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studies.id", ondelete="CASCADE"), nullable=False
    )
    volume_a_ml: Mapped[float] = mapped_column(Float, nullable=False)
    volume_b_ml: Mapped[float] = mapped_column(Float, nullable=False)
    pct_change: Mapped[float] = mapped_column(Float, nullable=False)
    rano_label: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    study_a: Mapped[Study] = relationship(
        back_populates="comparisons_a", foreign_keys=[study_a_id]
    )
    study_b: Mapped[Study] = relationship(
        back_populates="comparisons_b", foreign_keys=[study_b_id]
    )

    __table_args__ = (
        CheckConstraint("study_a_id <> study_b_id", name="ck_distinct_studies"),
    )
