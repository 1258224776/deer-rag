from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.models import Chunk
from app.indexing.dense import FaissDenseIndex
from app.indexing.lexical import BM25LexicalIndex
from app.storage import SQLiteMetadataStore


@dataclass
class CollectionIndexPaths:
    collection_dir: Path
    dense_index_path: Path
    dense_meta_path: Path
    lexical_state_path: Path


class CollectionIndexRegistry:
    def __init__(self, store: SQLiteMetadataStore, base_dir: str | Path = "data/indexes") -> None:
        self.store = store
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def paths_for(self, collection_id: str) -> CollectionIndexPaths:
        collection_dir = self.base_dir / collection_id
        collection_dir.mkdir(parents=True, exist_ok=True)
        return CollectionIndexPaths(
            collection_dir=collection_dir,
            dense_index_path=collection_dir / "dense.faiss",
            dense_meta_path=collection_dir / "dense.meta.json",
            lexical_state_path=collection_dir / "bm25.json",
        )

    def list_chunks(self, collection_id: str) -> list[Chunk]:
        return self.store.list_chunks(collection_id)

    def build_collection_indexes(self, collection_id: str) -> dict[str, int]:
        chunks = self.list_chunks(collection_id)
        paths = self.paths_for(collection_id)

        dense_index = FaissDenseIndex(
            index_path=paths.dense_index_path,
            meta_path=paths.dense_meta_path,
        )
        lexical_index = BM25LexicalIndex(state_path=paths.lexical_state_path)

        dense_count = dense_index.build(chunks)
        lexical_count = lexical_index.build(chunks)

        return {
            "collection_id": collection_id,
            "chunk_count": len(chunks),
            "dense_indexed": dense_count,
            "lexical_indexed": lexical_count,
        }
