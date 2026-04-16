from __future__ import annotations

from pathlib import Path

from app.core.interfaces import BaseChunker
from app.core.models import IngestionResult, SourceDocument
from app.ingestion.chunkers import FixedChunker
from app.ingestion.dedup import sha256_text
from app.storage.metadata import SQLiteMetadataStore


class IngestionService:
    def __init__(
        self,
        store: SQLiteMetadataStore,
        chunker: BaseChunker | None = None,
        raw_text_dir: str | Path | None = None,
    ) -> None:
        self.store = store
        self.chunker = chunker or FixedChunker()
        self.raw_text_dir = Path(raw_text_dir) if raw_text_dir is not None else None
        if self.raw_text_dir is not None:
            self.raw_text_dir.mkdir(parents=True, exist_ok=True)

    def ingest_text(
        self,
        *,
        collection_id: str,
        title: str,
        text: str,
        source_uri: str,
        source_type: str,
        raw_text_path: str | None = None,
        metadata: dict | None = None,
    ) -> IngestionResult:
        normalized_text = text.strip()
        checksum = sha256_text(normalized_text)
        is_duplicate = self.store.checksum_exists(checksum, collection_id=collection_id)
        effective_raw_text_path = raw_text_path or self._persist_raw_text(
            collection_id=collection_id,
            checksum=checksum,
            text=normalized_text,
        )

        document = SourceDocument(
            collection_id=collection_id,
            title=title,
            source_uri=source_uri,
            source_type=source_type,
            checksum=checksum,
            raw_text_path=effective_raw_text_path,
            metadata=metadata or {},
        )

        chunks = [] if is_duplicate else self.chunker.chunk(document, normalized_text)
        result = IngestionResult(
            document=document,
            chunks=chunks,
            text=normalized_text,
            was_duplicate=is_duplicate,
        )
        if not is_duplicate:
            self.store.upsert_source_document(document)
            self.store.upsert_chunks(chunks)
        return result

    def _persist_raw_text(self, *, collection_id: str, checksum: str, text: str) -> str | None:
        if self.raw_text_dir is None:
            return None
        collection_dir = self.raw_text_dir / collection_id
        collection_dir.mkdir(parents=True, exist_ok=True)
        path = collection_dir / f"{checksum}.txt"
        if not path.exists():
            path.write_text(text, encoding="utf-8")
        return str(path)
