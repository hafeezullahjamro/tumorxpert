from __future__ import annotations

from pathlib import Path

from .config import BACKEND_ROOT, Settings


def resolve_artifact_path(path: str | Path, settings: Settings) -> Path:
    """Resolve stored artifact paths after moving a local project folder."""
    original = Path(path)
    anchored = original if original.is_absolute() else BACKEND_ROOT / original
    if anchored.is_file():
        return anchored

    # Older Windows runs may have stored absolute paths. Keep the storage
    # suffix and look under the current configured storage directory.
    parts = str(path).replace("\\", "/").split("/")
    for index, part in enumerate(parts):
        if part in {"uploads", "processed", "exports", "temp"}:
            candidate = settings.storage_root.joinpath(*parts[index:]).resolve()
            if candidate.is_relative_to(settings.storage_root.resolve()) and candidate.is_file():
                return candidate
    return anchored


def ensure_storage_tree(settings: Settings) -> None:
    """Ensure expected storage directories exist."""
    for path in (
        settings.storage_root,
        settings.storage_uploads,
        settings.storage_processed,
        settings.storage_exports,
        settings.storage_temp,
    ):
        Path(path).mkdir(parents=True, exist_ok=True)
