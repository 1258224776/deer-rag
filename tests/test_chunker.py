from __future__ import annotations

from app.core.models import SourceDocument
from app.ingestion.chunkers.fixed import FixedChunker


def make_document() -> SourceDocument:
    return SourceDocument(
        collection_id="collection-1",
        title="Chunker Test",
        source_uri="memory://chunker",
        source_type="text",
        checksum="checksum",
    )


def test_fixed_chunker_returns_single_chunk_for_small_text() -> None:
    chunker = FixedChunker(chunk_size=50, overlap=5, encoder_name="missing-encoder")
    document = make_document()

    chunks = chunker.chunk(document, "short text only")

    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].text == "short text only"


def test_fixed_chunker_splits_large_text_into_multiple_chunks() -> None:
    chunker = FixedChunker(chunk_size=8, overlap=2, encoder_name="missing-encoder")
    document = make_document()
    text = "one two three four five six seven eight nine ten eleven twelve"

    chunks = chunker.chunk(document, text)

    assert len(chunks) >= 2
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_fixed_chunker_applies_overlap_between_neighbor_chunks() -> None:
    chunker = FixedChunker(chunk_size=6, overlap=2, encoder_name="missing-encoder")
    document = make_document()
    text = "one two three four five six seven eight nine ten"

    chunks = chunker.chunk(document, text)

    assert len(chunks) >= 2
    first_words = chunks[0].text.split()
    second_words = chunks[1].text.split()
    assert first_words[-2:] == second_words[:2]
