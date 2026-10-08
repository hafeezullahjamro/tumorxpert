from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def compute_pct_change(volume_a: float, volume_b: float) -> float:
    if volume_a <= 1e-3:
        return 0.0
    return round(((volume_b - volume_a) / volume_a) * 100.0, 2)


def rano_label(pct_change: float) -> str:
    if pct_change >= 25.0:
        return "Possible progression"
    if pct_change <= -50.0:
        return "Partial response"
    return "Likely stable"


def create_change_map(
    labels_a: np.ndarray,
    labels_b: np.ndarray,
    output_path: Path,
) -> Path:
    """Persist a simple difference mask highlighting voxels that changed."""
    diff = (labels_b.astype(int) - labels_a.astype(int)).astype(np.int8)
    np.save(output_path, diff)
    logger.info("Saved change-map stub to %s", output_path)
    return output_path
