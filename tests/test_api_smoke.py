from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from fastapi.testclient import TestClient

from app.api.app import create_app
from app.api.routers import routes
from app.core.models import Collection, EvidencePack, IngestionResult, SourceDocument


class FakeStore:
    def __init__(self) -> None:
        self.collections: dict[str, Collection] = {}
        self.logged_runs: list[dict] = []

    def get_collection(self, collection_id: str):
        return self.collections.get(collection_id)

    def list_collections(self):
        return list(self.collections.values())

    def upsert_collection(self, collection: Collection):
        self.collections[collection.id] = collection

    def log_retrieval_run(self, item):
        self.logged_runs.append(item.model_dump())


class FakeIngestionService:
    def ingest_text(self, **kwargs):
        document = SourceDocument(
            collection_id=kwargs["collection_id"],
            title=kwargs["title"],
            source_uri=kwargs["source_uri"],
            source_type=kwargs["source_type"],
            checksum="fake-checksum",
            metadata=kwargs.get("metadata", {}),
        )
        return IngestionResult(document=document, chunks=[], text="", was_duplicate=False)


class FakeIndexRegistry:
    def build_collection_indexes(self, collection_id: str):
        return {
            "collection_id": collection_id,
            "chunk_count": 3,
            "dense_indexed": 3,
            "lexical_indexed": 3,
        }


class FakeRetriever:
    def __init__(self, label: str) -> None:
        self.label = label

    def retrieve(self, query: str, collection_id: str, top_k: int = 10, **kwargs):
        return [
            EvidencePack(
                chunk_id=f"{self.label}-{idx}",
                document_id=f"doc-{idx}",
                snippet=f"{self.label} snippet {idx} for {query}",
                title=f"{self.label} title {idx}",
                source=f"https://example.com/{self.label}/{idx}",
                score=1.0 / idx,
                token_estimate=50,
                metadata={"retrieval": self.label},
            )
            for idx in range(1, top_k + 1)
        ]


class FakeReranker:
    def rerank(self, query: str, candidates, top_k: int | None = None, **kwargs):
        reranked = [
            item.model_copy(update={"rerank_score": float(len(candidates) - idx)})
            for idx, item in enumerate(candidates)
        ]
        reranked.sort(key=lambda item: item.rerank_score or 0.0, reverse=True)
        return reranked[:top_k] if top_k is not None else reranked


class FakeRetrievalPipeline:
    def run(self, *, query: str, collection_id: str, strategy: str, top_k: int, candidate_k: int | None = None, rerank: bool = False, options=None):
        retriever = FakeRetriever(strategy)
        candidates = retriever.retrieve(query, collection_id, top_k=candidate_k or top_k)
        if rerank:
            results = FakeReranker().rerank(query, candidates, top_k=top_k)
        else:
            results = candidates[:top_k]

        class Result:
            def __init__(self):
                self.query = query
                self.rewritten_queries = [query] if not getattr(options, "query_rewrite", False) else [query, f"{query} rewritten"]
                self.candidates = candidates
                self.results = results
                self.reranked = rerank
                self.trace_steps = [{"step": "retrieve", "count": len(candidates)}]
                self.diagnostics = {"graph_added": 0, "filtered_out": 0, "entity_matches": 0, "freshness_applied": 0}

        return Result()


class FakeContextOptimizer:
    def optimize(self, evidence, budget, *, merge_adjacent=True, compression_mode="none"):
        class Result:
            def __init__(self, selected):
                self.selected = selected[:2]
                self.dropped = [{"chunk_id": item.chunk_id, "reason": "budget_exceeded"} for item in selected[2:]]
                self.token_estimate = sum(item.token_estimate for item in self.selected)
                self.original_token_estimate = sum(item.token_estimate for item in selected)
                self.token_savings = self.original_token_estimate - self.token_estimate
                self.available_budget = budget.available
                self.merged_count = 1 if merge_adjacent else 0
                self.compression_mode = compression_mode

        return Result(evidence)


