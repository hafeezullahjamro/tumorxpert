from __future__ import annotations

import io
import logging
import re
import tempfile
import zipfile
from pathlib import Path

import SimpleITK as sitk

logger = logging.getLogger(__name__)

MODALITY_HINT_PATTERNS = (
    (re.compile(r"t1ce|t1c|post|gd|ce", re.IGNORECASE), "t1ce"),
    (re.compile(r"flair", re.IGNORECASE), "flair"),
    (re.compile(r"\bt1\b", re.IGNORECASE), "t1"),
    (re.compile(r"\bt2\b", re.IGNORECASE), "t2"),
)


def infer_modality_from_dicom_text(text: str) -> str | None:
    for pattern, modality in MODALITY_HINT_PATTERNS:
        if pattern.search(text):
            return modality
    return None


def _read_image(path: Path) -> sitk.Image:
    image = sitk.ReadImage(str(path))
    return sitk.Cast(image, sitk.sitkFloat32)


def _foreground_mask(image: sitk.Image) -> sitk.Image:
    mask = sitk.OtsuThreshold(image, 0, 1, 128)
    mask = sitk.BinaryMorphologicalClosing(mask, [2, 2, 2])
    mask = sitk.BinaryFillhole(mask)
    return sitk.Cast(mask, sitk.sitkUInt8)


def skull_strip(image: sitk.Image) -> sitk.Image:
    mask = _foreground_mask(image)
    stripped = sitk.Mask(image, mask)
    return sitk.Cast(stripped, sitk.sitkFloat32)


def n4_bias_correct(image: sitk.Image) -> sitk.Image:
    mask = _foreground_mask(image)
    corrector = sitk.N4BiasFieldCorrectionImageFilter()
    corrected = corrector.Execute(image, mask)
    return sitk.Cast(corrected, sitk.sitkFloat32)


def resample_to_reference(image: sitk.Image, reference: sitk.Image) -> sitk.Image:
    if (
        image.GetSize() == reference.GetSize()
        and image.GetSpacing() == reference.GetSpacing()
        and image.GetOrigin() == reference.GetOrigin()
        and image.GetDirection() == reference.GetDirection()
    ):
        return image

    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(reference)
    resampler.SetInterpolator(sitk.sitkLinear)
    resampler.SetDefaultPixelValue(0.0)
    return sitk.Cast(resampler.Execute(image), sitk.sitkFloat32)


def preprocess_nifti(
    input_path: Path,
    output_path: Path,
    *,
    reference_path: Path | None = None,
) -> Path:
    logger.info("Preprocessing NIfTI %s", input_path)
    image = _read_image(input_path)
    if reference_path is not None:
        reference = _read_image(reference_path)
        image = resample_to_reference(image, reference)
    image = n4_bias_correct(image)
    image = skull_strip(image)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(image, str(output_path), useCompression=True)
    return output_path


def preprocess_study_modalities(
    modality_paths: dict[str, Path],
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    ordered_modalities = list(modality_paths.keys())
    if not ordered_modalities:
        return {}

    reference_modality = ordered_modalities[0]
    reference_output = output_dir / f"{reference_modality}_preprocessed.nii.gz"
    preprocess_nifti(modality_paths[reference_modality], reference_output)

    processed = {reference_modality: reference_output}
    for modality, path in modality_paths.items():
        if modality == reference_modality:
            continue
        output_path = output_dir / f"{modality}_preprocessed.nii.gz"
        preprocess_nifti(path, output_path, reference_path=reference_output)
        processed[modality] = output_path
    return processed


def convert_dicom_zip_to_nifti_payloads(
    archive_name: str,
    data: bytes,
) -> tuple[list[tuple[str, bytes, str]], list[str]]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Invalid ZIP archive: {exc}") from exc

    with archive, tempfile.TemporaryDirectory() as tmpdir:
        extract_root = Path(tmpdir) / "dicom"
        archive.extractall(extract_root)

        series_candidates: dict[str, tuple[list[str], sitk.Image]] = {}
        for directory in sorted({path.parent for path in extract_root.rglob("*") if path.is_file()}):
            try:
                series_ids = sitk.ImageSeriesReader.GetGDCMSeriesIDs(str(directory)) or []
            except RuntimeError:
                continue
            for series_id in series_ids:
                file_names = list(sitk.ImageSeriesReader.GetGDCMSeriesFileNames(str(directory), series_id))
                if not file_names:
                    continue

                reader = sitk.ImageFileReader()
                reader.SetFileName(file_names[0])
                reader.LoadPrivateTagsOn()
                reader.ReadImageInformation()
                metadata_text = " ".join(
                    value
                    for key in ("0008|103e", "0018|1030", "0018|0024")
                    if reader.HasMetaDataKey(key)
                    for value in [reader.GetMetaData(key)]
                )
                modality = infer_modality_from_dicom_text(metadata_text)
                if not modality:
                    continue

                previous = series_candidates.get(modality)
                if previous and len(previous[0]) >= len(file_names):
                    continue

                series_reader = sitk.ImageSeriesReader()
                series_reader.SetFileNames(file_names)
                image = sitk.Cast(series_reader.Execute(), sitk.sitkFloat32)
                series_candidates[modality] = (file_names, image)

        if not series_candidates:
            raise ValueError("No supported DICOM MRI series were detected in the ZIP archive.")

        study_stem = Path(archive_name).stem.replace(".tar", "")
        payloads: list[tuple[str, bytes, str]] = []
        found_modalities: list[str] = []
        for modality, (_, image) in sorted(series_candidates.items()):
            output_path = extract_root / f"{study_stem}_{modality}.nii.gz"
            sitk.WriteImage(image, str(output_path), useCompression=True)
            payloads.append((output_path.name, output_path.read_bytes(), modality))
            found_modalities.append(modality)

        return payloads, found_modalities
