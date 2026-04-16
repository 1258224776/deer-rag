from __future__ import annotations

from pathlib import Path

import yaml


def load_experiment_config(path: str | Path, *, allowed_dir: str | Path | None = None) -> dict:
    config_path = Path(path)
    if allowed_dir is not None:
        resolved = config_path.resolve()
        allowed = Path(allowed_dir).resolve()
        try:
            resolved.relative_to(allowed)
        except ValueError as exc:
            raise ValueError("config_path must be within the experiments directory") from exc
        config_path = resolved
    if not config_path.exists():
        raise FileNotFoundError(f"Experiment config not found: {config_path}")
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("Experiment config must be a YAML mapping")
    return payload
