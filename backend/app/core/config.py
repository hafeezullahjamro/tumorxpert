from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_ROOT / ".env"),
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    app_name: str = "TumorXpert"
    env: Literal["local", "dev", "prod"] = "local"

    backend_host: str = "127.0.0.1"
    backend_port: int = 8000

    storage_root: Path = Path("./storage")
    auto_delete_enabled: bool = True
    auto_delete_days: int = 7
    model_root: Path = PROJECT_ROOT / "all best models"
    inference_device: str = "auto"
    segmentation_backend: Literal["auto", "ensemble", "nnunet2d", "swinunetr3d"] = "auto"
    swinunetr_overlap: float = 0.25

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "tumorxpert"
    postgres_user: str = "tx_user"
    postgres_password: str = "tx_password"

    redis_url: str = "redis://localhost:6379/0"
    database_url_override: str | None = Field(
        default=None, validation_alias="DATABASE_URL"
    )

    @field_validator("storage_root", "model_root")
    @classmethod
    def resolve_local_paths(cls, value: Path) -> Path:
        return value if value.is_absolute() else (BACKEND_ROOT / value).resolve()

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        ).render_as_string(hide_password=False)

    @property
    def storage_uploads(self) -> Path:
        return self.storage_root / "uploads"

    @property
    def storage_processed(self) -> Path:
        return self.storage_root / "processed"

    @property
    def storage_exports(self) -> Path:
        return self.storage_root / "exports"

    @property
    def storage_temp(self) -> Path:
        return self.storage_root / "temp"

    @property
    def segmentation_checkpoint(self) -> Path:
        return (
            self.model_root
            / "segmentation"
            / "nnunet_brats2d_best"
            / "fold_all"
            / "checkpoint_best.pth"
        )

    @property
    def synthesis_root(self) -> Path:
        return self.model_root / "synthesis"

    @property
    def swinunetr_checkpoint(self) -> Path:
        return self.model_root / "swinunetr" / "best.pth"


@lru_cache
def get_settings() -> Settings:
    return Settings()
