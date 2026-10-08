from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, Iterable

logger = logging.getLogger(__name__)

SEQUENCE_KEYS = ["t1", "t1ce", "t2", "flair"]
MODALITY_SUFFIX_MAP = {
    "0000": "flair",
    "0001": "t1",
    "0002": "t1ce",
    "0003": "t2",
}
MODALITY_PATTERNS = (
    (re.compile(r"_(0000)\.nii(?:\.gz)?$", re.IGNORECASE), "flair"),
    (re.compile(r"_(0001)\.nii(?:\.gz)?$", re.IGNORECASE), "t1"),
    (re.compile(r"_(0002)\.nii(?:\.gz)?$", re.IGNORECASE), "t1ce"),
    (re.compile(r"_(0003)\.nii(?:\.gz)?$", re.IGNORECASE), "t2"),
    (re.compile(r"(?:^|[_\-.])t1ce(?:[_\-.]|\.nii(?:\.gz)?$)", re.IGNORECASE), "t1ce"),
    (re.compile(r"(?:^|[_\-.])flair(?:[_\-.]|\.nii(?:\.gz)?$)", re.IGNORECASE), "flair"),
    (re.compile(r"(?:^|[_\-.])t1(?:[_\-.]|\.nii(?:\.gz)?$)", re.IGNORECASE), "t1"),
    (re.compile(r"(?:^|[_\-.])t2(?:[_\-.]|\.nii(?:\.gz)?$)", re.IGNORECASE), "t2"),
)


def modality_from_filename(filename: str) -> str | None:
    normalized = Path(filename).name.lower()
    match = re.search(r"_(\d{4})\.nii(?:\.gz)?$", normalized)
    if match:
        return MODALITY_SUFFIX_MAP.get(match.group(1))
    for pattern, modality in MODALITY_PATTERNS:
        if pattern.search(normalized):
            return modality
    return None


def detect_sequences_from_filenames(filenames: Iterable[str]) -> Dict[str, bool]:
    sequences = {key: False for key in SEQUENCE_KEYS}
    for name in filenames:
        modality = modality_from_filename(name)
        if modality:
            sequences[modality] = True
    logger.debug("Detected sequences %s from filenames %s", sequences, filenames)
    return sequences


def qc_assess(sequences: Dict[str, bool]) -> Dict[str, str]:
    flags: Dict[str, str] = {}
    if not sequences.get("t1ce"):
        flags["t1ce_missing"] = "T1ce sequence missing; enhancement estimates uncertain."
    if not sequences.get("flair"):
        flags["flair_missing"] = "FLAIR sequence missing; edema estimation limited."
    if sum(sequences.values()) <= 1:
        flags["limited_sequences"] = "Limited sequences detected; consider re-upload."
    if sum(sequences.values()) == len(SEQUENCE_KEYS):
        flags["all_sequences"] = "All primary BraTS sequences present."
    return flags
