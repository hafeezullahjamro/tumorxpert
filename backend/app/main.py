from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import Settings, get_settings
from .core.logging import configure_logging
from .core.paths import ensure_storage_tree
from .routers import admin, comparisons, health, inference, reports, studies, users
from .services.storage import AutoDeleteManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = get_settings()
    configure_logging()
    ensure_storage_tree(settings)
    # This local app runs one API worker. A run from an earlier worker cannot
    # still be executing after a fresh server startup.
    from sqlalchemy import select
    from .db.base import SessionLocal
    from .db.models import Study
    from .services.progress import timestamp
    with SessionLocal() as db:
        for study in db.scalars(select(Study).where(Study.status == "PROCESSING")):
            study.status = "FAILED"
            if study.progress:
                snapshot = dict(study.progress)
                snapshot.update(status="FAILED", error="Processing was interrupted by a backend restart. Retry this study.", finished_at=timestamp(), updated_at=timestamp())
                for stage in snapshot.get("stages", []):
                    for item in [stage, *stage.get("children", [])]:
                        if item["status"] == "RUNNING":
                            item["status"] = "FAILED"
                study.progress = snapshot
        db.commit()

    auto_delete_manager = AutoDeleteManager(settings)
    await auto_delete_manager.start()
    app.state.auto_delete_manager = auto_delete_manager

    try:
        yield
    finally:
        await auto_delete_manager.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="TumorXpert backend for brain tumor MRI workflows.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(users.router, prefix="/auth", tags=["auth"])
    app.include_router(studies.router, prefix="/studies", tags=["studies"])
    app.include_router(inference.router, prefix="/studies", tags=["inference"])
    app.include_router(reports.router, prefix="/studies", tags=["reports"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])
    app.include_router(comparisons.router, tags=["comparisons"])

    return app


app = create_app()


@app.get("/")
async def root():
    return {"message": "TumorXpert backend ready"}
