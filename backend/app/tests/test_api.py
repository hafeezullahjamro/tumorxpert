from __future__ import annotations

import io
import tarfile
import tempfile
import threading
from types import SimpleNamespace

import nibabel as nib
import numpy as np
import pytest


def _create_nifti_bytes(value: float = 0.0) -> bytes:
    data = np.full((16, 16, 16), fill_value=value, dtype=np.float32)
    img = nib.Nifti1Image(data, affine=np.eye(4))
    with tempfile.NamedTemporaryFile(suffix=".nii.gz") as tmp:
        nib.save(img, tmp.name)
        tmp.seek(0)
        return tmp.read()


def _create_tar_bytes(members: list[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, payload in members:
            info = tarfile.TarInfo(name=name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return buffer.getvalue()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_retention_update_starts_and_stops_cleanup_at_runtime(client, monkeypatch):
    from app.core.config import BACKEND_ROOT, get_settings
    from app.services.storage import StorageService

    settings = get_settings()
    assert settings.storage_root != BACKEND_ROOT / "storage"
    assert not settings.auto_delete_enabled
    manager = client.app.state.auto_delete_manager
    cleanup_called = threading.Event()
    cleanup_calls = []

    def fake_cleanup(storage, days):
        cleanup_calls.append((storage.settings.storage_root, days))
        cleanup_called.set()
        return []

    monkeypatch.setattr(StorageService, "cleanup_older_than", fake_cleanup)
    enabled = client.post("/admin/retention", json={"days": 3, "enabled": True})
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["auto_delete_enabled"] is True
    assert cleanup_called.wait(timeout=2)
    assert cleanup_calls == [(settings.storage_root, 3)]
    first_task = manager._task
    assert first_task is not None and not first_task.done()

    disabled = client.post("/admin/retention", json={"days": 3, "enabled": False})
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["auto_delete_enabled"] is False
    assert first_task.done()

    # A completed task must not prevent enabling retention again.
    cleanup_called.clear()
    reenabled = client.post("/admin/retention", json={"days": 5, "enabled": True})
    assert reenabled.status_code == 200, reenabled.text
    assert cleanup_called.wait(timeout=2)
    assert manager._task is not first_task
    assert cleanup_calls[-1] == (settings.storage_root, 5)
    client.post("/admin/retention", json={"days": 5, "enabled": False})
    assert manager._task.done()


def test_register_and_login_existing_bcrypt_password(client):
    credentials = {"email": "login-test@example.com", "password": "test-password"}
    registered = client.post("/auth/register", json=credentials)
    assert registered.status_code == 200, registered.text
    logged_in = client.post("/auth/login", json=credentials)
    assert logged_in.status_code == 200, logged_in.text
    assert logged_in.json()["user"]["id"] == registered.json()["id"]
    assert logged_in.json()["token"]["access_token"]
    assert client.post("/auth/register", json=credentials).status_code == 409
    assert client.post("/auth/login", json={**credentials, "password": "wrong-password"}).status_code == 401


def test_bcrypt_password_limit_uses_utf8_bytes(client):
    credentials = {"email": "unicode-test@example.com", "password": "é" * 37}
    assert client.post("/auth/register", json=credentials).status_code == 400
    assert client.post("/auth/login", json=credentials).status_code == 400
    credentials["password"] = "é" * 36
    assert client.post("/auth/register", json=credentials).status_code == 200
    assert client.post("/auth/login", json=credentials).status_code == 200


def test_upload_filename_stays_inside_study_storage(client):
    from pathlib import Path

    from app.core.config import get_settings

    response = client.post(
        "/studies/upload",
        files={"file": ("../../escaped_flair.nii.gz", _create_nifti_bytes(), "application/octet-stream")},
    )
    assert response.status_code == 200, response.text
    study_id = response.json()["id"]
    artifacts = client.get(f"/studies/{study_id}/files").json()
    upload_root = get_settings().storage_uploads / study_id
    assert len(artifacts) == 1
    assert Path(artifacts[0]["path"]).parent == upload_root
    assert not (get_settings().storage_root / "escaped_flair.nii.gz").exists()


@pytest.mark.parametrize("existing_absolute", [False, True])
def test_rerun_reuses_artifact_across_absolute_and_relative_paths(client, existing_absolute):
    from sqlalchemy import func, select

    from app.core.config import BACKEND_ROOT
    from app.db import crud, schemas
    from app.db.base import SessionLocal
    from app.db.models import FileArtifact

    with SessionLocal() as db:
        study = crud.create_study(db, schemas.StudyCreate(name="Relative artifact rerun"))
        relative_path = f"storage/processed/{study.id}/segmentation.nii.gz"
        absolute_path = str(BACKEND_ROOT / relative_path)
        first = FileArtifact(
            study_id=study.id, kind="SEG_NIFTI",
            path=absolute_path if existing_absolute else relative_path,
            size_bytes=10, checksum="a" * 64,
        )
        db.add(first)
        db.commit()
        db.refresh(first)
        rerun = crud.add_file(
            db,
            study_id=study.id,
            kind="SEG_NIFTI",
            path=relative_path if existing_absolute else absolute_path,
            size_bytes=20,
            checksum="b" * 64,
        )
        assert rerun.id == first.id
        assert rerun.path == relative_path
        assert rerun.size_bytes == 20
        count = db.scalar(select(func.count()).select_from(FileArtifact).where(FileArtifact.study_id == study.id))
        assert count == 1


def test_inference_sql_failure_persists_failed_status(client, monkeypatch):
    from app.db.models import User

    uploaded = client.post(
        "/studies/upload",
        files={"file": ("failure_flair.nii.gz", _create_nifti_bytes(), "application/octet-stream")},
    )
    assert uploaded.status_code == 200, uploaded.text
    study_id = uploaded.json()["id"]

    monkeypatch.setattr(
        "app.routers.inference.run_study_pipeline",
        lambda **kwargs: SimpleNamespace(
            reference_volume=np.ones((4, 4, 4), dtype=np.float32),
            completed_modalities={},
            metrics={},
        ),
    )

    def fail_commit(db, *args):
        db.add_all([
            User(email="duplicate@example.com", hashed_password="unused"),
            User(email="duplicate@example.com", hashed_password="unused"),
        ])
        db.commit()

    monkeypatch.setattr("app.routers.inference.crud.upsert_metrics", fail_commit)
    response = client.post(f"/studies/{study_id}/run")
    assert response.status_code == 500
    assert client.get(f"/studies/{study_id}").json()["status"] == "FAILED"


def test_mesh_export_supports_volume_filled_with_tumor(tmp_path):
    import trimesh

    from app.services.postprocess import export_mesh

    destination = tmp_path / "full-tumor.stl"
    export_mesh(np.ones((4, 5, 6), dtype=np.uint8), destination, (1.0, 2.0, 3.0))
    mesh = trimesh.load(destination)
    assert len(mesh.faces) > 0
    assert mesh.is_watertight


def test_pdf_export_falls_back_after_weasyprint_render_failure(monkeypatch, tmp_path):
    from app.services import pdf_report

    class BrokenWeasyHTML:
        def __init__(self, **kwargs):
            pass

        def write_pdf(self, *args):
            raise RuntimeError("PDF renderer is incompatible with the installed system libraries")

    monkeypatch.setattr(pdf_report, "WeasyHTML", BrokenWeasyHTML)
    destination = tmp_path / "exports" / "fallback.pdf"
    pdf_report.generate_pdf_report(
        app_name="TumorXpert",
        study_name="Fallback test",
        study_id="pdf-test",
        sequences={"flair": True, "t1": True, "t1ce": True, "t2": True},
        metrics={"wt_ml": 1.0, "tc_ml": 0.5, "et_ml": 0.1},
        model_metrics={},
        segmentation_backend="ensemble",
        qc_flags={},
        thumbnails=None,
        output_path=destination,
        generated_at="Test",
    )
    assert destination.read_bytes().startswith(b"%PDF-")


def test_comparison_rejects_unaligned_images_before_creating_record(client, monkeypatch, tmp_path):
    from app.routers import comparisons

    image_a = tmp_path / "a.nii.gz"
    image_b = tmp_path / "b.nii.gz"
    nib.save(nib.Nifti1Image(np.ones((4, 4, 4)), np.eye(4)), image_a)
    shifted_affine = np.eye(4)
    shifted_affine[0, 3] = 10.0
    nib.save(nib.Nifti1Image(np.ones((4, 4, 4)), shifted_affine), image_b)

    monkeypatch.setattr(comparisons.crud, "get_study", lambda *args: SimpleNamespace())
    monkeypatch.setattr(comparisons.crud, "get_metrics", lambda *args: SimpleNamespace(wt_ml=1.0))
    artifact_paths = iter((image_a, image_b))
    monkeypatch.setattr(comparisons.crud, "get_file_by_kind", lambda *args: SimpleNamespace(path=str(next(artifact_paths))))
    created_records = []
    monkeypatch.setattr(comparisons.crud, "create_comparison", lambda *args, **kwargs: created_records.append(kwargs))

    response = client.post("/compare", json={
        "study_a_id": "6d24a9f9-c4c0-483f-bb8c-fef1b33735fe",
        "study_b_id": "a1c4712d-2d1d-4eae-8b95-8d384753fd01",
    })
    assert response.status_code == 400, response.text
    assert "spatial alignment" in response.json()["detail"]
    assert not created_records


def test_upload_run_export_flow(client, monkeypatch):
    def fake_run_study_pipeline(*, study_root, processed_root, settings):
        from app.services.imaging import save_nifti
        from app.services.postprocess import compute_metrics

        reference = np.ones((16, 16, 16), dtype=np.float32)
        labels = np.zeros((16, 16, 16), dtype=np.uint8)
        labels[4:10, 4:10, 4:10] = 3
        confidence = np.full((16, 16, 16), 0.92, dtype=np.float32)
        affine = np.eye(4, dtype=np.float32)
        header = nib.Nifti1Image(reference, affine=affine).header.copy()

        processed_root.mkdir(parents=True, exist_ok=True)
        reference_path = processed_root / "reference_flair.nii.gz"
        segmentation_path = processed_root / "segmentation.nii.gz"
        confidence_path = processed_root / "confidence_map.nii.gz"

        save_nifti(reference, reference_path, affine=affine, header=header)
        save_nifti(labels.astype(np.uint8), segmentation_path, affine=affine, header=header)
        save_nifti(confidence, confidence_path, affine=affine, header=header)

        return SimpleNamespace(
            metrics=compute_metrics(labels, confidence, spacing=(1.0, 1.0, 1.0), runtime_sec=1.4),
            reference_volume=reference,
            reference_affine=affine,
            reference_header=header,
            reference_path=reference_path,
            segmentation_path=segmentation_path,
            confidence_path=confidence_path,
            labels=labels,
            confidence=confidence,
            synthesized_paths={},
            missing_modality=None,
            completed_modalities={
                "flair": reference,
                "t1": reference,
                "t1ce": reference,
                "t2": reference,
            },
        )

    monkeypatch.setattr("app.routers.inference.run_study_pipeline", fake_run_study_pipeline)

    files = [
        ("files", ("case_0000.nii.gz", _create_nifti_bytes(1.0), "application/octet-stream")),
        ("files", ("case_0001.nii.gz", _create_nifti_bytes(2.0), "application/octet-stream")),
        ("files", ("case_0002.nii.gz", _create_nifti_bytes(3.0), "application/octet-stream")),
        ("files", ("case_0003.nii.gz", _create_nifti_bytes(4.0), "application/octet-stream")),
    ]
    response = client.post(
        "/studies/upload",
        data={"name": "Unit Test Study"},
        files=files,
    )
    assert response.status_code == 200, response.text
    study = response.json()
    study_id = study["id"]
    assert all(study["sequences_present"].values())

    run_response = client.post(f"/studies/{study_id}/run")
    assert run_response.status_code == 200, run_response.text
    metrics = run_response.json()["metrics"]
    assert "wt_ml" in metrics
    assert "confidence_summary" in metrics
    assert "low_confidence_fraction" in metrics
    assert "dice_mock" not in metrics
    assert "hd95_mock" not in metrics
    assert "confidence_score_mock" not in metrics

    metrics_response = client.get(f"/studies/{study_id}/metrics")
    assert metrics_response.status_code == 200
    metrics_payload = metrics_response.json()
    assert "confidence_summary" in metrics_payload
    assert "low_confidence_fraction" in metrics_payload
    assert "dice_mock" not in metrics_payload
    assert "hd95_mock" not in metrics_payload
    assert "confidence_score_mock" not in metrics_payload

    pdf_response = client.get(f"/studies/{study_id}/export/pdf")
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.headers["content-disposition"].startswith("inline;")
    assert pdf_response.content.startswith(b"%PDF-")

    seg_response = client.get(f"/studies/{study_id}/export/seg")
    assert seg_response.status_code == 200

    json_response = client.get(f"/studies/{study_id}/export/json")
    assert json_response.status_code == 200
    metrics_json = json_response.json()
    assert metrics_json["wt_ml"] == metrics_payload["wt_ml"]
    assert "confidence_summary" in metrics_json
    assert "low_confidence_fraction" in metrics_json
    assert "dice_mock" not in metrics_json
    assert "hd95_mock" not in metrics_json
    assert "confidence_score_mock" not in metrics_json

    stl_response = client.get(f"/studies/{study_id}/export/stl")
    assert stl_response.status_code == 200

    rerun_response = client.post(f"/studies/{study_id}/run")
    assert rerun_response.status_code == 200, rerun_response.text


def test_upload_supports_brats_named_tar_archive(client):
    tar_bytes = _create_tar_bytes(
        [
            ("BraTS2021_00495/BraTS2021_00495_flair.nii.gz", _create_nifti_bytes(1.0)),
            ("BraTS2021_00495/BraTS2021_00495_t1.nii.gz", _create_nifti_bytes(2.0)),
            ("BraTS2021_00495/BraTS2021_00495_t1ce.nii.gz", _create_nifti_bytes(3.0)),
            ("BraTS2021_00495/BraTS2021_00495_t2.nii.gz", _create_nifti_bytes(4.0)),
        ]
    )

    response = client.post(
        "/studies/upload",
        files={"file": ("BraTS2021_00495.tar", tar_bytes, "application/x-tar")},
    )

    assert response.status_code == 200, response.text
    study = response.json()
    assert study["name"] == "BraTS2021_00495"
    assert study["sequences_present"] == {
        "flair": True,
        "t1": True,
        "t1ce": True,
        "t2": True,
    }


def test_compare_rejects_same_study(client, monkeypatch):
    def fake_run_study_pipeline(*, study_root, processed_root, settings):
        from app.services.imaging import save_nifti
        from app.services.postprocess import compute_metrics

        reference = np.ones((16, 16, 16), dtype=np.float32)
        labels = np.zeros((16, 16, 16), dtype=np.uint8)
        labels[3:9, 3:9, 3:9] = 3
        confidence = np.full((16, 16, 16), 0.9, dtype=np.float32)
        affine = np.eye(4, dtype=np.float32)
        header = nib.Nifti1Image(reference, affine=affine).header.copy()

        processed_root.mkdir(parents=True, exist_ok=True)
        reference_path = processed_root / "reference_flair.nii.gz"
        segmentation_path = processed_root / "segmentation.nii.gz"
        confidence_path = processed_root / "confidence_map.nii.gz"

        save_nifti(reference, reference_path, affine=affine, header=header)
        save_nifti(labels.astype(np.uint8), segmentation_path, affine=affine, header=header)
        save_nifti(confidence, confidence_path, affine=affine, header=header)

        return SimpleNamespace(
            metrics=compute_metrics(labels, confidence, spacing=(1.0, 1.0, 1.0), runtime_sec=1.0),
            reference_volume=reference,
            reference_affine=affine,
            reference_header=header,
            reference_path=reference_path,
            segmentation_path=segmentation_path,
            confidence_path=confidence_path,
            labels=labels,
            confidence=confidence,
            synthesized_paths={},
            missing_modality=None,
            completed_modalities={
                "flair": reference,
                "t1": reference,
                "t1ce": reference,
                "t2": reference,
            },
        )

    monkeypatch.setattr("app.routers.inference.run_study_pipeline", fake_run_study_pipeline)

    files = [
        ("files", ("case_0000.nii.gz", _create_nifti_bytes(1.0), "application/octet-stream")),
        ("files", ("case_0001.nii.gz", _create_nifti_bytes(2.0), "application/octet-stream")),
        ("files", ("case_0002.nii.gz", _create_nifti_bytes(3.0), "application/octet-stream")),
        ("files", ("case_0003.nii.gz", _create_nifti_bytes(4.0), "application/octet-stream")),
    ]
    upload_response = client.post("/studies/upload", data={"name": "Compare Study"}, files=files)
    assert upload_response.status_code == 200, upload_response.text
    study_id = upload_response.json()["id"]

    run_response = client.post(f"/studies/{study_id}/run")
    assert run_response.status_code == 200, run_response.text

    compare_response = client.post(
        "/compare",
        json={"study_a_id": study_id, "study_b_id": study_id},
    )
    assert compare_response.status_code == 400
    assert compare_response.json()["detail"] == "Select two different studies to compare."
