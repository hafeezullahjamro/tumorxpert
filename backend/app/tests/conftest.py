from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

# Set these before importing application modules. Tests must never reuse the
# configured PostgreSQL database or delete real MRI files during teardown.
_test_directory = tempfile.TemporaryDirectory(prefix="tumorxpert-tests-")
_test_root = Path(_test_directory.name)
_original_environment = {
    key: os.environ.get(key)
    for key in ("DATABASE_URL", "STORAGE_ROOT", "AUTO_DELETE_ENABLED")
}
os.environ["DATABASE_URL"] = f"sqlite:///{_test_root / 'test.db'}"
os.environ["STORAGE_ROOT"] = str(_test_root / "storage")
os.environ["AUTO_DELETE_ENABLED"] = "false"

from app.core.config import get_settings


@pytest.fixture(scope="session", autouse=True)
def setup_environment() -> Generator[None, None, None]:
    storage_root = Path(os.environ["STORAGE_ROOT"])
    storage_root.mkdir(parents=True, exist_ok=True)

    get_settings.cache_clear()

    from app.db.base import Base, engine

    Base.metadata.create_all(bind=engine)

    yield

    engine.dispose()
    _test_directory.cleanup()
    get_settings.cache_clear()
    for key, value in _original_environment.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
