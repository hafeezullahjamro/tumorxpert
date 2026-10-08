from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import nibabel as nib
import numpy as np

from ..core.config import Settings
from .imaging import save_nifti
from .postprocess import compute_metrics, compute_model_agreement
from .preprocess import preprocess_study_modalities
from .qc import modality_from_filename

logger = logging.getLogger(__name__)

SEGMENTATION_MODALITIES = ("flair", "t1", "t1ce", "t2")
FILE_KIND_BY_MODALITY = {
    "flair": "FLAIR",
    "t1": "T1",
    "t1ce": "T1CE",
    "t2": "T2",
}
SYNTHESIS_SOURCE_MODALITIES = {
    "t1ce": ("flair", "t1", "t2"),
    "flair": ("t1", "t1ce", "t2"),
    "t1": ("flair", "t1ce", "t2"),
    "t2": ("flair", "t1", "t1ce"),
}
PREFERRED_REFERENCE_MODALITIES = ("flair", "t1ce", "t2", "t1")


@dataclass
class NiftiVolume:
    data: np.ndarray
    affine: np.ndarray
    header: nib.Nifti1Header
    path: Path
    spacing: tuple[float, float, float]


@dataclass
class SegmentationOutput:
    name: str
    labels: np.ndarray
    confidence: np.ndarray
    segmentation_path: Path
    confidence_path: Path


@dataclass
class PipelineResult:
    metrics: dict[str, float]
    model_metrics: dict[str, dict[str, float]]
    reference_volume: np.ndarray
    reference_affine: np.ndarray
    reference_header: nib.Nifti1Header
    reference_path: Path
    segmentation_path: Path
    confidence_path: Path
    labels: np.ndarray
    confidence: np.ndarray
    synthesized_paths: dict[str, Path]
    missing_modality: str | None
    completed_modalities: dict[str, np.ndarray]
    model_outputs: dict[str, SegmentationOutput]
    segmentation_backend: str


def _load_torch_dependencies() -> tuple[Any, Any, Any]:
    try:
        import torch
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "PyTorch is required for model inference. Install backend requirements including torch."
        ) from exc

    from .model_defs import PlainConvUNet2D, UNet2D

    return torch, PlainConvUNet2D, UNet2D


def _load_monai_dependencies() -> tuple[Any, Any]:
    try:
        from einops import rearrange as _rearrange  # noqa: F401
        from monai.inferers import sliding_window_inference
        from monai.networks.nets import SwinUNETR
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "MONAI and einops are required for Swin UNETR inference. Install backend requirements including monai and einops."
        ) from exc

    return SwinUNETR, sliding_window_inference


def _resolve_device(settings: Settings, torch: Any) -> Any:
    configured = settings.inference_device.lower()
    if configured == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")
    return torch.device(configured)


