from __future__ import annotations

import io
import json
import tarfile
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..core.config import Settings, get_settings
from ..core.paths import resolve_artifact_path
from ..db import crud, schemas
from ..db.base import get_db
from ..services.preprocess import convert_dicom_zip_to_nifti_payloads
from ..services.qc import detect_sequences_from_filenames, modality_from_filename, qc_assess
from ..services.storage import StorageService

router = APIRouter()

FILE_KIND_BY_MODALITY = {
    "flair": "FLAIR",
    "t1": "T1",
    "t1ce": "T1CE",
    "t2": "T2",
}


def _storage(settings: Settings) -> StorageService:
    return StorageService(settings)


def _is_supported_nifti(filename: str) -> bool:
    normalized = filename.lower()
    return normalized.endswith(".nii") or normalized.endswith(".nii.gz")


def _is_auxiliary_nifti(filename: str) -> bool:
    normalized = Path(filename).name.lower()
    return normalized.endswith("_seg.nii") or normalized.endswith("_seg.nii.gz")


def _is_tar_archive(filename: str) -> bool:
    normalized = filename.lower()
    return normalized.endswith(".tar") or normalized.endswith(".tar.gz") or normalized.endswith(".tgz")


def _strip_study_suffix(filename: str) -> str:
    stem = Path(filename).name
    for suffix in (".tar.gz", ".tgz", ".tar", ".nii.gz", ".nii"):
        if stem.lower().endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    for suffix in ("_0000", "_0001", "_0002", "_0003", "_flair", "_t1ce", "_t1", "_t2", "_seg"):
        if stem.lower().endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return stem


def _extract_tar_payloads(filename: str, data: bytes) -> list[tuple[str, bytes]]:
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
            payloads: list[tuple[str, bytes]] = []
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                member_name = Path(member.name).name
                if not _is_supported_nifti(member_name):
                    continue
                if _is_auxiliary_nifti(member_name):
                    continue
                extracted = archive.extractfile(member)
                if extracted is None:
                    continue
                payloads.append((member_name, extracted.read()))
    except tarfile.TarError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid TAR archive: {exc}") from exc
    if not payloads:
        raise HTTPException(
            status_code=400,
            detail="TAR archive does not contain any supported NIfTI modality files.",
        )
    return payloads


def _extract_zip_payloads(filename: str, data: bytes) -> tuple[list[tuple[str, bytes, str]], bool]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            payloads: list[tuple[str, bytes, str]] = []
            nifti_members = []
            for member in archive.infolist():
                if member.is_dir():
                    continue
                member_name = Path(member.filename).name
                if _is_supported_nifti(member_name):
                    nifti_members.append(member)

            if nifti_members:
                for member in nifti_members:
                    member_name = Path(member.filename).name
                    if _is_auxiliary_nifti(member_name):
                        continue
                    modality = modality_from_filename(member_name)
                    if not modality:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Unable to detect modality from '{member_name}' inside ZIP archive.",
                        )
                    payloads.append((member_name, archive.read(member), modality))
                return payloads, False
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail=f"Invalid ZIP archive: {exc}") from exc

    try:
        payloads, _ = convert_dicom_zip_to_nifti_payloads(filename, data)
        return payloads, True
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/upload", response_model=schemas.StudyRead)
async def upload_study(
    *,
    name: Optional[str] = Form(None),
    owner_user_id: Optional[int] = Form(None),
    files: list[UploadFile] = File(default_factory=list),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    uploads = [*files, *([file] if file is not None else [])]
    if not uploads:
        raise HTTPException(status_code=400, detail="Upload at least one NIfTI modality file.")

    upload_payloads: list[tuple[str, bytes, str]] = []
    original_archives: list[tuple[str, bytes, str]] = []
    seen_modalities: set[str] = set()
    filenames: list[str] = []

    for upload in uploads:
        if not upload.filename:
            raise HTTPException(status_code=400, detail="Uploaded file missing filename.")
        filename = upload.filename
        data = await upload.read()
        file_ext = filename.lower()
        if file_ext.endswith(".zip"):
            archive_payloads_3, is_dicom_zip = _extract_zip_payloads(filename, data)
            if is_dicom_zip:
                original_archives.append((filename, data, "DICOM_ZIP"))
            archive_payloads: list[tuple[str, bytes, str] | tuple[str, bytes]] = archive_payloads_3
        elif _is_tar_archive(filename):
            archive_payloads = _extract_tar_payloads(filename, data)
        elif _is_supported_nifti(filename):
            if _is_auxiliary_nifti(filename):
                continue
            archive_payloads = [(filename, data)]
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Upload BraTS-style NIfTI files, DICOM ZIP, or a TAR archive containing them.",
            )

        for payload in archive_payloads:
            if len(payload) == 3:
                payload_name, payload_data, modality = payload
            else:
                payload_name, payload_data = payload
                modality = modality_from_filename(payload_name)
            filenames.append(payload_name)
            if not modality:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Unable to detect modality from '{payload_name}'. Supported names include "
                        "'*_0000.nii.gz' to '*_0003.nii.gz' and '*_flair.nii.gz'/'*_t1.nii.gz'/'*_t1ce.nii.gz'/'*_t2.nii.gz'."
                    ),
                )
            if modality in seen_modalities:
                raise HTTPException(
                    status_code=400,
                    detail=f"Duplicate modality uploaded for '{modality}'. Upload only one file per modality.",
                )
            seen_modalities.add(modality)
            upload_payloads.append((payload_name, payload_data, modality))

    if not upload_payloads:
        raise HTTPException(
            status_code=400,
            detail="No supported MRI modality files were found in the upload.",
        )

    sequences = detect_sequences_from_filenames(filenames)
    qc_flags = qc_assess(sequences)

    inferred_name = name
    if not inferred_name:
        inferred_name = _strip_study_suffix(filenames[0])

    study = crud.create_study(
        db,
        schemas.StudyCreate(
            name=inferred_name or f"Study {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            owner_user_id=owner_user_id,
            sequences_present=sequences,
            qc_flags=qc_flags,
        ),
    )

    storage = _storage(settings)
    for filename, data, kind in original_archives:
        stored = storage.save_upload_bytes(
            str(study.id),
            data=data,
            filename=filename,
            kind=kind,
        )
        crud.add_file(
            db,
            study_id=study.id,
            kind=kind,
            path=str(stored.path),
            size_bytes=stored.size_bytes,
            checksum=stored.checksum,
        )

    for filename, data, modality in upload_payloads:
        stored = storage.save_upload_bytes(
            str(study.id),
            data=data,
            filename=filename or f"{modality}.nii.gz",
            kind=FILE_KIND_BY_MODALITY[modality],
        )
        crud.add_file(
            db,
            study_id=study.id,
            kind=FILE_KIND_BY_MODALITY[modality],
            path=str(stored.path),
            size_bytes=stored.size_bytes,
            checksum=stored.checksum,
        )

    return schemas.StudyRead.model_validate(study)


