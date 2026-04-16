from __future__ import annotations

from fastapi import FastAPI

from app.api.routers import router
from app.core.config import load_config


def create_app() -> FastAPI:
    config = load_config()
    app = FastAPI(title=config.app_name)
    app.include_router(router)
    return app
