from __future__ import annotations

from app.core.interfaces import BaseRetriever
from app.core.models import EvidencePack
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.dense import DenseRetriever


class HybridRetriever(BaseRetriever):
    def __init__(
        self,
        dense_retriever: DenseRetriever,
        bm25_retriever: BM25Retriever,
        rrf_k: int = 10,
    ) -> None:
        self.dense_retriever = dense_retriever
        self.bm25_retriever = bm25_retriever
        self.rrf_k = rrf_k
        self.candidate_multiplier = 2

    def retrieve(self, query: str, collection_id: str, top_k: int = 10, **kwargs) -> list[EvidencePack]:
        candidate_k = max(int(kwargs.get("candidate_k", top_k * self.candidate_multiplier)), top_k)
        dense_hits = self.dense_retriever.retrieve(query, collection_id, top_k=candidate_k, **kwargs)
        bm25_hits = self.bm25_retriever.retrieve(query, collection_id, top_k=candidate_k, **kwargs)

        fused: dict[str, EvidencePack] = {}
        self._apply_rrf(fused, dense_hits)
        self._apply_rrf(fused, bm25_hits)

        ranked = sorted(fused.values(), key=lambda item: item.score, reverse=True)
        return ranked[:top_k]

    def _apply_rrf(self, fused: dict[str, EvidencePack], hits: list[EvidencePack]) -> None:
        for rank, hit in enumerate(hits, start=1):
            fused_score = 1.0 / (self.rrf_k + rank)
            if hit.chunk_id not in fused:
                fused[hit.chunk_id] = hit.model_copy(
                    update={
                        "score": fused_score,
                        "metadata": {
                            **hit.metadata,
                            "retrieval": "hybrid",
                            "rrf_sources": [hit.metadata.get("retrieval")],
                        },
                    }
                )
                continue

            existing = fused[hit.chunk_id]
            sources = list(existing.metadata.get("rrf_sources", []))
            source_name = hit.metadata.get("retrieval")
            if source_name and source_name not in sources:
                sources.append(source_name)
            fused[hit.chunk_id] = existing.model_copy(
                update={
                    "score": existing.score + fused_score,
                    "metadata": {
                        **existing.metadata,
                        "rrf_sources": sources,
                    },
                }
            )
