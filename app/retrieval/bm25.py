from __future__ import annotations

from app.core.interfaces import BaseRetriever
from app.core.models import EvidencePack
from app.indexing.lexical import BM25LexicalIndex
from app.indexing.registry import CollectionIndexRegistry
from app.retrieval.text import tokenize_text
from app.storage import SQLiteMetadataStore


class BM25Retriever(BaseRetriever):
    def __init__(self, registry: CollectionIndexRegistry, store: SQLiteMetadataStore) -> None:
        self.registry = registry
        self.store = store
        self._loaded_collection_id: str | None = None
        self._bm25 = None
        self._chunk_ids: list[str] = []

    def _ensure_loaded(self, collection_id: str):
        if self._loaded_collection_id == collection_id:
            return self._bm25, self._chunk_ids

        paths = self.registry.paths_for(collection_id)
        lexical_index = BM25LexicalIndex(state_path=paths.lexical_state_path)
        bm25, chunk_ids = lexical_index.load()
        self._loaded_collection_id = collection_id
        self._bm25 = bm25
        self._chunk_ids = chunk_ids
        return bm25, chunk_ids

    def retrieve(self, query: str, collection_id: str, top_k: int = 10, **kwargs) -> list[EvidencePack]:
        bm25, chunk_ids = self._ensure_loaded(collection_id)
        if bm25 is None or not chunk_ids:
            return []

        query_tokens = tokenize_text(query)
        scores = bm25.get_scores(query_tokens)
        ranked_pairs = sorted(
            ((chunk_ids[idx], float(score)) for idx, score in enumerate(scores)),
            key=lambda item: item[1],
            reverse=True,
        )[:top_k]

        ranked_ids = [chunk_id for chunk_id, _score in ranked_pairs]
        score_map = {chunk_id: score for chunk_id, score in ranked_pairs}
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
                    "retrieval": "bm25",
                },
            )
            for record in records
        ]
