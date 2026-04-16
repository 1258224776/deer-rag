from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class EvaluationCase(BaseModel):
    query: str
    gold_chunk_ids: list[str] = Field(default_factory=list)
    top_k: int | None = None
    candidate_k: int | None = None
    rerank: bool | None = None


class EvaluationDataset(BaseModel):
    collection_id: str
    cases: list[EvaluationCase] = Field(default_factory=list)


def load_evaluation_dataset(path: str | Path, *, allowed_dir: str | Path | None = None) -> EvaluationDataset:
    dataset_path = Path(path)
    if allowed_dir is not None:
        resolved = dataset_path.resolve()
        allowed = Path(allowed_dir).resolve()
        try:
            resolved.relative_to(allowed)
        except ValueError as exc:
            raise ValueError("dataset_path must be within the evaluation directory") from exc
        dataset_path = resolved

    if not dataset_path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found: {dataset_path}")

    payload = yaml.safe_load(dataset_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("Evaluation dataset must be a YAML mapping")
    return EvaluationDataset.model_validate(payload)
