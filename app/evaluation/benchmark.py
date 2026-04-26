from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from app.context import ContextOptimizer
from app.core.config import load_config
from app.core.models import RetrievalOptions, TokenBudget
from app.evaluation.artifacts import ExperimentArtifactStore
from app.evaluation.dataset import EvaluationDataset
from app.evaluation.offline import OfflineEvaluationRunner
from app.evaluation.runner import ExperimentRunner
from app.indexing.dense import FaissDenseIndex
from app.indexing.lexical import BM25LexicalIndex
from app.indexing.registry import CollectionIndexRegistry
from app.retrieval import BM25Retriever, CrossEncoderReranker, DenseRetriever, HybridRetriever
from app.storage import SQLiteMetadataStore


class EmbeddingBenchmarkRunner:
    def __init__(self, store: SQLiteMetadataStore) -> None:
        self.store = store

    def run_dataset(
        self,
        dataset: EvaluationDataset,
        *,
        embedding_models: list[str],
        strategies: list[str],
        top_k: int,
        candidate_k: int | None = None,
        rerank: bool = False,
        budget: TokenBudget | None = None,
        merge_adjacent: bool = True,
        compression_mode: str = "none",
        options: RetrievalOptions | None = None,
        hybrid_rrf_k: int | None = None,
    ) -> dict:
        collection_id = dataset.collection_id
        config = load_config()
        documents = self.store.list_documents(collection_id)
        chunks = self.store.list_chunks(collection_id)
        if not documents or not chunks:
            raise ValueError("Collection must contain documents and chunks before running embedding benchmarks")

        effective_rrf_k = hybrid_rrf_k or config.retrieval.hybrid_rrf_k
        models: list[dict] = []
        for model_name in embedding_models:
            with TemporaryDirectory(prefix="deer-rag-embedding-benchmark-") as temp_dir:
                temp_store = self._clone_store(Path(temp_dir), documents, chunks)
                try:
                    registry = CollectionIndexRegistry(temp_store, base_dir=Path(temp_dir) / "indexes")
                    paths = registry.paths_for(collection_id)
                    FaissDenseIndex(
                        index_path=paths.dense_index_path,
                        meta_path=paths.dense_meta_path,
                        model_name=model_name,
                    ).build(chunks)
                    BM25LexicalIndex(paths.lexical_state_path).build(chunks)

                    dense = DenseRetriever(registry, temp_store, model_name=model_name)
                    bm25 = BM25Retriever(registry, temp_store)
                    hybrid = HybridRetriever(dense, bm25, rrf_k=effective_rrf_k)
                    experiment_runner = ExperimentRunner(
                        dense_retriever=dense,
                        bm25_retriever=bm25,
                        hybrid_retriever=hybrid,
                        reranker=CrossEncoderReranker(model_name=config.models.reranker_model_name),
                        context_optimizer=ContextOptimizer(),
                        store=temp_store,
                        artifact_store=ExperimentArtifactStore(Path(temp_dir) / "artifacts"),
                    )
                    offline_runner = OfflineEvaluationRunner(experiment_runner)
                    result = offline_runner.run_dataset(
                        dataset,
                        strategies=strategies,
                        top_k=top_k,
                        candidate_k=candidate_k,
                        rerank=rerank,
                        budget=budget,
                        merge_adjacent=merge_adjacent,
                        compression_mode=compression_mode,
                        options=options,
                    )
                    models.append(
                        {
                "model_name": model_name,
                "hybrid_rrf_k": effective_rrf_k,
                "summary": result["summary"],
            }
                    )
                finally:
                    # SQLite files stay locked on Windows until the engine is disposed.
                    temp_store.engine.dispose()

        return {
            "collection_id": collection_id,
            "case_count": len(dataset.cases),
            "hybrid_rrf_k": effective_rrf_k,
            "models": models,
        }

    def _clone_store(self, temp_dir: Path, documents, chunks) -> SQLiteMetadataStore:
        temp_store = SQLiteMetadataStore(temp_dir / "metadata.sqlite3")
        temp_store.init_db()
        for document in documents:
            temp_store.upsert_source_document(document)
        temp_store.upsert_chunks(chunks)
        return temp_store


class RerankerBenchmarkRunner:
    def __init__(
        self,
        *,
        dense_retriever: DenseRetriever,
        bm25_retriever: BM25Retriever,
        hybrid_retriever: HybridRetriever,
        store: SQLiteMetadataStore,
    ) -> None:
        self.dense_retriever = dense_retriever
        self.bm25_retriever = bm25_retriever
        self.hybrid_retriever = hybrid_retriever
        self.store = store

    def run_dataset(
        self,
        dataset: EvaluationDataset,
        *,
        reranker_models: list[str],
        strategy: str,
        top_k: int,
        candidate_k: int | None = None,
        budget: TokenBudget | None = None,
        merge_adjacent: bool = True,
        compression_mode: str = "none",
        options: RetrievalOptions | None = None,
    ) -> dict:
        models: list[dict] = []
        for model_name in reranker_models:
            with TemporaryDirectory(prefix="deer-rag-reranker-benchmark-") as temp_dir:
                experiment_runner = ExperimentRunner(
                    dense_retriever=self.dense_retriever,
                    bm25_retriever=self.bm25_retriever,
                    hybrid_retriever=self.hybrid_retriever,
                    reranker=CrossEncoderReranker(model_name=model_name),
                    context_optimizer=ContextOptimizer(),
                    store=self.store,
                    artifact_store=ExperimentArtifactStore(Path(temp_dir) / "artifacts"),
                )
                offline_runner = OfflineEvaluationRunner(experiment_runner)
                result = offline_runner.run_dataset(
                    dataset,
                    strategies=[strategy],
                    top_k=top_k,
                    candidate_k=candidate_k,
                    rerank=True,
                    budget=budget,
                    merge_adjacent=merge_adjacent,
                    compression_mode=compression_mode,
                    options=options,
                )
                models.append(
                    {
                        "model_name": model_name,
                        "summary": result["summary"],
                    }
                )

        return {
            "collection_id": dataset.collection_id,
            "case_count": len(dataset.cases),
            "models": models,
        }
