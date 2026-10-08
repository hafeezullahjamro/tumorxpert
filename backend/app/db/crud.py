from __future__ import annotations

import uuid
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import BACKEND_ROOT
from . import models, schemas


def create_user(db: Session, data: schemas.UserCreate, hashed_password: str) -> models.User:
    user = models.User(email=data.email, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.scalar(select(models.User).where(models.User.email == email))


def create_study(db: Session, data: schemas.StudyCreate) -> models.Study:
    study = models.Study(
        name=data.name,
        owner_user_id=data.owner_user_id,
        sequences_present=data.sequences_present,
        qc_flags=data.qc_flags,
    )
    db.add(study)
    db.commit()
    db.refresh(study)
    return study


def list_studies(db: Session, owner_user_id: Optional[int] = None) -> list[models.Study]:
    stmt = select(models.Study).order_by(models.Study.created_at.desc())
    if owner_user_id is not None:
        stmt = stmt.where(models.Study.owner_user_id == owner_user_id)
    return list(db.scalars(stmt))


def get_study(db: Session, study_id: uuid.UUID) -> Optional[models.Study]:
    return db.get(models.Study, study_id)


def delete_study(db: Session, study: models.Study) -> None:
    db.delete(study)
    db.commit()


def add_file(
    db: Session,
    *,
    study_id: uuid.UUID,
    kind: str,
    path: str,
    size_bytes: int,
    checksum: str,
) -> models.FileArtifact:
    artifact_path = Path(path)
    absolute_alias: str | None = None
    if artifact_path.is_absolute():
        try:
            path = str(artifact_path.relative_to(BACKEND_ROOT))
            absolute_alias = str(artifact_path)
        except ValueError:
            # External storage locations retain their absolute paths.
            pass
    else:
        absolute_alias = str(BACKEND_ROOT / artifact_path)
    existing = db.scalar(
        select(models.FileArtifact).where(
            models.FileArtifact.study_id == study_id,
            models.FileArtifact.path == path,
        )
    )
    if existing is None and absolute_alias is not None:
        existing = db.scalar(
            select(models.FileArtifact).where(
                models.FileArtifact.study_id == study_id,
                models.FileArtifact.path == absolute_alias,
            )
        )
    if existing:
        existing.path = path
        existing.kind = kind
        existing.size_bytes = size_bytes
        existing.checksum = checksum
        file_obj = existing
    else:
        file_obj = models.FileArtifact(
            study_id=study_id,
            kind=kind,
            path=path,
            size_bytes=size_bytes,
            checksum=checksum,
        )
        db.add(file_obj)
    db.commit()
    db.refresh(file_obj)
    return file_obj


def list_files(db: Session, study_id: uuid.UUID) -> list[models.FileArtifact]:
    stmt = select(models.FileArtifact).where(models.FileArtifact.study_id == study_id)
    return list(db.scalars(stmt))


def get_file(db: Session, file_id: int) -> Optional[models.FileArtifact]:
    return db.get(models.FileArtifact, file_id)


def get_file_by_kind(db: Session, study_id: uuid.UUID, kind: str) -> Optional[models.FileArtifact]:
    stmt = (
        select(models.FileArtifact)
        .where(
            models.FileArtifact.study_id == study_id,
            models.FileArtifact.kind == kind,
        )
        .order_by(models.FileArtifact.created_at.desc())
    )
    return db.scalar(stmt)


def upsert_metrics(db: Session, study_id: uuid.UUID, payload: dict) -> models.Metric:
    payload = dict(payload)
    payload.pop("low_confidence_fraction", None)
    payload.pop("model_agreement_wt_dice", None)
    payload.pop("label_disagreement_ml", None)
    confidence_summary = payload.pop("confidence_summary", None)
    if confidence_summary is not None:
        payload["confidence_score_mock"] = confidence_summary
    payload.setdefault("hd95_mock", 0.0)
    payload.setdefault("dice_mock", 0.0)
    payload.setdefault("confidence_score_mock", 0.0)

    metrics = db.scalar(
        select(models.Metric).where(models.Metric.study_id == study_id)
    )
    if metrics:
        for key, value in payload.items():
            setattr(metrics, key, value)
    else:
        metrics = models.Metric(study_id=study_id, **payload)
        db.add(metrics)
    db.commit()
    db.refresh(metrics)
    return metrics


def get_metrics(db: Session, study_id: uuid.UUID) -> Optional[models.Metric]:
    return db.scalar(
        select(models.Metric).where(models.Metric.study_id == study_id)
    )


def create_comparison(
    db: Session,
    *,
    study_a_id: uuid.UUID,
    study_b_id: uuid.UUID,
    volume_a_ml: float,
    volume_b_ml: float,
    pct_change: float,
    rano_label: str,
) -> models.Comparison:
    comparison = models.Comparison(
        study_a_id=study_a_id,
        study_b_id=study_b_id,
        volume_a_ml=volume_a_ml,
        volume_b_ml=volume_b_ml,
        pct_change=pct_change,
        rano_label=rano_label,
    )
    db.add(comparison)
    db.commit()
    db.refresh(comparison)
    return comparison


def list_comparisons(
    db: Session, *, study_id: Optional[uuid.UUID] = None
) -> list[models.Comparison]:
    stmt = select(models.Comparison).order_by(models.Comparison.created_at.desc())
    if study_id:
        stmt = stmt.where(
            (models.Comparison.study_a_id == study_id)
            | (models.Comparison.study_b_id == study_id)
        )
    return list(db.scalars(stmt))