def discover_study_modalities(study_root: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for path in sorted(study_root.glob("*.nii*")):
        modality = modality_from_filename(path.name)
        if not modality:
            continue
        if modality in paths:
            raise ValueError(
                f"Duplicate modality detected for {modality}: {paths[modality].name}, {path.name}"
            )
        paths[modality] = path
    return paths


def _load_nifti(path: Path) -> NiftiVolume:
    image = nib.load(str(path))
    data = np.asarray(image.get_fdata(dtype=np.float32), dtype=np.float32)
    if data.ndim != 3:
        raise ValueError(f"{path.name} must be a 3D NIfTI volume.")
    spacing = tuple(float(value) for value in image.header.get_zooms()[:3])
    return NiftiVolume(
        data=data,
        affine=np.asarray(image.affine, dtype=np.float32),
        header=image.header.copy(),
        path=path,
        spacing=spacing,
    )


def _normalize_nonzero(volume: np.ndarray) -> np.ndarray:
    normalized = volume.astype(np.float32, copy=True)
    mask = normalized != 0
    if not np.any(mask):
        return normalized
    values = normalized[mask]
    mean = float(values.mean())
    std = float(values.std())
    if std < 1e-6:
        normalized[mask] = values - mean
        return normalized
    normalized[mask] = (values - mean) / std
    return normalized


def _pad_2d_channels(
    array: np.ndarray,
    divisor: int,
    *,
    minimum_size: int | None = None,
) -> tuple[np.ndarray, tuple[tuple[int, int], tuple[int, int]]]:
    height, width = array.shape[-2:]
    if minimum_size is not None:
        height = max(height, minimum_size)
        width = max(width, minimum_size)
    pad_h_total = (divisor - (height % divisor)) % divisor
    pad_w_total = (divisor - (width % divisor)) % divisor
    original_height, original_width = array.shape[-2:]
    if minimum_size is not None:
        pad_h_total = max(pad_h_total, height - original_height)
        pad_w_total = max(pad_w_total, width - original_width)
    pad_h = (pad_h_total // 2, pad_h_total - (pad_h_total // 2))
    pad_w = (pad_w_total // 2, pad_w_total - (pad_w_total // 2))
    padded = np.pad(array, ((0, 0), pad_h, pad_w), mode="constant")
    return padded, (pad_h, pad_w)


def _crop_2d(
    array: np.ndarray, padding: tuple[tuple[int, int], tuple[int, int]]
) -> np.ndarray:
    (pad_top, pad_bottom), (pad_left, pad_right) = padding
    height_end = array.shape[-2] - pad_bottom if pad_bottom else array.shape[-2]
    width_end = array.shape[-1] - pad_right if pad_right else array.shape[-1]
    return array[..., pad_top:height_end, pad_left:width_end]


def _validate_modalities(volumes: dict[str, NiftiVolume]) -> None:
    reference = next(iter(volumes.values()))
    for modality, volume in volumes.items():
        if volume.data.shape != reference.data.shape:
            raise ValueError(
                f"Shape mismatch for {modality}: expected {reference.data.shape}, found {volume.data.shape}."
            )
        if not np.allclose(volume.affine, reference.affine, atol=1e-3):
            raise ValueError(f"Affine mismatch detected for {modality}; all modalities must be aligned.")


def _load_synthesis_model(
    target_modality: str,
    settings: Settings,
    device: Any,
    torch: Any,
    UNet2D: Any,
) -> Any:
    checkpoint_path = settings.synthesis_root / target_modality / f"{target_modality}_synth_best.pth"
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Synthesis checkpoint not found: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    model = UNet2D(in_channels=int(checkpoint["in_channels"]))
    model.load_state_dict(checkpoint["model_state"])
    model.to(device)
    model.eval()
    return model


def _load_nnunet_model(settings: Settings, device: Any, torch: Any, PlainConvUNet2D: Any) -> Any:
    checkpoint_path = settings.segmentation_checkpoint
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"nnU-Net checkpoint not found: {checkpoint_path}")
    # The bundled training checkpoint contains NumPy scalars in its optimizer
    # and logging metadata. PyTorch's weights-only loader cannot deserialize
    # those fields. This path is the configured local model asset, not an upload.
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model = PlainConvUNet2D(in_channels=4, num_classes=4)
    model.load_state_dict(checkpoint["network_weights"], strict=True)
    model.to(device)
    model.eval()
    return model


def _load_swinunetr_model(settings: Settings, device: Any, torch: Any) -> tuple[Any, tuple[int, int, int]]:
    checkpoint_path = settings.swinunetr_checkpoint
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Swin UNETR checkpoint not found: {checkpoint_path}")

    SwinUNETR, _ = _load_monai_dependencies()
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    config = checkpoint.get("config", {}) if isinstance(checkpoint, dict) else {}
    roi_size = tuple(int(value) for value in config.get("roi_size", (96, 96, 96)))
    model = SwinUNETR(
        img_size=roi_size,
        in_channels=4,
        out_channels=4,
        feature_size=int(config.get("feature_size", 12)),
        drop_rate=0.0,
        attn_drop_rate=0.0,
        dropout_path_rate=float(config.get("drop_prob", 0.0)),
        use_checkpoint=False,
        spatial_dims=3,
    )
    model.load_state_dict(checkpoint["model_state"], strict=True)
    model.to(device)
    model.eval()
    return model, roi_size


def _synthesize_missing_modality(
    *,
    target_modality: str,
    normalized_modalities: dict[str, np.ndarray],
    volumes: dict[str, NiftiVolume],
    model: Any,
    device: Any,
    torch: Any,
) -> np.ndarray:
    source_modalities = SYNTHESIS_SOURCE_MODALITIES[target_modality]
    height, width, depth = next(iter(normalized_modalities.values())).shape
    synthesized = np.zeros((height, width, depth), dtype=np.float32)
    k = 2

    with torch.no_grad():
        for z in range(k, depth - k):
            channels = [
                normalized_modalities[modality][:, :, z - k : z + k + 1]
                for modality in source_modalities
            ]
            stacked = np.concatenate([np.moveaxis(item, -1, 0) for item in channels], axis=0)
            padded, padding = _pad_2d_channels(stacked, divisor=8)
            tensor = torch.from_numpy(padded[None, ...]).to(device=device, dtype=torch.float32)
            prediction = model(tensor).detach().cpu().numpy()[0, 0]
            prediction = _crop_2d(prediction, padding)
            synthesized[:, :, z] = prediction.astype(np.float32)

    background_mask = np.zeros_like(synthesized, dtype=bool)
    for modality in source_modalities:
        background_mask |= volumes[modality].data != 0
    synthesized[~background_mask] = 0
    return synthesized


def _segment_completed_modalities_nnunet(
    *,
    normalized_modalities: dict[str, np.ndarray],
    model: Any,
    device: Any,
    torch: Any,
) -> np.ndarray:
    ordered = [normalized_modalities[key] for key in SEGMENTATION_MODALITIES]
    height, width, depth = ordered[0].shape
    probabilities = np.zeros((4, height, width, depth), dtype=np.float32)

    with torch.no_grad():
        for z in range(depth):
            slice_stack = np.stack([volume[:, :, z] for volume in ordered], axis=0)
            padded, padding = _pad_2d_channels(slice_stack, divisor=32, minimum_size=64)
            tensor = torch.from_numpy(padded[None, ...]).to(device=device, dtype=torch.float32)
            logits = model(tensor)
            probs = torch.softmax(logits, dim=1).detach().cpu().numpy()[0]
            probs = _crop_2d(probs, padding)
            probabilities[:, :, :, z] = probs.astype(np.float32)

    return probabilities


def _segment_completed_modalities_swinunetr(
    *,
    normalized_modalities: dict[str, np.ndarray],
    model: Any,
    roi_size: tuple[int, int, int],
    overlap: float,
    device: Any,
    torch: Any,
) -> np.ndarray:
    _, sliding_window_inference = _load_monai_dependencies()
    ordered = [normalized_modalities[key].astype(np.float32) for key in SEGMENTATION_MODALITIES]
    stacked = np.stack(ordered, axis=0)

    with torch.no_grad():
        tensor = torch.from_numpy(stacked[None, ...]).to(device=device, dtype=torch.float32)
        logits = sliding_window_inference(
            inputs=tensor,
            roi_size=roi_size,
            sw_batch_size=1,
            predictor=model,
            overlap=overlap,
        )
        probabilities = torch.softmax(logits, dim=1)[0].detach().cpu().numpy().astype(np.float32)
    return probabilities


def _labels_from_probabilities(probabilities: np.ndarray) -> np.ndarray:
    return np.argmax(probabilities, axis=0).astype(np.uint8)


def _confidence_from_probabilities(probabilities: np.ndarray) -> np.ndarray:
    return np.max(probabilities, axis=0).astype(np.float32)


def _calibrate_confidence(
    ensemble_probabilities: np.ndarray,
    model_probability_maps: dict[str, np.ndarray],
) -> np.ndarray:
    base_confidence = _confidence_from_probabilities(ensemble_probabilities)
    if len(model_probability_maps) < 2:
        return base_confidence

    label_maps = [_labels_from_probabilities(probabilities) for probabilities in model_probability_maps.values()]
    agreement = np.ones_like(base_confidence, dtype=np.float32)
    for label_map in label_maps[1:]:
        agreement *= (label_map == label_maps[0]).astype(np.float32)
    calibrated = 0.8 * base_confidence + 0.2 * agreement
    return np.clip(calibrated, 0.0, 1.0).astype(np.float32)


def _ensemble_probabilities(model_probability_maps: OrderedDict[str, np.ndarray]) -> np.ndarray:
    probability_stack = np.stack(list(model_probability_maps.values()), axis=0)
    return np.mean(probability_stack, axis=0).astype(np.float32)


def _select_reference_modality(available_modalities: dict[str, np.ndarray]) -> str:
    for modality in PREFERRED_REFERENCE_MODALITIES:
        if modality in available_modalities:
            return modality
    return next(iter(available_modalities))


def _save_prediction_output(
    *,
    name: str,
    labels: np.ndarray,
    confidence: np.ndarray,
    processed_root: Path,
    affine: np.ndarray,
    header: nib.Nifti1Header,
    final_primary: bool = False,
) -> SegmentationOutput:
    segmentation_filename = "segmentation.nii.gz" if final_primary else f"{name}_segmentation.nii.gz"
    confidence_filename = "confidence_map.nii.gz" if final_primary else f"{name}_confidence_map.nii.gz"

    segmentation_path = processed_root / segmentation_filename
    segmentation_header = header.copy()
    segmentation_header.set_data_dtype(np.uint8)
    save_nifti(labels.astype(np.uint8), segmentation_path, affine=affine, header=segmentation_header)

    confidence_path = processed_root / confidence_filename
    confidence_header = header.copy()
    confidence_header.set_data_dtype(np.float32)
    save_nifti(confidence.astype(np.float32), confidence_path, affine=affine, header=confidence_header)

    return SegmentationOutput(
        name=name,
        labels=labels.astype(np.uint8),
        confidence=confidence.astype(np.float32),
        segmentation_path=segmentation_path,
        confidence_path=confidence_path,
    )


def run_study_pipeline(*, study_root: Path, processed_root: Path, settings: Settings) -> PipelineResult:
    start_time = perf_counter()
    torch, PlainConvUNet2D, UNet2D = _load_torch_dependencies()
    device = _resolve_device(settings, torch)

    modality_paths = discover_study_modalities(study_root)
    missing_modalities = [key for key in SEGMENTATION_MODALITIES if key not in modality_paths]
    if len(modality_paths) < 3:
        raise ValueError("At least three modality NIfTI files are required to run inference.")
    if len(missing_modalities) > 1:
        raise ValueError(
            "Only one missing modality is supported. Upload three or four BraTS-style modality files."
        )

    preprocessed_paths = preprocess_study_modalities(modality_paths, processed_root / "preprocessed")
    volumes = {modality: _load_nifti(path) for modality, path in preprocessed_paths.items()}
    _validate_modalities(volumes)
    normalized = {modality: _normalize_nonzero(volume.data) for modality, volume in volumes.items()}

    synthesized_paths: dict[str, Path] = {}
    missing_modality = missing_modalities[0] if missing_modalities else None
    if missing_modality:
        synthesis_model = _load_synthesis_model(
            target_modality=missing_modality,
            settings=settings,
            device=device,
            torch=torch,
            UNet2D=UNet2D,
        )
        synthesized_volume = _synthesize_missing_modality(
            target_modality=missing_modality,
            normalized_modalities=normalized,
            volumes=volumes,
            model=synthesis_model,
            device=device,
            torch=torch,
        )
        template = next(iter(volumes.values()))
        synthesized_header = template.header.copy()
        synthesized_header.set_data_dtype(np.float32)
        synthesized_path = processed_root / f"synthesized_{missing_modality}.nii.gz"
        save_nifti(
            synthesized_volume.astype(np.float32),
            synthesized_path,
            affine=template.affine,
            header=synthesized_header,
        )
        volumes[missing_modality] = NiftiVolume(
            data=synthesized_volume,
            affine=template.affine,
            header=synthesized_header,
            path=synthesized_path,
            spacing=template.spacing,
        )
        normalized[missing_modality] = synthesized_volume
        synthesized_paths[missing_modality] = synthesized_path

    reference_modality = _select_reference_modality(normalized)
    reference_metadata = volumes[reference_modality]
    reference_volume = normalized[reference_modality].astype(np.float32)
    reference_path = processed_root / f"reference_{reference_modality}.nii.gz"
    reference_header = reference_metadata.header.copy()
    reference_header.set_data_dtype(np.float32)
    save_nifti(reference_volume, reference_path, affine=reference_metadata.affine, header=reference_header)

    model_probability_maps: OrderedDict[str, np.ndarray] = OrderedDict()
    backend_mode = settings.segmentation_backend

    if backend_mode in {"auto", "ensemble", "nnunet2d"}:
        nnunet_required = backend_mode in {"ensemble", "nnunet2d"}
        try:
            nnunet_model = _load_nnunet_model(settings, device, torch, PlainConvUNet2D)
            model_probability_maps["nnunet"] = _segment_completed_modalities_nnunet(
                normalized_modalities=normalized,
                model=nnunet_model,
                device=device,
                torch=torch,
            )
        except Exception:
            if nnunet_required:
                raise
            logger.exception("nnU-Net inference unavailable during auto mode; continuing without it.")

    if backend_mode in {"auto", "ensemble", "swinunetr3d"}:
        swin_required = backend_mode in {"ensemble", "swinunetr3d"}
        try:
            swin_model, roi_size = _load_swinunetr_model(settings, device, torch)
            model_probability_maps["swinunetr"] = _segment_completed_modalities_swinunetr(
                normalized_modalities=normalized,
                model=swin_model,
                roi_size=roi_size,
                overlap=settings.swinunetr_overlap,
                device=device,
                torch=torch,
            )
        except Exception:
            if swin_required:
                raise
            logger.exception("Swin UNETR inference unavailable during auto mode; continuing without it.")

    if not model_probability_maps:
        raise RuntimeError("No segmentation backend is available for inference.")

    model_outputs: dict[str, SegmentationOutput] = {}
    model_metrics: dict[str, dict[str, float]] = {}
    for name, probabilities in model_probability_maps.items():
        labels = _labels_from_probabilities(probabilities)
        confidence = _confidence_from_probabilities(probabilities)
        output = _save_prediction_output(
            name=name,
            labels=labels,
            confidence=confidence,
            processed_root=processed_root,
            affine=reference_metadata.affine,
            header=reference_metadata.header,
        )
        model_outputs[name] = output
        model_metrics[name] = compute_metrics(
            labels=labels,
            uncertainty=confidence,
            spacing=reference_metadata.spacing,
            runtime_sec=0.0,
        )

    ensemble_probabilities = _ensemble_probabilities(model_probability_maps)
    ensemble_labels = _labels_from_probabilities(ensemble_probabilities)
    ensemble_confidence = _calibrate_confidence(ensemble_probabilities, model_probability_maps)
    ensemble_output = _save_prediction_output(
        name="ensemble",
        labels=ensemble_labels,
        confidence=ensemble_confidence,
        processed_root=processed_root,
        affine=reference_metadata.affine,
        header=reference_metadata.header,
        final_primary=True,
    )
    model_outputs["ensemble"] = ensemble_output

    runtime_sec = perf_counter() - start_time
    agreement_metrics: dict[str, float] = {}
    if "nnunet" in model_outputs and "swinunetr" in model_outputs:
        agreement_metrics = compute_model_agreement(
            model_outputs["nnunet"].labels,
            model_outputs["swinunetr"].labels,
            spacing=reference_metadata.spacing,
        )
    metrics = compute_metrics(
        labels=ensemble_labels,
        uncertainty=ensemble_confidence,
        spacing=reference_metadata.spacing,
        runtime_sec=runtime_sec,
        agreement_metrics=agreement_metrics,
    )
    model_metrics["ensemble"] = metrics

    logger.info(
        "Completed study pipeline using %s device; models=%s; missing modality=%s",
        device,
        ",".join(model_probability_maps.keys()),
        missing_modality or "none",
    )

    return PipelineResult(
        metrics=metrics,
        model_metrics=model_metrics,
        reference_volume=reference_volume,
        reference_affine=reference_metadata.affine,
        reference_header=reference_header,
        reference_path=reference_path,
        segmentation_path=ensemble_output.segmentation_path,
        confidence_path=ensemble_output.confidence_path,
        labels=ensemble_output.labels,
        confidence=ensemble_output.confidence,
        synthesized_paths=synthesized_paths,
        missing_modality=missing_modality,
        completed_modalities={key: normalized[key].astype(np.float32) for key in SEGMENTATION_MODALITIES},
        model_outputs=model_outputs,
        segmentation_backend="ensemble" if len(model_probability_maps) > 1 else next(iter(model_probability_maps)),
    )
