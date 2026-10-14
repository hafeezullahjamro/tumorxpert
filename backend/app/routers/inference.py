from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import update

from ..core.config import Settings, get_settings
from ..db import crud
from ..db.models import Study
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
from ..services.progress import ProgressReporter
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
    progress = ProgressReporter(db.get_bind(), study.id)
    claimed = db.execute(update(Study).where(Study.id == study.id, Study.status != "PROCESSING")
                         .values(status="PROCESSING", progress=progress.snapshot))
    if claimed.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="This study is already processing.")
    db.commit()

    try:
        processed_root = storage.processed_root(str(study.id))
        processed_root.mkdir(parents=True, exist_ok=True)
        pipeline_result = run_study_pipeline(
            study_root=storage.study_root(str(study.id)),
            processed_root=processed_root,
            settings=settings,
            progress=progress,
        )
        model_outputs = getattr(pipeline_result, "model_outputs", {}) or {}
        progress.children("previews", [("previews.scan", "Render MRI thumbnails"), ("previews.modalities", "Render modality previews")]
                          + [(f"previews.{name}.{kind}", f"Render {name} {kind} previews") for name in model_outputs for kind in ("segmentation", "confidence")])
        progress.update("previews.scan", force=True)
        thumbs_dir = processed_root / "thumbnails"
        thumbnails = generate_thumbnails(pipeline_result.reference_volume, thumbs_dir)
        progress.done("previews.scan")
        progress.update("previews.modalities", force=True)
        thumbnails.update(generate_modality_previews(pipeline_result.completed_modalities, thumbs_dir))
        progress.done("previews.modalities")
        for output_name, output in model_outputs.items():
            progress.update(f"previews.{output_name}.segmentation", force=True)
            thumbnails.update(
                generate_segmentation_previews(
                    pipeline_result.reference_volume,
                    output.labels,
                    thumbs_dir,
                    prefix=output_name,
                )
            )
            progress.done(f"previews.{output_name}.segmentation")
            progress.update(f"previews.{output_name}.confidence", force=True)
            thumbnails.update(
                generate_confidence_previews(
                    output.confidence,
                    thumbs_dir,
                    prefix=output_name,
                )
            )
            progress.done(f"previews.{output_name}.confidence")
        metrics = pipeline_result.metrics

        progress.children("exports", [("exports.json", "Write metrics JSON"), ("exports.mesh", "Generate tumor mesh"),
                                      ("exports.metadata", "Write segmentation metadata"), ("exports.pdf", "Generate PDF report")])
        exports_root = storage.exports_root(str(study.id))
        exports_root.mkdir(parents=True, exist_ok=True)
        metrics_json_path = exports_root / "metrics.json"
        progress.update("exports.json", force=True)
        export_metrics_json(metrics, metrics_json_path)
        progress.done("exports.json")

        mesh_path = exports_root / "tumor_mesh.stl"
        progress.update("exports.mesh", force=True)
        export_mesh(pipeline_result.labels, mesh_path, spacing=tuple(pipeline_result.reference_header.get_zooms()[:3]))
        progress.done("exports.mesh")

        dicom_seg_path = exports_root / "segmentation.dcm"
        progress.update("exports.metadata", detail="Metadata placeholder; this is not a clinical DICOM-SEG file.", force=True)
        create_dicom_seg_stub(str(study.id), metrics, dicom_seg_path)
        progress.done("exports.metadata")

        pdf_path = exports_root / "report.pdf"
        progress.update("exports.pdf", force=True)
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
        progress.done("exports.pdf")
        artifact_count = 7 + sum(2 for name in model_outputs if name != "ensemble") + len(pipeline_result.synthesized_paths) + len(thumbnails)
        saved = 0
        progress.update("persist", 0, artifact_count + 1, unit="records", force=True)
        crud.upsert_metrics(db, study.id, metrics)
        saved += 1
        progress.update("persist", saved, artifact_count + 1, unit="records")

        def save_artifact(kind, path):
            nonlocal saved
            crud.add_file(db, study_id=study.id, kind=kind, path=str(path),
                          size_bytes=path.stat().st_size, checksum=compute_checksum(path.read_bytes()))
            saved += 1
            progress.update("persist", saved, artifact_count + 1, unit="records")

        for kind, path in (
            ("NIFTI", pipeline_result.reference_path),
            ("SEG_NIFTI", pipeline_result.segmentation_path),
            ("NIFTI", pipeline_result.confidence_path),
            ("JSON", metrics_json_path),
            ("STL", mesh_path),
            ("SEG_DICOM", dicom_seg_path),
            ("PDF", pdf_path),
        ):
            save_artifact(kind, path)

        for output_name, output in model_outputs.items():
            if output_name == "ensemble":
                continue
            for path in (output.segmentation_path, output.confidence_path):
                save_artifact("NIFTI", path)

        for modality, path in pipeline_result.synthesized_paths.items():
            save_artifact(FILE_KIND_BY_MODALITY[modality], path)

        for name, thumb_path in thumbnails.items():
            save_artifact("PNG", thumb_path)

        progress.done("persist")
        study.status = "DONE"
        progress.finish(db)
        db.commit()
    except Exception as exc:
        # A failed commit leaves the session unusable until it is rolled back.
        # Recover it before persisting the failed status.
        db.rollback()
        study.status = "FAILED"
        progress.fail(exc, db)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}") from exc

    return {"status": study.status, "metrics": metrics}