@router.get("", response_model=list[schemas.StudyRead])
def list_studies(
    *,
    owner_user_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    studies = crud.list_studies(db, owner_user_id=owner_user_id)
    return [schemas.StudyRead.model_validate(study) for study in studies]


@router.get("/{study_id}", response_model=schemas.StudyRead)
def get_study(
    study_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    study = crud.get_study(db, study_id)
    if not study:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study not found.")
    return schemas.StudyRead.model_validate(study)


@router.get("/{study_id}/files", response_model=list[schemas.FileArtifactRead])
def list_study_files(
    study_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    study = crud.get_study(db, study_id)
    if not study:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study not found.")
    files = crud.list_files(db, study_id)
    return [schemas.FileArtifactRead.model_validate(file) for file in files]


@router.get("/{study_id}/files/{file_id}/content")
def get_study_file_content(
    study_id: uuid.UUID,
    file_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    file_record = crud.get_file(db, file_id)
    if not file_record or file_record.study_id != study_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    path = resolve_artifact_path(file_record.path, settings)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file is missing.")
    media_type = "image/png" if file_record.kind == "PNG" else "application/octet-stream"
    return FileResponse(path, filename=path.name, media_type=media_type)


@router.get("/{study_id}/metrics", response_model=schemas.MetricRead)
def get_study_metrics(
    study_id: uuid.UUID,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    metrics_file = crud.get_file_by_kind(db, study_id, "JSON")
    if metrics_file:
        path = resolve_artifact_path(metrics_file.path, settings)
        if path.exists():
            payload = json.loads(path.read_text())
            return schemas.MetricRead(
                wt_ml=float(payload.get("wt_ml", 0.0)),
                tc_ml=float(payload.get("tc_ml", 0.0)),
                et_ml=float(payload.get("et_ml", 0.0)),
                edema_core_ratio=float(payload.get("edema_core_ratio", 0.0)),
                confidence_summary=float(payload.get("confidence_summary", 0.0)),
                low_confidence_fraction=float(payload.get("low_confidence_fraction", 0.0)),
                model_agreement_wt_dice=(
                    float(payload["model_agreement_wt_dice"])
                    if "model_agreement_wt_dice" in payload
                    else None
                ),
                label_disagreement_ml=(
                    float(payload["label_disagreement_ml"])
                    if "label_disagreement_ml" in payload
                    else None
                ),
                runtime_sec=float(payload.get("runtime_sec", 0.0)),
                created_at=metrics_file.created_at,
            )

    metrics = crud.get_metrics(db, study_id)
    if not metrics:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metrics not available.")
    return schemas.MetricRead(
        wt_ml=metrics.wt_ml,
        tc_ml=metrics.tc_ml,
        et_ml=metrics.et_ml,
        edema_core_ratio=metrics.edema_core_ratio,
        confidence_summary=metrics.confidence_score_mock,
        low_confidence_fraction=0.0,
        model_agreement_wt_dice=None,
        label_disagreement_ml=None,
        runtime_sec=metrics.runtime_sec,
        created_at=metrics.created_at,
    )


@router.delete("/{study_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_study(
    study_id: uuid.UUID,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    study = crud.get_study(db, study_id)
    if not study:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study not found.")
    storage = _storage(settings)
    storage.remove_study(str(study.id))
    crud.delete_study(db, study)
    return None
