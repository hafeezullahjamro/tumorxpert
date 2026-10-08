from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional

from fastapi import UploadFile

from ..core.config import Settings

logger = logging.getLogger(__name__)


def compute_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class StoredFile:
    kind: str
    path: Path
    size_bytes: int
    checksum: str


class StorageService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def study_root(self, study_id: str) -> Path:
        return Path(self.settings.storage_uploads) / study_id

    def processed_root(self, study_id: str) -> Path:
        return Path(self.settings.storage_processed) / study_id

    def exports_root(self, study_id: str) -> Path:
        return Path(self.settings.storage_exports) / study_id

    def ensure_study_structure(self, study_id: str) -> None:
        for base in (self.study_root(study_id), self.processed_root(study_id), self.exports_root(study_id)):
            base.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, study_id: str, upload: UploadFile, filename: str, kind: str) -> StoredFile:
        data = await upload.read()
        return self.save_upload_bytes(study_id, data, filename, kind)

    def save_upload_bytes(
        self,
        study_id: str,
        data: bytes,
        filename: str,
        kind: str,
    ) -> StoredFile:
        self.ensure_study_structure(study_id)
        checksum = compute_checksum(data)
        # Browser uploads can contain Unix or Windows path prefixes. Store only
        # the filename so an upload always stays within its study directory.
        safe_filename = Path(filename.replace("\\", "/")).name
        if safe_filename in ("", ".", ".."):
            raise ValueError("Uploaded file must have a filename.")
        destination = self.study_root(study_id) / safe_filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        logger.info("Saved upload %s (%s bytes)", destination, len(data))
        return StoredFile(
            kind=kind,
            path=destination,
            size_bytes=len(data),
            checksum=checksum,
        )

    def save_bytes(self, study_id: str, subdir: str, filename: str, data: bytes) -> Path:
        root_map = {
            "uploads": self.study_root,
            "processed": self.processed_root,
            "exports": self.exports_root,
        }
        if subdir not in root_map:
            raise ValueError(f"Unknown subdir '{subdir}'")
        path = root_map[subdir](study_id) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def save_text(self, study_id: str, subdir: str, filename: str, text: str) -> Path:
        return self.save_bytes(study_id, subdir, filename, text.encode("utf-8"))

    def save_file(self, study_id: str, subdir: str, filename: str, source: Path) -> Path:
        destination = self.save_bytes(study_id, subdir, filename, source.read_bytes())
        return destination

    def remove_study(self, study_id: str) -> None:
        import shutil

        for base in (
            self.study_root(study_id),
            self.processed_root(study_id),
            self.exports_root(study_id),
        ):
            if base.exists():
                shutil.rmtree(base, ignore_errors=True)

    def directory_stats(self, path: Path) -> tuple[int, int]:
        total_size = 0
        total_files = 0
        if not path.exists():
            return total_size, total_files
        for file in path.glob("**/*"):
            if file.is_file():
                total_files += 1
                total_size += file.stat().st_size
        return total_size, total_files

    def collect_storage_usage(self) -> dict[str, dict[str, int]]:
        mapping = {
            "uploads": Path(self.settings.storage_uploads),
            "processed": Path(self.settings.storage_processed),
            "exports": Path(self.settings.storage_exports),
            "temp": Path(self.settings.storage_temp),
        }
        stats = {}
        for key, path in mapping.items():
            size, files = self.directory_stats(path)
            stats[key] = {"bytes": size, "files": files}
        return stats

    def cleanup_older_than(self, days: int) -> list[Path]:
        threshold = datetime.now(timezone.utc) - timedelta(days=days)
        removed: list[Path] = []
        for base in (self.settings.storage_uploads, self.settings.storage_processed, self.settings.storage_exports):
            base_path = Path(base)
            if not base_path.exists():
                continue
            for study_dir in base_path.iterdir():
                if not study_dir.is_dir():
                    continue
                newest_file_time = max(
                    (datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc) for f in study_dir.glob("**/*") if f.is_file()),
                    default=datetime.fromtimestamp(study_dir.stat().st_mtime, tz=timezone.utc),
                )
                if newest_file_time < threshold:
                    import shutil

                    shutil.rmtree(study_dir, ignore_errors=True)
                    removed.append(study_dir)
        return removed


class AutoDeleteManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._sleep_override: Optional[float] = None  # exposed for tests

    async def start(self) -> None:
        if not self.settings.auto_delete_enabled:
            logger.info("Auto-delete disabled by configuration.")
            return
        if self._task and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Auto-delete background task started.")

    async def stop(self) -> None:
        if not self._task:
            return
        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        logger.info("Auto-delete background task stopped.")

    async def _run_loop(self) -> None:
        storage = StorageService(self.settings)
        while not self._stop_event.is_set():
            try:
                removed = storage.cleanup_older_than(self.settings.auto_delete_days)
                if removed:
                    logger.info("Auto-delete removed %d studies.", len(removed))
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Auto-delete failed: %s", exc)
            wait_seconds = self._sleep_override or 24 * 3600
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=wait_seconds)
            except asyncio.TimeoutError:
                continue
