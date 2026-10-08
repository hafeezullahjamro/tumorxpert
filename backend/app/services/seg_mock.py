from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Dict, Tuple

import nibabel as nib
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def _seed_from_text(text: str) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _create_coordinate_grid(shape: Tuple[int, int, int]) -> Tuple[np.ndarray, ...]:
    ranges = [np.linspace(-1.0, 1.0, num=s) for s in shape]
    return np.meshgrid(*ranges, indexing="ij")


def generate_mock_volume(study_id: str, shape: Tuple[int, int, int] = (160, 192, 160)) -> np.ndarray:
    rng = np.random.default_rng(_seed_from_text(f"volume-{study_id}"))
    volume = rng.normal(loc=0.0, scale=0.15, size=shape).astype(np.float32)
    volume = (volume - volume.min()) / (volume.max() - volume.min() + 1e-6)
    return volume


def generate_mock_segmentation(study_id: str, shape: Tuple[int, int, int]) -> Tuple[np.ndarray, np.ndarray]:
    X, Y, Z = _create_coordinate_grid(shape)
    radii = np.array([0.55, 0.45, 0.32])
    rng = np.random.default_rng(_seed_from_text(f"seg-{study_id}"))
    offsets = rng.uniform(-0.1, 0.1, size=3)
    Xo, Yo, Zo = X - offsets[0], Y - offsets[1], Z - offsets[2]

    distance = np.sqrt((Xo / radii[0]) ** 2 + (Yo / radii[1]) ** 2 + (Zo / radii[2]) ** 2)

    labels = np.zeros(shape, dtype=np.uint8)
    labels[distance <= 1.0] = 1  # whole tumor (WT)
    labels[distance <= 0.75] = 2  # tumor core (TC)
    labels[distance <= 0.55] = 3  # enhancing tumor (ET)

    uncertainty = np.clip(1.0 - np.abs(distance - 1.0), 0.0, 1.0).astype(np.float32)
    uncertainty *= rng.uniform(0.6, 1.0)  # scale to vary across studies

    return labels, uncertainty


def save_nifti(data: np.ndarray, path: Path, affine=None) -> Path:
    if affine is None:
        affine = np.diag([1.0, 1.0, 1.0, 1.0])
    img = nib.Nifti1Image(data, affine=affine)
    nib.save(img, str(path))
    return path


def generate_thumbnails(volume: np.ndarray, output_dir: Path) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    mid_slices = {
        "axial": volume[:, :, volume.shape[2] // 2],
        "coronal": volume[:, volume.shape[1] // 2, :],
        "sagittal": volume[volume.shape[0] // 2, :, :],
    }
    results: Dict[str, Path] = {}
    for name, slice_data in mid_slices.items():
        normalized = (slice_data - slice_data.min()) / (slice_data.ptp() + 1e-6)
        image = Image.fromarray((normalized * 255).astype(np.uint8))
        path = output_dir / f"{name}.png"
        image.save(path)
        results[name] = path
    return results
