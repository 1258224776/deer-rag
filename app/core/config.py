from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class PathsConfig(BaseModel):
    data_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "data")
    metadata_db: Path = Field(default_factory=lambda: PROJECT_ROOT / "data" / "metadata.sqlite3")
    artifacts_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "data" / "artifacts")
    experiments_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "data" / "experiments")
    raw_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "data" / "raw")
    evaluation_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "data" / "evaluation")


class RetrievalDefaults(BaseModel):
    top_k: int = 8
    hybrid_rrf_k: int = 10
    default_budget_total: int = 6000
    default_budget_reserve: int = 1000
    default_budget_per_evidence: int = 600


class AppConfig(BaseModel):
    app_name: str = "deer-rag"
    env: str = "dev"
    paths: PathsConfig = Field(default_factory=PathsConfig)
    retrieval: RetrievalDefaults = Field(default_factory=RetrievalDefaults)
    extra: dict[str, Any] = Field(default_factory=dict)


DEFAULT_CONFIG = AppConfig()


def load_config(path: str | Path | None = None) -> AppConfig:
    if path is None:
        return DEFAULT_CONFIG

    config_path = Path(path)
    if not config_path.exists():
        return DEFAULT_CONFIG

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return AppConfig.model_validate(raw)
