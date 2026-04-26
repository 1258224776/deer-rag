from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.models import Chunk


class FaissDenseIndex:
    DEFAULT_MODEL_NAME = "BAAI/bge-small-zh-v1.5"

    def __init__(self, index_path: str | Path, meta_path: str | Path, model_name: str = DEFAULT_MODEL_NAME) -> None:
        self.index_path = Path(index_path)
        self.meta_path = Path(meta_path)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.meta_path.parent.mkdir(parents=True, exist_ok=True)
        self.model_name = model_name
        self._model: SentenceTransformer | None = None
        self._chunk_ids: list[str] = []

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def build(self, chunks: list[Chunk]) -> int:
        texts = [chunk.text for chunk in chunks]
        self._chunk_ids = [chunk.id for chunk in chunks]

        if not texts:
            if self.index_path.exists():
                self.index_path.unlink()
            self.meta_path.write_text(json.dumps({"chunk_ids": []}, ensure_ascii=False), encoding="utf-8")
            return 0

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        vectors = np.asarray(embeddings, dtype="float32")
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        faiss.write_index(index, str(self.index_path))
        self.meta_path.write_text(json.dumps({"chunk_ids": self._chunk_ids}, ensure_ascii=False), encoding="utf-8")
        return len(texts)

    def load(self) -> tuple[faiss.Index | None, list[str]]:
        if not self.index_path.exists() or not self.meta_path.exists():
            return None, []
        index = faiss.read_index(str(self.index_path))
        payload = json.loads(self.meta_path.read_text(encoding="utf-8"))
        chunk_ids = payload.get("chunk_ids", [])
        return index, chunk_ids