class FakeContextPacker:
    def pack(self, evidence, profile: str = "markdown"):
        return "\n".join(item.snippet for item in evidence)


class FakeExperimentRunner:
    def run(self, **kwargs):
        strategies = kwargs["strategies"]
        compression_mode = kwargs.get("compression_mode", "none")
        merge_adjacent = kwargs.get("merge_adjacent", True)
        assembled_token_estimate = 80 if compression_mode == "extractive" else 100
        original_token_estimate = 120
        token_savings = original_token_estimate - assembled_token_estimate
        result = {
            "query": kwargs["query"],
            "collection_id": kwargs["collection_id"],
            "strategies": [
                {
                    "strategy": strategy,
                    "candidate_count": 3,
                    "result_count": 2,
                    "selected_count": 2,
                    "latency_ms": 1,
                    "token_estimate": 100,
                    "assembled_token_estimate": assembled_token_estimate,
                    "original_token_estimate": original_token_estimate,
                    "token_savings": token_savings,
                    "token_per_evidence": 50.0,
                    "merged_count": 1 if merge_adjacent else 0,
                    "compression_mode": compression_mode,
                    "chunk_ids": [f"{strategy}-1", f"{strategy}-2"],
                    "result_chunk_ids": [f"{strategy}-1", f"{strategy}-2", f"{strategy}-3"],
                    "metrics": {"recall_at_k": None, "mrr": None},
                    "reranked": kwargs["rerank"],
                    "dropped_count": 0,
                }
                for strategy in strategies
            ],
            "overlap": {"dense__bm25": 0.5} if len(strategies) > 1 else {},
        }
        if kwargs.get("save_artifact"):
            result["artifact_id"] = "artifact-demo"
            result["artifact_path"] = "D:/deer-rag/data/experiments/artifact-demo.json"
        return result


class FakeExperimentArtifactStore:
    def list(self):
        return [
            {
                "artifact_id": "artifact-demo",
                "artifact_path": "D:/deer-rag/data/experiments/artifact-demo.json",
                "size_bytes": 256,
            },
            {
                "artifact_id": "artifact-alt",
                "artifact_path": "D:/deer-rag/data/experiments/artifact-alt.json",
                "size_bytes": 240,
            }
        ]

    def get(self, artifact_id: str):
        if artifact_id == "artifact-demo":
            return {
                "query": "artifact query",
                "collection_id": "collection-demo",
                "strategies": [
                    {
                        "strategy": "dense",
                        "latency_ms": 3,
                        "token_estimate": 120,
                        "assembled_token_estimate": 80,
                        "original_token_estimate": 140,
                        "token_savings": 60,
                        "token_per_evidence": 60.0,
                        "selected_count": 2,
                        "merged_count": 1,
                        "compression_mode": "extractive",
                        "metrics": {"recall_at_k": 0.5, "mrr": 0.5},
                    }
                ],
                "overlap": {},
                "artifact_id": "artifact-demo",
                "artifact_path": "D:/deer-rag/data/experiments/artifact-demo.json",
            }
        if artifact_id == "artifact-alt":
            return {
                "query": "artifact query",
                "collection_id": "collection-demo",
                "strategies": [
                    {
                        "strategy": "hybrid",
                        "latency_ms": 5,
                        "token_estimate": 150,
                        "assembled_token_estimate": 90,
                        "original_token_estimate": 180,
                        "token_savings": 90,
                        "token_per_evidence": 75.0,
                        "selected_count": 2,
                        "merged_count": 0,
                        "compression_mode": "none",
                        "metrics": {"recall_at_k": 1.0, "mrr": 1.0},
                    }
                ],
                "overlap": {"dense__hybrid": 0.5},
                "artifact_id": "artifact-alt",
                "artifact_path": "D:/deer-rag/data/experiments/artifact-alt.json",
            }
        else:
            raise FileNotFoundError(f"Experiment artifact not found: {artifact_id}")


