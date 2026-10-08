from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict


def create_dicom_seg_stub(
    study_id: str,
    metrics: Dict[str, float],
    output_path: Path,
) -> Path:
    """Persist a human-readable text stub masquerading as a DICOM-SEG file."""
    content = (
        "DICOM-SEG PLACEHOLDER\n"
        f"Study ID: {study_id}\n"
        f"Generated: {datetime.utcnow().isoformat()}Z\n"
        f"Metrics: {metrics}\n"
        "NOTE: Replace with real DICOM-SEG serialization via pydicom in production.\n"
    )
    output_path.write_text(content)
    return output_path
