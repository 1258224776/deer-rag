from __future__ import annotations

import logging
from pathlib import Path

import pytest

from app.api.app import create_app
from app.core.config import CONFIG_ENV_VAR, load_config
from app.retrieval.rerank import CrossEncoderReranker


def test_cross_encoder_reranker_defaults_to_chinese_model() -> None:
    reranker = CrossEncoderReranker()

    assert reranker.model_name == "BAAI/bge-reranker-base"


def test_load_config_uses_defaults_when_no_path_is_provided(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)

    config = load_config()

    assert config.using_default_config is True
    assert config.loaded_from == "defaults"
    assert config.models.reranker_model_name == "BAAI/bge-reranker-base"


def test_load_config_raises_for_missing_explicit_path(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing-config.yaml"

    with pytest.raises(FileNotFoundError, match="Config file not found"):
        load_config(missing_path)


def test_load_config_reads_path_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = tmp_path / "deer-rag.yaml"
    config_path.write_text(
        """
app_name: deer-rag-test
models:
  embedding_model_name: custom-embed
  reranker_model_name: custom-reranker
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv(CONFIG_ENV_VAR, str(config_path))

    config = load_config()

    assert config.using_default_config is False
    assert config.loaded_from == str(config_path.resolve())
    assert config.models.embedding_model_name == "custom-embed"
    assert config.models.reranker_model_name == "custom-reranker"


def test_create_app_logs_effective_config(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)

    with caplog.at_level(logging.INFO):
        app = create_app()

    assert app.title == "deer-rag"
    assert "config source=defaults" in caplog.text
    assert "reranker_model=BAAI/bge-reranker-base" in caplog.text
