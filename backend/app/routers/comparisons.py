from __future__ import annotations

import uuid

import nibabel as nib
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.config import Settings, get_settings
from ..core.paths import resolve_artifact_path
from ..db import crud, schemas
from ..db.base import get_db
from ..services.longitudinal import compute_pct_change, create_change_map, rano_label

router = APIRouter()


@router.post("/compare", response_model=schemas.ComparisonRead)
def compare_studies(
    payload: schemas.ComparisonCreate,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    if payload.study_a_id == payload.study_b_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select two different studies to compare.",
        )

    study_a = crud.get_study(db, payload.study_a_id)
    study_b = crud.get_study(db, payload.study_b_id)
    if not study_a or not study_b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or both studies not found.")

    metrics_a = crud.get_metrics(db, payload.study_a_id)
    metrics_b = crud.get_metrics(db, payload.study_b_id)
    if not metrics_a or not metrics_b:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Run inference on both studies before comparing.",
        )

    seg_a_record = crud.get_file_by_kind(db, payload.study_a_id, "SEG_NIFTI")
    seg_b_record = crud.get_file_by_kind(db, payload.study_b_id, "SEG_NIFTI")
    if not seg_a_record or not seg_b_record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Segmentation artifacts missing.")

    seg_a_path = resolve_artifact_path(seg_a_record.path, settings)
    seg_b_path = resolve_artifact_path(seg_b_record.path, settings)
    if not seg_a_path.is_file() or not seg_b_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored segmentation artifact is missing.")

    image_a = nib.load(seg_a_path)
    image_b = nib.load(seg_b_path)
    if image_a.shape != image_b.shape or not np.allclose(image_a.affine, image_b.affine):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Study segmentations must have matching image dimensions and spatial alignment before comparison.",
        )

    change_map_dir = seg_b_path.parent
    change_map_path = change_map_dir / f"change_map_{payload.study_a_id}_{payload.study_b_id}.npy"
    seg_a = image_a.get_fdata().astype(int)
    seg_b = image_b.get_fdata().astype(int)
    create_change_map(seg_a, seg_b, change_map_path)

    pct = compute_pct_change(metrics_a.wt_ml, metrics_b.wt_ml)
    label = rano_label(pct)
    comparison = crud.create_comparison(
        db,
        study_a_id=payload.study_a_id,
        study_b_id=payload.study_b_id,
        volume_a_ml=metrics_a.wt_ml,
        volume_b_ml=metrics_b.wt_ml,
        pct_change=pct,
        rano_label=label,
    )

    return schemas.ComparisonRead.model_validate(comparison)