class FakeChunkSizeCompareRunner:
    def run(self, **kwargs):
        return {
            "collection_id": kwargs["collection_id"],
            "query": kwargs["query"],
            "variants": [
                {
                    "chunk_size": size,
                    "overlap": kwargs["overlap"],
                    "chunk_count": 4,
                    "avg_chunk_tokens": float(size) / 2.0,
                    "experiment": {
                        "query": kwargs["query"],
                        "collection_id": kwargs["collection_id"],
                        "strategies": [
                            {
                                "strategy": "dense",
                                "reranked": kwargs["rerank"],
                                "candidate_count": 3,
                                "result_count": 2,
                                "selected_count": 2,
                                "dropped_count": 0,
                                "latency_ms": 1,
                                "token_estimate": 100,
                                "assembled_token_estimate": 80,
                                "original_token_estimate": 120,
                                "token_savings": 40,
                                "token_per_evidence": 50.0,
                                "merged_count": 1,
                                "compression_mode": kwargs["compression_mode"],
                                "chunk_ids": ["dense-1", "dense-2"],
                                "result_chunk_ids": ["dense-1", "dense-2", "dense-3"],
                                "metrics": {"recall_at_k": None, "mrr": None},
                            }
                        ],
                        "overlap": {},
                    },
                }
                for size in kwargs["chunk_sizes"]
            ],
        }


class FakeOfflineEvaluationRunner:
    def run_dataset(self, dataset, **kwargs):
        return {
            "collection_id": dataset.collection_id,
            "case_count": len(dataset.cases),
            "summary": [
                {
                    "strategy": "dense",
                    "avg_latency_ms": 1.0,
                    "avg_token_estimate": 80.0,
                    "avg_recall_at_k": 0.5,
                    "avg_mrr": 0.5,
                    "avg_ndcg_at_k": 0.5,
                }
            ],
            "cases": [
                {
                    "case_index": 0,
                    "query": dataset.cases[0].query if dataset.cases else "query",
                    "gold_chunk_ids": dataset.cases[0].gold_chunk_ids if dataset.cases else [],
                    "strategies": [],
                }
            ],
        }


class FakeEmbeddingBenchmarkRunner:
    def run_dataset(self, dataset, **kwargs):
        return {
            "collection_id": dataset.collection_id,
            "case_count": len(dataset.cases),
            "hybrid_rrf_k": kwargs.get("hybrid_rrf_k") or 60,
            "models": [
                {
                    "model_name": model_name,
                    "summary": [
                        {
                            "strategy": strategy,
                            "avg_latency_ms": 1.0,
                            "avg_token_estimate": 80.0,
                            "avg_recall_at_k": 0.5,
                            "avg_mrr": 0.5,
                            "avg_ndcg_at_k": 0.5,
                        }
                        for strategy in kwargs["strategies"]
                    ],
                }
                for model_name in kwargs["embedding_models"]
            ],
        }


class FakeRerankerBenchmarkRunner:
    def run_dataset(self, dataset, **kwargs):
        return {
            "collection_id": dataset.collection_id,
            "case_count": len(dataset.cases),
            "models": [
                {
                    "model_name": model_name,
                    "summary": [
                        {
                            "strategy": kwargs["strategy"],
                            "avg_latency_ms": 1.0,
                            "avg_token_estimate": 70.0,
                            "avg_recall_at_k": 0.6,
                            "avg_mrr": 0.6,
                            "avg_ndcg_at_k": 0.6,
                        }
                    ],
                }
                for model_name in kwargs["reranker_models"]
            ],
        }


def make_cached(value):
    @lru_cache(maxsize=1)
    def _factory():
        return value

    return _factory


