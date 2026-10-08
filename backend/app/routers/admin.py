from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Request

from ..core.config import Settings, get_settings
from ..services.storage import StorageService

router = APIRouter()


class RetentionUpdate(BaseModel):
    days: int = Field(ge=1, le=365)
    enabled: bool | None = None


@router.get("/storage")
def storage_overview(settings: Settings = Depends(get_settings)):
    storage = StorageService(settings)
    usage = storage.collect_storage_usage()
    return {"usage": usage, "auto_delete_days": settings.auto_delete_days, "auto_delete_enabled": settings.auto_delete_enabled}


@router.post("/retention")
async def update_retention(
    payload: RetentionUpdate,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    settings.auto_delete_days = payload.days
    if payload.enabled is not None:
        settings.auto_delete_enabled = payload.enabled
    manager = request.app.state.auto_delete_manager
    if settings.auto_delete_enabled:
        await manager.start()
    else:
        await manager.stop()
    return {"auto_delete_days": settings.auto_delete_days, "auto_delete_enabled": settings.auto_delete_enabled}
