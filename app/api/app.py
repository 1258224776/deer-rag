from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import router
from app.core.config import load_config


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    config = load_config()
    logger.info(
        "Starting %s with config source=%s default_config=%s embedding_model=%s reranker_model=%s data_dir=%s metadata_db=%s",
        config.app_name,
        config.loaded_from,
        config.using_default_config,
        config.models.embedding_model_name,
        config.models.reranker_model_name,
        config.paths.data_dir,
        config.paths.metadata_db,
    )
    app = FastAPI(title=config.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app
