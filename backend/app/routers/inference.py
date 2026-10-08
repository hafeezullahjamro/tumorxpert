from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.config import Settings, get_settings
from ..db import crud
from ..db.base import get_db
from ..services.dicom_seg_stub import create_dicom_seg_stub
from ..services.imaging import (
    generate_confidence_previews,
    generate_modality_previews,
    generate_segmentation_previews,
    generate_thumbnails,
)
from ..services.inference_pipeline import FILE_KIND_BY_MODALITY, run_study_pipeline
from ..services.pdf_report import generate_pdf_report
from ..services.postprocess import export_mesh, export_metrics_json
from ..services.storage import StorageService, compute_checksum

router = APIRouter()


@router.post("/{study_id}/run")
def run_inference(
    study_id: uuid.UUID,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    study = crud.get_study(db, study_id)
    if not study:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study not found.")

    storage = StorageService(settings)
    study.status = "PROCESSING"
    db.commit()

    try:
        processed_root = storage.processed_root(str(study.id))
        processed_root.mkdir(parents=True, exist_ok=True)
        pipeline_result = run_study_pipeline(
            study_root=storage.study_root(str(study.id)),
            processed_root=processed_root,
            settings=settings,
        )
        thumbs_dir = processed_root / "thumbnails"
        thumbnails = {
            **generate_thumbnails(pipeline_result.reference_volume, thumbs_dir),
            **generate_modality_previews(
                pipeline_result.completed_modalities,
                thumbs_dir,
            ),
        }
        model_outputs = getattr(pipeline_result, "model_outputs", {}) or {}
        for output_name, output in model_outputs.items():
            thumbnails.update(
                generate_segmentation_previews(
                    pipeline_result.reference_volume,
                    output.labels,
                    thumbs_dir,
                    prefix=output_name,
                )
            )
            thumbnails.update(
                generate_confidence_previews(
                    output.confidence,
                    thumbs_dir,
                    prefix=output_name,
                )
            )
        metrics = pipeline_result.metrics
        crud.upsert_metrics(db, study.id, metrics)

        exports_root = storage.exports_root(str(study.id))
        exports_root.mkdir(parents=True, exist_ok=True)
        metrics_json_path = exports_root / "metrics.json"
        export_metrics_json(metrics, metrics_json_path)

        mesh_path = exports_root / "tumor_mesh.stl"
        export_mesh(pipeline_result.labels, mesh_path, spacing=tuple(pipeline_result.reference_header.get_zooms()[:3]))

        dicom_seg_path = exports_root / "segmentation.dcm"
        create_dicom_seg_stub(str(study.id), metrics, dicom_seg_path)

        pdf_path = exports_root / "report.pdf"
        generate_pdf_report(
            app_name=settings.app_name,
            study_name=study.name,
            study_id=str(study.id),
            sequences=study.sequences_present,
            metrics=metrics,
            model_metrics=getattr(pipeline_result, "model_metrics", {}),
            segmentation_backend=getattr(pipeline_result, "segmentation_backend", "ensemble"),
            qc_flags=study.qc_flags,
            thumbnails=thumbnails,
            output_path=pdf_path,
            generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        )

        for kind, path in (
            ("NIFTI", pipeline_result.reference_path),
            ("SEG_NIFTI", pipeline_result.segmentation_path),
            ("NIFTI", pipeline_result.confidence_path),
            ("JSON", metrics_json_path),
            ("STL", mesh_path),
            ("SEG_DICOM", dicom_seg_path),
            ("PDF", pdf_path),
        ):
            crud.add_file(
                db,
                study_id=study.id,
                kind=kind,
                path=str(path),
                size_bytes=path.stat().st_size,
                checksum=compute_checksum(path.read_bytes()),
            )

        for output_name, output in model_outputs.items():
            if output_name == "ensemble":
                continue
            for path in (output.segmentation_path, output.confidence_path):
                crud.add_file(
                    db,
                    study_id=study.id,
                    kind="NIFTI",
                    path=str(path),
                    size_bytes=path.stat().st_size,
                    checksum=compute_checksum(path.read_bytes()),
                )

        for modality, path in pipeline_result.synthesized_paths.items():
            crud.add_file(
                db,
                study_id=study.id,
                kind=FILE_KIND_BY_MODALITY[modality],
                path=str(path),
                size_bytes=path.stat().st_size,
                checksum=compute_checksum(path.read_bytes()),
            )

        for name, thumb_path in thumbnails.items():
            crud.add_file(
                db,
                study_id=study.id,
                kind="PNG",
                path=str(thumb_path),
                size_bytes=thumb_path.stat().st_size,
                checksum=compute_checksum(thumb_path.read_bytes()),
            )

        study.status = "DONE"
        db.commit()
    except Exception as exc:
        # A failed commit leaves the session unusable until it is rolled back.
        # Recover it before persisting the failed status.
        db.rollback()
        study.status = "FAILED"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}") from exc

    return {"status": study.status, "metrics": metrics}
