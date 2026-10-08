from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
from skimage.measure import marching_cubes
import trimesh

logger = logging.getLogger(__name__)


def compute_metrics(
    labels: np.ndarray,
    uncertainty: np.ndarray,
    spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    runtime_sec: float = 12.5,
    agreement_metrics: Dict[str, float] | None = None,
) -> Dict[str, float]:
    voxel_volume_ml = float(np.prod(spacing)) / 1000.0
    wt_voxels = np.count_nonzero(labels > 0)
    tc_voxels = np.count_nonzero((labels == 1) | (labels == 3))
    et_voxels = np.count_nonzero(labels == 3)
    wt_ml = wt_voxels * voxel_volume_ml
    tc_ml = tc_voxels * voxel_volume_ml
    et_ml = et_voxels * voxel_volume_ml
    edema_core_ratio = (wt_ml - tc_ml) / max(tc_ml, 1e-3)
    focus_mask = labels > 0
    focus_values = uncertainty[focus_mask] if np.any(focus_mask) else uncertainty.reshape(-1)
    confidence_summary = float(np.clip(focus_values.mean(), 0.0, 1.0))
    low_confidence_fraction = float(np.mean(focus_values < 0.6)) if focus_values.size else 0.0

    metrics = {
        "wt_ml": round(wt_ml, 2),
        "tc_ml": round(tc_ml, 2),
        "et_ml": round(et_ml, 2),
        "edema_core_ratio": round(edema_core_ratio, 2),
        "confidence_summary": round(confidence_summary, 3),
        "low_confidence_fraction": round(low_confidence_fraction, 3),
        "runtime_sec": round(runtime_sec, 1),
    }
    if agreement_metrics:
        metrics.update(
            {
                key: round(float(value), 3 if "dice" in key else 2)
                for key, value in agreement_metrics.items()
            }
        )
    logger.info("Computed inference metrics: %s", metrics)
    return metrics


def compute_model_agreement(
    labels_a: np.ndarray,
    labels_b: np.ndarray,
    spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> Dict[str, float]:
    voxel_volume_ml = float(np.prod(spacing)) / 1000.0
    wt_a = labels_a > 0
    wt_b = labels_b > 0
    denom = int(np.count_nonzero(wt_a) + np.count_nonzero(wt_b))
    if denom == 0:
        wt_dice = 1.0
    else:
        intersection = int(np.count_nonzero(wt_a & wt_b))
        wt_dice = (2.0 * intersection) / denom

    disagreement_voxels = int(np.count_nonzero(labels_a != labels_b))
    return {
        "model_agreement_wt_dice": wt_dice,
        "label_disagreement_ml": disagreement_voxels * voxel_volume_ml,
    }


def export_metrics_json(metrics: Dict[str, float], output_path: Path) -> Path:
    output_path.write_text(json.dumps(metrics, indent=2))
    return output_path


def export_mesh(labels: np.ndarray, output_path: Path, spacing: Tuple[float, float, float]) -> Path:
    surface = labels >= 1
    if not surface.any():
        trimesh.Trimesh(vertices=np.empty((0, 3)), faces=np.empty((0, 3), dtype=np.int64), process=False).export(output_path)
        logger.info("Exported empty STL mesh to %s", output_path)
        return output_path
    # A background border gives marching cubes a valid surface even when tumor
    # touches every image boundary or fills the whole volume.
    padded_surface = np.pad(surface, 1, mode="constant")
    verts, faces, _, _ = marching_cubes(padded_surface.astype(float), level=0.5, spacing=spacing)
    verts -= np.asarray(spacing)
    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    mesh.export(output_path)
    logger.info("Exported STL mesh to %s", output_path)
    return output_path