def build_client():
    fake_store = FakeStore()

    routes.get_store = make_cached(fake_store)
    routes.get_ingestion_service = make_cached(FakeIngestionService())
    routes.get_index_registry = make_cached(FakeIndexRegistry())
    routes.get_dense_retriever = make_cached(FakeRetriever("dense"))
    routes.get_bm25_retriever = make_cached(FakeRetriever("bm25"))
    routes.get_hybrid_retriever = make_cached(FakeRetriever("hybrid"))
    routes.get_reranker = make_cached(FakeReranker())
    routes.get_retrieval_pipeline = make_cached(FakeRetrievalPipeline())
    routes.get_context_optimizer = make_cached(FakeContextOptimizer())
    routes.get_context_packer = make_cached(FakeContextPacker())
    routes.get_experiment_artifact_store = make_cached(FakeExperimentArtifactStore())
    routes.get_experiment_runner = make_cached(FakeExperimentRunner())
    routes.get_chunk_size_compare_runner = make_cached(FakeChunkSizeCompareRunner())
    routes.get_offline_evaluation_runner = make_cached(FakeOfflineEvaluationRunner())
    routes.get_embedding_benchmark_runner = make_cached(FakeEmbeddingBenchmarkRunner())
    routes.get_reranker_benchmark_runner = make_cached(FakeRerankerBenchmarkRunner())

    app = create_app()
    return TestClient(app), fake_store


def test_health():
    client, _ = build_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_collection_create_and_list():
    client, _ = build_client()

    created = client.post("/collections", json={"name": "Demo Collection"})
    assert created.status_code == 200
    collection_id = created.json()["id"]

    listed = client.get("/collections")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == collection_id


def test_phase1_and_phase2_smoke_flow():
    client, _ = build_client()
    created = client.post("/collections", json={"name": "Demo Collection"})
    collection_id = created.json()["id"]

    ingest = client.post(
        "/ingest/text",
        json={
            "collection_id": collection_id,
            "title": "Doc 1",
            "text": "This is a test document.",
            "source_uri": "memory://doc-1",
            "source_type": "text",
        },
    )
    assert ingest.status_code == 200
    assert ingest.json()["result"]["chunk_count"] == 0

    build = client.post("/indexes/build", json={"collection_id": collection_id})
    assert build.status_code == 200
    assert build.json()["dense_indexed"] == 3

    retrieve = client.post(
        "/retrieve",
        json={
            "query": "test query",
            "collection_id": collection_id,
            "top_k": 2,
            "strategy": "hybrid",
            "rerank": True,
        },
    )
    assert retrieve.status_code == 200
    assert retrieve.json()["metrics"]["result_count"] == 2

    assemble = client.post(
        "/context/assemble",
        json={
            "evidence": retrieve.json()["results"],
            "budget": {"total": 500, "reserve": 100, "per_evidence": 100},
            "profile": "agent",
            "merge_adjacent": True,
            "compression_mode": "extractive",
        },
    )
    assert assemble.status_code == 200
    assert assemble.json()["metrics"]["selected_count"] == 2
    assert assemble.json()["metrics"]["compression_mode"] == "extractive"

    experiment = client.post(
        "/experiments/run",
        json={
            "query": "test query",
            "collection_id": collection_id,
            "strategies": ["dense", "bm25", "hybrid"],
            "top_k": 2,
            "rerank": False,
            "merge_adjacent": True,
            "compression_mode": "extractive",
        },
    )
    assert experiment.status_code == 200
    assert len(experiment.json()["strategies"]) == 3
    assert experiment.json()["strategies"][0]["compression_mode"] == "extractive"

    efficiency = client.post(
        "/experiments/context-efficiency",
        json={
            "query": "test query",
            "collection_id": collection_id,
            "strategies": ["dense", "hybrid"],
            "top_k": 2,
            "baseline_merge_adjacent": False,
            "baseline_compression_mode": "none",
            "optimized_merge_adjacent": True,
            "optimized_compression_mode": "extractive",
        },
    )
    assert efficiency.status_code == 200
    efficiency_payload = efficiency.json()
    assert efficiency_payload["baseline"]["strategies"][0]["compression_mode"] == "none"
    assert efficiency_payload["optimized"]["strategies"][0]["compression_mode"] == "extractive"
    assert efficiency_payload["deltas"][0]["token_savings_delta"] > 0

    chunk_compare = client.post(
        "/experiments/chunk-size",
        json={
            "collection_id": collection_id,
            "query": "test query",
            "chunk_sizes": [128, 256],
            "overlap": 32,
            "strategies": ["dense"],
            "top_k": 2,
            "compression_mode": "extractive",
        },
    )
    assert chunk_compare.status_code == 200
    assert len(chunk_compare.json()["variants"]) == 2


