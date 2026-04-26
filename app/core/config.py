from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, PrivateAttr


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_ENV_VAR = "DEER_RAG_CONFIG"


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


class ModelConfig(BaseModel):
    embedding_model_name: str = "BAAI/bge-small-zh-v1.5"
    reranker_model_name: str = "BAAI/bge-reranker-base"


class AppConfig(BaseModel):
    app_name: str = "deer-rag"
    env: str = "dev"
    paths: PathsConfig = Field(default_factory=PathsConfig)
    retrieval: RetrievalDefaults = Field(default_factory=RetrievalDefaults)
    models: ModelConfig = Field(default_factory=ModelConfig)
    extra: dict[str, Any] = Field(default_factory=dict)
    _loaded_from: str = PrivateAttr("defaults")
    _using_default_config: bool = PrivateAttr(True)

    @property
    def loaded_from(self) -> str:
        return self._loaded_from

    @property
    def using_default_config(self) -> bool:
        return self._using_default_config

    def mark_loaded(self, *, loaded_from: str, using_default_config: bool) -> "AppConfig":
        self._loaded_from = loaded_from
        self._using_default_config = using_default_config
        return self


DEFAULT_CONFIG = AppConfig()


def _build_default_config() -> AppConfig:
    return DEFAULT_CONFIG.model_copy(deep=True).mark_loaded(
        loaded_from="defaults",
        using_default_config=True,
    )


def _resolve_config_path(path: str | Path | None) -> Path | None:
    if path is not None:
        return Path(path)

    env_path = os.getenv(CONFIG_ENV_VAR)
    if env_path:
        return Path(env_path)

    return None


def load_config(path: str | Path | None = None) -> AppConfig:
    config_path = _resolve_config_path(path)
    if config_path is None:
        return _build_default_config()

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("Config file must contain a YAML mapping.")

    return AppConfig.model_validate(raw).mark_loaded(
        loaded_from=str(config_path.resolve()),
        using_default_config=False,
    )
