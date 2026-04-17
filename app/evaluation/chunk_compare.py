from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from app.context import ContextOptimizer
from app.core.config import load_config
from app.core.models import Chunk, RetrievalOptions, SourceDocument, TokenBudget
from app.ingestion.chunkers import FixedChunker
from app.indexing import CollectionIndexRegistry
from app.retrieval import BM25Retriever, CrossEncoderReranker, DenseRetriever, HybridRetriever
from app.storage import SQLiteMetadataStore
from app.evaluation.artifacts import ExperimentArtifactStore
from app.evaluation.runner import ExperimentRunner


class ChunkSizeCompareRunner:
    def __init__(self, store: SQLiteMetadataStore, data_dir: str | Path) -> None:
        self.store = store
        self.data_dir = Path(data_dir)

    def run(
        self,
        *,
        collection_id: str,
        query: str,
        chunk_sizes: list[int],
        overlap: int = 120,
        strategies: list[str],
        top_k: int,
        candidate_k: int | None = None,
        rerank: bool = False,
        budget: TokenBudget | None = None,
        merge_adjacent: bool = True,
        compression_mode: str = "none",
        gold_chunk_ids: list[str] | None = None,
        options: RetrievalOptions | None = None,
    ) -> dict:
        documents = self.store.list_documents(collection_id)
        if not documents:
            raise ValueError("No source documents found for the collection")

        results: list[dict] = []
        for chunk_size in chunk_sizes:
            variant_chunks, variant_documents = self._build_variant_chunks(documents, chunk_size=chunk_size, overlap=overlap)
            with TemporaryDirectory(prefix="deer-rag-chunk-compare-") as temp_dir:
                temp_path = Path(temp_dir)
                temp_store = SQLiteMetadataStore(temp_path / "metadata.sqlite3")
                temp_store.init_db()
                for document in variant_documents:
                    temp_store.upsert_source_document(document)
                temp_store.upsert_chunks(variant_chunks)

                try:
                    registry = CollectionIndexRegistry(temp_store, base_dir=temp_path / "indexes")
                    registry.build_collection_indexes(collection_id)
                    dense = DenseRetriever(registry, temp_store)
                    bm25 = BM25Retriever(registry, temp_store)
                    hybrid = HybridRetriever(dense, bm25, rrf_k=load_config().retrieval.hybrid_rrf_k)
                    runner = ExperimentRunner(
                        dense_retriever=dense,
                        bm25_retriever=bm25,
                        hybrid_retriever=hybrid,
                        reranker=CrossEncoderReranker(),
                        context_optimizer=ContextOptimizer(),
                        store=temp_store,
                        artifact_store=ExperimentArtifactStore(temp_path / "artifacts"),
                    )
                    experiment = runner.run(
                        query=query,
                        collection_id=collection_id,
                        strategies=list(strategies),
                        top_k=top_k,
                        candidate_k=candidate_k,
                        rerank=rerank,
                        budget=budget,
                        merge_adjacent=merge_adjacent,
                        compression_mode=compression_mode,
                        gold_chunk_ids=gold_chunk_ids,
                        options=options,
                    )
                finally:
                    temp_store.engine.dispose()

            token_counts = [chunk.token_count for chunk in variant_chunks]
            results.append(
                {
                    "chunk_size": chunk_size,
                    "overlap": overlap,
                    "chunk_count": len(variant_chunks),
                    "avg_chunk_tokens": (sum(token_counts) / len(token_counts)) if token_counts else 0.0,
                    "experiment": experiment,
                }
            )

        return {
            "collection_id": collection_id,
            "query": query,
            "variants": results,
        }

    def _build_variant_chunks(
        self,
        documents: list[SourceDocument],
        *,
        chunk_size: int,
        overlap: int,
    ) -> tuple[list[Chunk], list[SourceDocument]]:
        chunker = FixedChunker(chunk_size=chunk_size, overlap=overlap)
        all_chunks: list[Chunk] = []
        cloned_documents: list[SourceDocument] = []

        for document in documents:
            if not document.raw_text_path:
                raise ValueError(f"Document {document.id} is missing raw_text_path")
            raw_text = Path(document.raw_text_path).read_text(encoding="utf-8")
            cloned_document = document.model_copy()
            cloned_documents.append(cloned_document)
            all_chunks.extend(chunker.chunk(cloned_document, raw_text))

        return all_chunks, cloned_documents
