from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..core.config import Settings, get_settings
from ..core.paths import resolve_artifact_path
from ..db import crud
from ..db.base import get_db

router = APIRouter()


def _serve_file(path: Path, filename: str, media_type: str) -> FileResponse:
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not available.")
    return FileResponse(
        path,
        filename=filename,
        media_type=media_type,
        content_disposition_type="inline" if media_type == "application/pdf" else "attachment",
    )


@router.get("/{study_id}/export/pdf")
def export_pdf(study_id: uuid.UUID, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    record = crud.get_file_by_kind(db, study_id, "PDF")
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF not generated yet.")
    return _serve_file(resolve_artifact_path(record.path, settings), filename="report.pdf", media_type="application/pdf")


@router.get("/{study_id}/export/seg")
def export_segmentation(study_id: uuid.UUID, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    record = crud.get_file_by_kind(db, study_id, "SEG_DICOM")
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segmentation not generated yet.")
    path = resolve_artifact_path(record.path, settings)
    return _serve_file(path, filename=path.name, media_type="application/octet-stream")


@router.get("/{study_id}/export/json")
def export_metrics_json(study_id: uuid.UUID, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    record = crud.get_file_by_kind(db, study_id, "JSON")
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metrics JSON not available.")
    return _serve_file(resolve_artifact_path(record.path, settings), filename="metrics.json", media_type="application/json")


@router.get("/{study_id}/export/stl")
def export_mesh(study_id: uuid.UUID, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    record = crud.get_file_by_kind(db, study_id, "STL")
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mesh not available.")
    return _serve_file(resolve_artifact_path(record.path, settings), filename="tumor_mesh.stl", media_type="model/stl")
