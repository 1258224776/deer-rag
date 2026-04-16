from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.core.models import Chunk, SourceDocument
from app.ingestion.service import IngestionService


class FakeStore:
    def __init__(self, duplicate_checksums: set[str] | None = None) -> None:
        self.duplicate_checksums = duplicate_checksums or set()
        self.saved_documents: list[SourceDocument] = []
        self.saved_chunks: list[Chunk] = []

    def checksum_exists(self, checksum: str, *, collection_id: str | None = None) -> bool:
        return checksum in self.duplicate_checksums

    def upsert_source_document(self, document: SourceDocument) -> None:
        self.saved_documents.append(document)

    def upsert_chunks(self, chunks: list[Chunk]) -> None:
        self.saved_chunks.extend(chunks)


class FakeChunker:
    def chunk(self, document: SourceDocument, text: str, **kwargs) -> list[Chunk]:
        return [
            Chunk(
                document_id=document.id,
                chunk_index=0,
                text=text,
                token_count=max(1, len(text.split())),
            )
        ]


def test_ingestion_service_persists_document_and_chunks_for_new_text() -> None:
    store = FakeStore()
    service = IngestionService(store=store, chunker=FakeChunker())

    result = service.ingest_text(
        collection_id="collection-1",
        title="Doc",
        text="hello ingestion",
        source_uri="memory://doc",
        source_type="text",
    )

    assert result.was_duplicate is False
    assert len(result.chunks) == 1
    assert len(store.saved_documents) == 1
    assert len(store.saved_chunks) == 1


def test_ingestion_service_skips_duplicate_persistence() -> None:
    store = FakeStore(duplicate_checksums={"2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"})
    service = IngestionService(store=store, chunker=FakeChunker())

    result = service.ingest_text(
        collection_id="collection-1",
        title="Doc",
        text="hello",
        source_uri="memory://doc",
        source_type="text",
    )

    assert result.was_duplicate is True
    assert result.chunks == []
    assert store.saved_documents == []
    assert store.saved_chunks == []


def test_ingestion_service_persists_raw_text_when_directory_is_configured() -> None:
    store = FakeStore()
    raw_dir = Path("C:/Users/admin/.codex/memories/deer_rag_test_raw") / uuid4().hex
    raw_dir.mkdir(parents=True, exist_ok=True)
    service = IngestionService(store=store, chunker=FakeChunker(), raw_text_dir=raw_dir)

    result = service.ingest_text(
        collection_id="collection-1",
        title="Doc",
        text="hello raw text",
        source_uri="memory://doc",
        source_type="text",
    )

    assert result.document.raw_text_path is not None
    raw_path = Path(result.document.raw_text_path)
    assert raw_path.exists()
    assert raw_path.read_text(encoding="utf-8") == "hello raw text"
