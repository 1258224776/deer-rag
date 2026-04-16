from __future__ import annotations

from functools import lru_cache

from app.context import ContextOptimizer, ContextPacker
from app.core.config import AppConfig, load_config
from app.evaluation import (
    ChunkSizeCompareRunner,
    ExperimentArtifactStore,
    ExperimentRunner,
    OfflineEvaluationRunner,
)
from app.indexing import CollectionIndexRegistry
from app.ingestion import IngestionService
from app.retrieval import BM25Retriever, CrossEncoderReranker, DenseRetriever, HybridRetriever
from app.storage import SQLiteMetadataStore


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return load_config()


@lru_cache(maxsize=1)
def get_store() -> SQLiteMetadataStore:
    config = get_config()
    store = SQLiteMetadataStore(config.paths.metadata_db)
    store.init_db()
    return store


@lru_cache(maxsize=1)
def get_index_registry() -> CollectionIndexRegistry:
    config = get_config()
    return CollectionIndexRegistry(get_store(), base_dir=config.paths.data_dir / "indexes")


@lru_cache(maxsize=1)
def get_ingestion_service() -> IngestionService:
    return IngestionService(store=get_store(), raw_text_dir=get_config().paths.raw_dir)


@lru_cache(maxsize=1)
def get_dense_retriever() -> DenseRetriever:
    return DenseRetriever(get_index_registry(), get_store())


@lru_cache(maxsize=1)
def get_bm25_retriever() -> BM25Retriever:
    return BM25Retriever(get_index_registry(), get_store())


@lru_cache(maxsize=1)
def get_hybrid_retriever() -> HybridRetriever:
    return HybridRetriever(get_dense_retriever(), get_bm25_retriever(), rrf_k=get_config().retrieval.hybrid_rrf_k)


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoderReranker:
    return CrossEncoderReranker()


@lru_cache(maxsize=1)
def get_context_optimizer() -> ContextOptimizer:
    return ContextOptimizer()


@lru_cache(maxsize=1)
def get_context_packer() -> ContextPacker:
    return ContextPacker()


@lru_cache(maxsize=1)
def get_experiment_artifact_store() -> ExperimentArtifactStore:
    config = get_config()
    return ExperimentArtifactStore(config.paths.experiments_dir)


@lru_cache(maxsize=1)
def get_experiment_runner() -> ExperimentRunner:
    return ExperimentRunner(
        dense_retriever=get_dense_retriever(),
        bm25_retriever=get_bm25_retriever(),
        hybrid_retriever=get_hybrid_retriever(),
        reranker=get_reranker(),
        context_optimizer=get_context_optimizer(),
        store=get_store(),
        artifact_store=get_experiment_artifact_store(),
    )


@lru_cache(maxsize=1)
def get_chunk_size_compare_runner() -> ChunkSizeCompareRunner:
    return ChunkSizeCompareRunner(store=get_store(), data_dir=get_config().paths.data_dir)


@lru_cache(maxsize=1)
def get_offline_evaluation_runner() -> OfflineEvaluationRunner:
    return OfflineEvaluationRunner(get_experiment_runner())
