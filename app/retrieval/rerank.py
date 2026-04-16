from __future__ import annotations

from sentence_transformers.cross_encoder import CrossEncoder

from app.core.interfaces import BaseReranker
from app.core.models import EvidencePack


class CrossEncoderReranker(BaseReranker):
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self.model_name = model_name
        self._model: CrossEncoder | None = None

    @property
    def model(self) -> CrossEncoder:
        if self._model is None:
            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(self, query: str, candidates: list[EvidencePack], top_k: int | None = None, **kwargs) -> list[EvidencePack]:
        if not candidates:
            return []

        pairs = [(query, candidate.snippet) for candidate in candidates]
        scores = self.model.predict(pairs)

        reranked = [
            candidate.model_copy(
                update={
                    "rerank_score": float(score),
                    "metadata": {
                        **candidate.metadata,
                        "reranker": self.model_name,
                    },
                }
            )
            for candidate, score in zip(candidates, scores)
        ]
        reranked.sort(key=lambda item: item.rerank_score or float("-inf"), reverse=True)
        if top_k is not None:
            return reranked[:top_k]
        return reranked