def test_experiment_run_config_and_artifact(tmp_path: Path):
    client, _ = build_client()
    created = client.post("/collections", json={"name": "Experiment Collection"})
    collection_id = created.json()["id"]

    experiments_dir = Path("D:/deer-rag/data/experiments")
    experiments_dir.mkdir(parents=True, exist_ok=True)
    config_path = experiments_dir / "smoke-experiment-runtime.yaml"
    config_path.write_text(
        "\n".join(
            [
                'query: "artifact query"',
                f'collection_id: "{collection_id}"',
                "strategies:",
                '  - "dense"',
                '  - "hybrid"',
                "top_k: 3",
                "rerank: true",
                "save_artifact: true",
                'artifact_name: "smoke-run"',
            ]
        ),
        encoding="utf-8",
    )

    response = client.post(
        "/experiments/run-config",
        json={"config_path": str(config_path)},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["strategies"]) == 2
    assert payload["artifact_id"] == "artifact-demo"
    assert payload["artifact_path"].endswith("artifact-demo.json")

    listed = client.get("/experiments/artifacts")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["artifact_id"] == "artifact-demo"

    fetched = client.get("/experiments/artifacts/artifact-demo")
    assert fetched.status_code == 200
    assert fetched.json()["artifact_id"] == "artifact-demo"

    compared = client.post(
        "/experiments/compare",
        json={"artifact_ids": ["artifact-demo", "artifact-alt"]},
    )
    assert compared.status_code == 200
    compare_payload = compared.json()
    assert len(compare_payload["items"]) == 2
    assert compare_payload["items"][0]["artifact_id"] == "artifact-demo"

    summary = client.post(
        "/experiments/compare-summary",
        json={"artifact_ids": ["artifact-demo", "artifact-alt"]},
    )
    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload["fastest"][0]["artifact_id"] == "artifact-demo"
    assert summary_payload["most_token_efficient"][0]["artifact_id"] == "artifact-demo"

    evaluation_dir = Path("D:/deer-rag/data/evaluation")
    evaluation_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = evaluation_dir / "smoke-dataset-runtime.yaml"
    dataset_path.write_text(
        "\n".join(
            [
                f'collection_id: "{collection_id}"',
                "cases:",
                '  - query: "artifact query"',
                "    gold_chunk_ids:",
                '      - "dense-1"',
            ]
        ),
        encoding="utf-8",
    )

    evaluation = client.post(
        "/evaluation/run-dataset",
        json={"dataset_path": str(dataset_path), "strategies": ["dense"], "top_k": 2},
    )
    assert evaluation.status_code == 200
    assert evaluation.json()["case_count"] == 1

    embedding_benchmark = client.post(
        "/experiments/benchmark/embeddings",
        json={
            "dataset_path": str(dataset_path),
            "embedding_models": ["model-a", "model-b"],
            "strategies": ["dense"],
            "top_k": 2,
        },
    )
    assert embedding_benchmark.status_code == 200
    assert len(embedding_benchmark.json()["models"]) == 2

    reranker_benchmark = client.post(
        "/experiments/benchmark/rerankers",
        json={
            "dataset_path": str(dataset_path),
            "reranker_models": ["reranker-a", "reranker-b"],
            "strategy": "hybrid",
            "top_k": 2,
        },
    )
    assert reranker_benchmark.status_code == 200
    assert len(reranker_benchmark.json()["models"]) == 2
