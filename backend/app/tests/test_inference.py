from __future__ import annotations

import nibabel as nib
import numpy as np
import pytest


@pytest.mark.parametrize("backend", ["ensemble", "swinunetr3d"])
def test_requested_swin_backend_requires_checkpoint(backend, monkeypatch, tmp_path):
    from app.core.config import Settings
    from app.services import inference_pipeline

    study_root = tmp_path / "study"
    processed_root = tmp_path / "processed"
    study_root.mkdir()
    processed_root.mkdir()
    for modality in inference_pipeline.SEGMENTATION_MODALITIES:
        image = nib.Nifti1Image(np.ones((4, 4, 4), dtype=np.float32), np.eye(4))
        nib.save(image, study_root / f"study_{modality}.nii.gz")

    monkeypatch.setattr(inference_pipeline, "_load_torch_dependencies", lambda: (None, None, None))
    monkeypatch.setattr(inference_pipeline, "_resolve_device", lambda *args: "cpu")
    monkeypatch.setattr(inference_pipeline, "preprocess_study_modalities", lambda paths, output_dir: paths)
    monkeypatch.setattr(inference_pipeline, "_load_nnunet_model", lambda *args: None)
    monkeypatch.setattr(
        inference_pipeline,
        "_segment_completed_modalities_nnunet",
        lambda **kwargs: np.full((4, 4, 4, 4), 0.25, dtype=np.float32),
    )
    settings = Settings(
        _env_file=None,
        segmentation_backend=backend,
        model_root=tmp_path / "missing-models",
        storage_root=tmp_path,
    )

    with pytest.raises(FileNotFoundError, match="Swin UNETR checkpoint not found"):
        inference_pipeline.run_study_pipeline(
            study_root=study_root,
            processed_root=processed_root,
            settings=settings,
        )
