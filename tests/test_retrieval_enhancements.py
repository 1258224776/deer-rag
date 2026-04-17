from __future__ import annotations

from datetime import datetime, timezone

from app.context.optimizer import ContextOptimizer
from app.core.models import Chunk, EvidencePack, FreshnessConfig, GraphExpansionConfig, MetadataFilters, RetrievalOptions, SourceDocument, TokenBudget
from app.retrieval.pipeline import RetrievalPipeline
from app.retrieval.query_rewrite import RuleBasedQueryRewriter
from app.retrieval.text import tokenize_text


class FakeRetriever:
    def __init__(self, items: list[EvidencePack]) -> None:
        self.items = items

    def retrieve(self, query: str, collection_id: str, top_k: int = 10, **kwargs):
        return self.items[:top_k]


class FakeReranker:
    def rerank(self, query: str, candidates: list[EvidencePack], top_k: int | None = None, **kwargs):
        ranked = sorted(candidates, key=lambda item: item.score, reverse=True)
        return ranked[:top_k] if top_k is not None else ranked


class FakeStore:
    def __init__(self, documents: list[SourceDocument], chunks: list[Chunk]) -> None:
        self.documents = documents
        self.chunks = chunks

    def list_documents(self, collection_id: str) -> list[SourceDocument]:
        return [item for item in self.documents if item.collection_id == collection_id]

    def list_chunks(self, collection_id: str) -> list[Chunk]:
        document_ids = {item.id for item in self.list_documents(collection_id)}
        return [item for item in self.chunks if item.document_id in document_ids]


def test_tokenize_text_supports_cjk_bigrams_and_compatibility_block() -> None:
    tokens = tokenize_text("\u6df7\u5408\u68c0\u7d22 RAG \ufa11")

    assert "\u6df7\u5408" in tokens
    assert "\u68c0\u7d22" in tokens
    assert "rag" in tokens
    assert "\ufa11" in tokens


def test_tokenize_text_filters_cjk_stopwords_and_avoids_cross_stopword_bigrams() -> None:
    tokens = tokenize_text("\u8bf7\u95ee\u6df7\u5408\u68c0\u7d22\u600e\u4e48\u5de5\u4f5c")

    assert "\u8bf7\u95ee" not in tokens
    assert "\u600e\u4e48" not in tokens
    assert "\u95ee\u6df7" not in tokens
    assert "\u7d22\u600e" not in tokens
    assert "\u6df7\u5408" in tokens
    assert "\u68c0\u7d22" in tokens


def test_tokenize_text_uses_bigrams_for_multi_char_cjk_segments() -> None:
    tokens = tokenize_text("\u4e2d\u6587\u68c0\u7d22")

    assert "\u4e2d" not in tokens
    assert "\u6587" not in tokens
    assert "\u4e2d\u6587" in tokens
    assert "\u6587\u68c0" in tokens
    assert "\u68c0\u7d22" in tokens
    assert "\u4e2d\u6587\u68c0\u7d22" in tokens


def test_query_rewriter_generates_keyword_variants() -> None:
    query = "\u8bf7\u95ee\u6df7\u5408\u68c0\u7d22\u600e\u4e48\u5de5\u4f5c"
    rewrites = RuleBasedQueryRewriter().rewrite(query)

    assert rewrites[0] == query
    assert any("\u6df7\u5408" in item for item in rewrites[1:])


def test_retrieval_pipeline_applies_metadata_filters_and_graph_expansion() -> None:
    collection_id = "collection-1"
    document = SourceDocument(
        id="doc-1",
        collection_id=collection_id,
        title="\u963f\u91cc\u5df4\u5df4\u8d22\u62a5",
        source_uri="memory://doc-1",
        source_type="text",
        checksum="checksum-1",
        published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        metadata={"region": "cn"},
    )
    chunks = [
        Chunk(id="chunk-0", document_id=document.id, chunk_index=0, text="\u963f\u91cc\u5df4\u5df4\u7b2c\u4e00\u5b63\u5ea6\u6536\u5165\u589e\u957f", token_count=10),
        Chunk(id="chunk-1", document_id=document.id, chunk_index=1, text="\u963f\u91cc\u5df4\u5df4\u73b0\u91d1\u6d41\u6539\u5584", token_count=10),
        Chunk(id="chunk-2", document_id=document.id, chunk_index=2, text="\u963f\u91cc\u5df4\u5df4\u4e91\u4e1a\u52a1\u6062\u590d\u589e\u957f", token_count=10),
    ]
    seed = EvidencePack(
        chunk_id="chunk-1",
        document_id=document.id,
        snippet=chunks[1].text,
        title=document.title,
        source=document.source_uri,
        score=0.8,
        token_estimate=10,
        metadata={
            "chunk_index": 1,
            "document_metadata": {"region": "cn"},
            "chunk_metadata": {},
            "source_type": "text",
            "published_at": document.published_at.isoformat(),
            "ingested_at": document.ingested_at.isoformat(),
            "retrieval": "dense",
        },
    )
    pipeline = RetrievalPipeline(
        retrievers={"dense": FakeRetriever([seed]), "bm25": FakeRetriever([seed]), "hybrid": FakeRetriever([seed])},
        reranker=FakeReranker(),
        store=FakeStore([document], chunks),
    )

    result = pipeline.run(
        query="\u963f\u91cc\u5df4\u5df4 \u8d22\u62a5",
        collection_id=collection_id,
        strategy="dense",
        top_k=3,
        rerank=False,
        options=RetrievalOptions(
            query_rewrite=True,
            entity_aware=True,
            metadata_filters=MetadataFilters(source_types=["text"], document_metadata={"region": "cn"}),
            graph_expansion=GraphExpansionConfig(enabled=True, hops=1, max_neighbors=2),
            freshness=FreshnessConfig(enabled=True, weight=0.1, half_life_days=365),
        ),
    )

    assert len(result.candidates) >= 2
    assert result.rewritten_queries
    assert all(item.metadata.get("source_type") == "text" for item in result.results)


def test_context_optimizer_extractive_is_query_aware() -> None:
    optimizer = ContextOptimizer()
    budget = TokenBudget(total=80, reserve=0, per_evidence=32)
    evidence = EvidencePack(
        chunk_id="chunk-1",
        document_id="doc-1",
        snippet=(
            "\u516c\u53f8\u4ecb\u7ecd\u90e8\u5206\uff0c\u4e3b\u8981\u8bf4\u660e\u5386\u53f2\u80cc\u666f\u3002 "
            "\u963f\u91cc\u5df4\u5df4\u4e91\u4e1a\u52a1\u6062\u590d\u589e\u957f\uff0c\u5b63\u5ea6\u6536\u5165\u540c\u6bd4\u63d0\u5347\u3002 "
            "\u9644\u5f55\u90e8\u5206\uff0c\u5305\u542b\u65e0\u5173\u8bf4\u660e\u3002"
        ),
        title="\u8d22\u62a5",
        source="memory://doc-1",
        score=1.0,
        token_estimate=40,
    )

    result = optimizer.optimize(
        [evidence],
        budget,
        merge_adjacent=False,
        compression_mode="extractive",
        query="\u963f\u91cc\u5df4\u5df4\u4e91\u4e1a\u52a1",
    )

    assert len(result.selected) == 1
    assert "\u963f\u91cc\u5df4\u5df4\u4e91\u4e1a\u52a1\u6062\u590d\u589e\u957f" in result.selected[0].snippet
