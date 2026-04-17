from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.core.models import Chunk, SourceDocument, TokenBudget
from app.evaluation.benchmark import EmbeddingBenchmarkRunner
from app.evaluation.dataset import EvaluationCase, EvaluationDataset


class FakeStore:
    def __init__(self, documents: list[SourceDocument], chunks: list[Chunk]) -> None:
        self._documents = documents
        self._chunks = chunks

    def list_documents(self, collection_id: str) -> list[SourceDocument]:
        return [item for item in self._documents if item.collection_id == collection_id]

    def list_chunks(self, collection_id: str) -> list[Chunk]:
        document_ids = {item.id for item in self.list_documents(collection_id)}
        return [item for item in self._chunks if item.document_id in document_ids]


class FakeEngine:
    def __init__(self) -> None:
        self.dispose_count = 0

    def dispose(self) -> None:
        self.dispose_count += 1


class FakeTempStore(FakeStore):
    def __init__(self, documents: list[SourceDocument], chunks: list[Chunk]) -> None:
        super().__init__(documents, chunks)
        self.engine = FakeEngine()

    def upsert_source_document(self, item: SourceDocument) -> None:
        return None

    def upsert_chunks(self, items: list[Chunk]) -> None:
        return None


def test_embedding_benchmark_runner_disposes_temp_store_on_each_model(monkeypatch) -> None:
    import app.evaluation.benchmark as benchmark_module

    collection_id = "collection-1"
    document = SourceDocument(
        id="doc-1",
        collection_id=collection_id,
        title="Doc",
        source_uri="memory://doc-1",
        source_type="text",
        checksum="checksum-1",
    )
    chunk = Chunk(
        id="chunk-1",
        document_id=document.id,
        chunk_index=0,
        text="example chunk",
        token_count=4,
    )
    dataset = EvaluationDataset(
        collection_id=collection_id,
        cases=[EvaluationCase(query="example query", gold_chunk_ids=[chunk.id])],
    )

    temp_stores: list[FakeTempStore] = []

    def fake_clone_store(self, temp_dir: Path, documents, chunks):
        store = FakeTempStore(list(documents), list(chunks))
        temp_stores.append(store)
        return store

    class FakeRegistry:
        def __init__(self, store, base_dir):
            self.store = store
            self.base_dir = Path(base_dir)

        def paths_for(self, collection_id: str):
            base = self.base_dir / collection_id
            return SimpleNamespace(
                dense_index_path=base / "dense.faiss",
                dense_meta_path=base / "dense.meta.json",
                lexical_state_path=base / "bm25.json",
            )

    class FakeDenseIndex:
        def __init__(self, *args, **kwargs) -> None:
            return None

        def build(self, chunks: list[Chunk]) -> int:
            return len(chunks)

    class FakeLexicalIndex(FakeDenseIndex):
        pass

    class FakeRetriever:
        def __init__(self, *args, **kwargs) -> None:
            return None

    class FakeExperimentRunner:
        def __init__(self, *args, **kwargs) -> None:
            return None

    class FakeOfflineRunner:
        def __init__(self, experiment_runner) -> None:
            self.experiment_runner = experiment_runner

        def run_dataset(self, dataset, **kwargs):
            strategies = kwargs.get("strategies", [])
            return {
                "summary": [
                    {
                        "strategy": strategy,
                        "avg_recall_at_k": 1.0,
                        "avg_mrr": 1.0,
                        "avg_ndcg_at_k": 1.0,
                    }
                    for strategy in strategies
                ]
            }

    monkeypatch.setattr(EmbeddingBenchmarkRunner, "_clone_store", fake_clone_store)
    monkeypatch.setattr(benchmark_module, "CollectionIndexRegistry", FakeRegistry)
    monkeypatch.setattr(benchmark_module, "FaissDenseIndex", FakeDenseIndex)
    monkeypatch.setattr(benchmark_module, "BM25LexicalIndex", FakeLexicalIndex)
    monkeypatch.setattr(benchmark_module, "DenseRetriever", FakeRetriever)
    monkeypatch.setattr(benchmark_module, "BM25Retriever", FakeRetriever)
    monkeypatch.setattr(benchmark_module, "HybridRetriever", FakeRetriever)
    monkeypatch.setattr(benchmark_module, "CrossEncoderReranker", lambda *args, **kwargs: object())
    monkeypatch.setattr(benchmark_module, "ContextOptimizer", lambda *args, **kwargs: object())
    monkeypatch.setattr(benchmark_module, "ExperimentArtifactStore", lambda *args, **kwargs: object())
    monkeypatch.setattr(benchmark_module, "ExperimentRunner", FakeExperimentRunner)
    monkeypatch.setattr(benchmark_module, "OfflineEvaluationRunner", FakeOfflineRunner)

    runner = EmbeddingBenchmarkRunner(FakeStore([document], [chunk]))
    result = runner.run_dataset(
        dataset,
        embedding_models=["model-a", "model-b"],
        strategies=["dense"],
        top_k=5,
        budget=TokenBudget(),
    )

    assert len(result["models"]) == 2
    assert result["hybrid_rrf_k"] == 10
    assert len(temp_stores) == 2
    assert all(item.engine.dispose_count == 1 for item in temp_stores)
