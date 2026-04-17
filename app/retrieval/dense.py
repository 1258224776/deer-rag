from __future__ import annotations

import numpy as np

from app.core.interfaces import BaseRetriever
from app.core.models import EvidencePack
from app.indexing.dense import FaissDenseIndex
from app.indexing.registry import CollectionIndexRegistry
from app.storage import SQLiteMetadataStore


class DenseRetriever(BaseRetriever):
    def __init__(
        self,
        registry: CollectionIndexRegistry,
        store: SQLiteMetadataStore,
        model_name: str = "BAAI/bge-small-zh-v1.5",
    ) -> None:
        self.registry = registry
        self.store = store
        self.model_name = model_name
        self._loaded_collection_id: str | None = None
        self._index = None
        self._chunk_ids: list[str] = []
        self._dense_index: FaissDenseIndex | None = None

    def _ensure_loaded(self, collection_id: str) -> tuple[FaissDenseIndex, object | None, list[str]]:
        if self._loaded_collection_id == collection_id and self._dense_index is not None:
            return self._dense_index, self._index, self._chunk_ids

        paths = self.registry.paths_for(collection_id)
        dense_index = FaissDenseIndex(
            index_path=paths.dense_index_path,
            meta_path=paths.dense_meta_path,
            model_name=self.model_name,
        )
        index, chunk_ids = dense_index.load()
        self._loaded_collection_id = collection_id
        self._dense_index = dense_index
        self._index = index
        self._chunk_ids = chunk_ids
        return dense_index, index, chunk_ids

    def retrieve(self, query: str, collection_id: str, top_k: int = 10, **kwargs) -> list[EvidencePack]:
        dense_index, index, chunk_ids = self._ensure_loaded(collection_id)
        if index is None or not chunk_ids:
            return []

        query_vector = dense_index.model.encode(
            [query],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        scores, indices = index.search(np.asarray(query_vector, dtype="float32"), min(top_k, len(chunk_ids)))

        ranked_ids: list[str] = []
        score_map: dict[str, float] = {}
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(chunk_ids):
                continue
            chunk_id = chunk_ids[idx]
            ranked_ids.append(chunk_id)
            score_map[chunk_id] = float(score)

        records = self.store.get_chunk_records_by_ids(ranked_ids)
        return [
            EvidencePack(
                chunk_id=record["chunk"].id,
                document_id=record["document"].id,
                snippet=record["chunk"].text,
                title=record["document"].title,
                source=record["document"].source_uri,
                score=score_map.get(record["chunk"].id, 0.0),
                token_estimate=record["chunk"].token_count,
                metadata={
                    "chunk_index": record["chunk"].chunk_index,
                    "section_title": record["chunk"].section_title,
                    "document_metadata": record["document"].metadata,
                    "chunk_metadata": record["chunk"].metadata,
                    "source_type": record["document"].source_type,
                    "published_at": (
                        record["document"].published_at.isoformat() if record["document"].published_at is not None else None
                    ),
                    "ingested_at": record["document"].ingested_at.isoformat(),
                    "retrieval": "dense",
                },
            )
            for record in records
        ]
