from __future__ import annotations

from pathlib import Path
from typing import Dict

import nibabel as nib
import numpy as np
from PIL import Image


def save_nifti(data: np.ndarray, path: Path, affine: np.ndarray, header: nib.Nifti1Header | None = None) -> Path:
    image = nib.Nifti1Image(data, affine=affine, header=header)
    nib.save(image, str(path))
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
        normalized = (slice_data - slice_data.min()) / (float(np.ptp(slice_data)) + 1e-6)
        image = Image.fromarray((normalized * 255).astype(np.uint8))
        path = output_dir / f"{name}.png"
        image.save(path)
        results[name] = path
    return results


def generate_segmentation_previews(
    volume: np.ndarray,
    labels: np.ndarray,
    output_dir: Path,
    *,
    prefix: str = "ensemble",
) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    slices = {
        "axial": (volume[:, :, volume.shape[2] // 2], labels[:, :, labels.shape[2] // 2]),
        "coronal": (volume[:, volume.shape[1] // 2, :], labels[:, labels.shape[1] // 2, :]),
        "sagittal": (volume[volume.shape[0] // 2, :, :], labels[labels.shape[0] // 2, :, :]),
    }
    results: Dict[str, Path] = {}
    palette = {
        1: np.array([255, 99, 132], dtype=np.float32),
        2: np.array([72, 187, 255], dtype=np.float32),
        3: np.array([255, 170, 82], dtype=np.float32),
    }

    for name, (image_slice, label_slice) in slices.items():
        normalized = (image_slice - image_slice.min()) / (float(np.ptp(image_slice)) + 1e-6)
        base_rgb = np.repeat((normalized[..., None] * 255).astype(np.uint8), 3, axis=2).astype(np.float32)

        overlay = base_rgb.copy()
        for label_value, color in palette.items():
            mask = label_slice == label_value
            if np.any(mask):
                overlay[mask] = overlay[mask] * 0.4 + color * 0.6

        path = output_dir / f"{prefix}_{name}_overlay.png"
        Image.fromarray(np.clip(overlay, 0, 255).astype(np.uint8)).save(path)
        results[f"{prefix}_{name}_overlay"] = path

    return results


def generate_modality_previews(modalities: Dict[str, np.ndarray], output_dir: Path) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: Dict[str, Path] = {}

    for modality, volume in modalities.items():
        slice_data = volume[:, :, volume.shape[2] // 2]
        normalized = (slice_data - slice_data.min()) / (float(np.ptp(slice_data)) + 1e-6)
        image = Image.fromarray((normalized * 255).astype(np.uint8))
        path = output_dir / f"{modality}_preview.png"
        image.save(path)
        results[f"{modality}_preview"] = path

    return results


def generate_confidence_previews(
    confidence_map: np.ndarray,
    output_dir: Path,
    *,
    prefix: str = "ensemble",
) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    slices = {
        "axial": confidence_map[:, :, confidence_map.shape[2] // 2],
        "coronal": confidence_map[:, confidence_map.shape[1] // 2, :],
        "sagittal": confidence_map[confidence_map.shape[0] // 2, :, :],
    }
    results: Dict[str, Path] = {}
    for name, slice_data in slices.items():
        normalized = np.clip(slice_data.astype(np.float32), 0.0, 1.0)
        heatmap = np.zeros((*normalized.shape, 3), dtype=np.uint8)
        heatmap[..., 0] = (255 * (1.0 - normalized)).astype(np.uint8)
        heatmap[..., 1] = (255 * normalized).astype(np.uint8)
        heatmap[..., 2] = (180 * normalized).astype(np.uint8)
        path = output_dir / f"{prefix}_{name}_confidence.png"
        Image.fromarray(heatmap).save(path)
        results[f"{prefix}_{name}_confidence"] = path
    return results
