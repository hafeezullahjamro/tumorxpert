from concurrent.futures import ThreadPoolExecutor
import threading
from unittest.mock import Mock

import numpy as np
import pytest

from app.tests.test_api import _create_nifti_bytes


def test_measured_progress_survives_new_requests_and_rejects_duplicate_runs(client, monkeypatch):
    uploaded = client.post('/studies/upload', files={'file': ('tracked_flair.nii.gz', _create_nifti_bytes(), 'application/gzip')})
    study_id = uploaded.json()['id']
    started, release = threading.Event(), threading.Event()

    def blocked_pipeline(*, progress, **kwargs):
        progress.update('validate', force=True)
        progress.done('validate')
        progress.children('preprocess', [('flair.n4', 'FLAIR bias correction')])
        progress.update('flair.n4', 3, 20, unit='iterations', force=True)
        started.set()
        assert release.wait(10)
        raise RuntimeError('Controlled preprocessing failure')

    monkeypatch.setattr('app.routers.inference.run_study_pipeline', blocked_pipeline)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(client.post, f'/studies/{study_id}/run')
        try:
            assert started.wait(5)
            first = client.get(f'/studies/{study_id}').json()
            assert first['status'] == 'PROCESSING'
            child = first['progress']['stages'][1]['children'][0]
            assert child['completed'] == 3 and child['total'] == 20
            assert child['percent'] == 15
            second = client.get(f'/studies/{study_id}').json()
            assert second['progress'] == first['progress']
            assert client.post(f'/studies/{study_id}/run').status_code == 409
        finally:
            release.set()
        assert pending.result(timeout=10).status_code == 500
    failed = client.get(f'/studies/{study_id}').json()
    assert failed['status'] == failed['progress']['status'] == 'FAILED'
    assert failed['progress']['percent'] < 100
    assert failed['progress']['stages'][1]['children'][0]['status'] == 'FAILED'
    assert 'Controlled preprocessing failure' in failed['progress']['error']


def test_n4_progress_comes_from_actual_simpleitk_iterations(monkeypatch):
    import SimpleITK as sitk
    from app.services import preprocess

    factory = sitk.N4BiasFieldCorrectionImageFilter
    def small_filter():
        corrector = factory()
        corrector.SetMaximumNumberOfIterations([2, 2])
        return corrector
    monkeypatch.setattr(preprocess.sitk, 'N4BiasFieldCorrectionImageFilter', small_filter)
    reporter = Mock()
    image = sitk.GetImageFromArray(np.random.default_rng(7).uniform(1, 100, (8, 16, 16)).astype(np.float32))
    corrected = preprocess.n4_bias_correct(image, progress=reporter, key='flair.n4')
    assert corrected.GetSize() == image.GetSize()
    calls = reporter.update.call_args_list
    observed = [call.args[1] for call in calls if call.kwargs.get('status') != 'DONE']
    assert observed and observed == sorted(observed)
    assert 0 < observed[-1] <= 4
    assert calls[-1].kwargs['status'] == 'DONE'
    assert calls[-1].args[1] == observed[-1]


def test_actual_slice_and_monai_window_counts():
    import torch
    from app.services.inference_pipeline import _segment_completed_modalities_nnunet, _segment_completed_modalities_swinunetr

    device = torch.device('cpu')
    def model(tensor):
        return torch.zeros((tensor.shape[0], 4, *tensor.shape[2:]), dtype=tensor.dtype)
    volumes = {name: np.ones((12, 8, 8), dtype=np.float32) for name in ('flair', 't1', 't1ce', 't2')}
    slices = []
    result = _segment_completed_modalities_nnunet(normalized_modalities=volumes, model=model, device=device, torch=torch,
                                                  progress_callback=lambda done, total: slices.append((done, total)))
    assert result.shape == (4, 12, 8, 8)
    assert slices == [(i, 8) for i in range(1, 9)]
    windows = []
    result = _segment_completed_modalities_swinunetr(normalized_modalities=volumes, model=model, roi_size=(8, 8, 8), overlap=0.25,
                                                    device=device, torch=torch, progress_callback=lambda done, total: windows.append((done, total)))
    assert result.shape == (4, 12, 8, 8)
    assert windows == [(0, 2), (1, 2), (2, 2)]


def test_synthesis_rejects_volume_with_no_predictable_slices():
    from app.services.inference_pipeline import _synthesize_missing_modality
    volumes = {name: np.ones((8, 8, 4), dtype=np.float32) for name in ('flair', 't1', 't2')}
    with pytest.raises(ValueError, match='at least five slices'):
        _synthesize_missing_modality(target_modality='t1ce', normalized_modalities=volumes,
                                     volumes={}, model=None, device=None, torch=None)
