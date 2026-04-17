from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen

import yaml

from app.context import ContextOptimizer
from app.core.config import load_config
from app.core.models import Collection, RetrievalOptions, TokenBudget
from app.evaluation import ExperimentArtifactStore, ExperimentRunner, OfflineEvaluationRunner
from app.evaluation.dataset import EvaluationCase, EvaluationDataset
from app.indexing import CollectionIndexRegistry
from app.ingestion import IngestionService
from app.ingestion.chunkers import FixedChunker
from app.ingestion.parsers.web import WebParser
from app.retrieval import BM25Retriever, CrossEncoderReranker, DenseRetriever, HybridRetriever
from app.storage import SQLiteMetadataStore

DEFAULT_SPEC_PATH = Path("data/evaluation/mini-eval-python-venv-zh.yaml")
DEFAULT_REPORT_PATH = Path("data/artifacts/mini-eval-python-venv-zh-report.json")


def load_spec(path: str | Path) -> dict:
    spec_path = Path(path)
    payload = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("Mini eval spec must be a YAML mapping.")
    return payload


def fetch_source_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="ignore")
    return WebParser().parse(html)


def build_dataset(spec: dict) -> tuple[EvaluationDataset, dict]:
    config = load_config()
    collection_id = spec["collection_id"]
    source = spec["source"]
    chunking = spec["chunking"]

    store = SQLiteMetadataStore(config.paths.metadata_db)
    store.init_db()
    registry = CollectionIndexRegistry(store=store, base_dir=config.paths.data_dir / "indexes")
    chunker = FixedChunker(
        chunk_size=int(chunking["chunk_size"]),
        overlap=int(chunking["overlap"]),
    )
    ingestion = IngestionService(
        store=store,
        chunker=chunker,
        raw_text_dir=config.paths.raw_dir,
    )

    collection = Collection(
        id=collection_id,
        name=spec.get("title", "Mini Eval"),
        description=spec.get("description", ""),
        domain="mini-eval",
        metadata={
            "source_url": source["url"],
            "source_version": source.get("version"),
            "chunk_size": int(chunking["chunk_size"]),
            "overlap": int(chunking["overlap"]),
        },
    )
    store.upsert_collection(collection)

    source_text = fetch_source_text(source["url"])
    ingestion.ingest_text(
        collection_id=collection_id,
        title=source["title"],
        text=source_text,
        source_uri=source["url"],
        source_type=source.get("source_type", "web"),
        metadata={
            "language": "zh-CN",
            "source_version": source.get("version"),
            "mini_eval": True,
        },
    )
    index_stats = registry.build_collection_indexes(collection_id)
    chunks = store.list_chunks(collection_id)
    cases = resolve_cases(spec.get("cases", []), chunks, default_slice=spec.get("slice"))

    dataset = EvaluationDataset(collection_id=collection_id, cases=cases["dataset_cases"])
    runtime_meta = {
        "collection_id": collection_id,
        "chunk_count": len(chunks),
        "index_stats": index_stats,
        "resolved_cases": cases["resolved_cases"],
        "store": store,
        "registry": registry,
    }
    return dataset, runtime_meta


def resolve_cases(raw_cases: list[dict], chunks: list, *, default_slice: str | None = None) -> dict:
    dataset_cases: list[EvaluationCase] = []
    resolved_cases: list[dict] = []

    for raw_case in raw_cases:
        gold_indexes = list(raw_case.get("gold_chunk_indexes", []))
        if not gold_indexes:
            raise ValueError(f"Case {raw_case.get('id', raw_case.get('query', '<unknown>'))} is missing gold_chunk_indexes.")

        gold_chunks = []
        gold_chunk_ids = []
        for index in gold_indexes:
            if index < 0 or index >= len(chunks):
                raise ValueError(f"Gold chunk index {index} is out of range for a collection with {len(chunks)} chunks.")
            chunk = chunks[index]
            gold_chunks.append(chunk)
            gold_chunk_ids.append(chunk.id)

        for marker in raw_case.get("gold_contains", []):
            if not any(marker in chunk.text for chunk in gold_chunks):
                raise ValueError(
                    f"Gold marker {marker!r} was not found in case {raw_case.get('id', raw_case.get('query', '<unknown>'))}."
                )

        dataset_cases.append(
            EvaluationCase(
                query=raw_case["query"],
                gold_chunk_ids=gold_chunk_ids,
            )
        )
        resolved_cases.append(
            {
                "id": raw_case.get("id"),
                "query": raw_case["query"],
                "slice": raw_case.get("slice", default_slice),
                "query_type": raw_case.get("query_type"),
                "expected_winner": raw_case.get("expected_winner"),
                "difficulty": raw_case.get("difficulty"),
                "gold_chunk_indexes": gold_indexes,
                "gold_chunk_ids": gold_chunk_ids,
                "gold_markers": list(raw_case.get("gold_contains", [])),
                "gold_preview": [chunk.text[:180] for chunk in gold_chunks],
            }
        )

    return {
        "dataset_cases": dataset_cases,
        "resolved_cases": resolved_cases,
    }


def build_runner(store: SQLiteMetadataStore, registry: CollectionIndexRegistry) -> tuple[OfflineEvaluationRunner, DenseRetriever, BM25Retriever]:
    dense_retriever = DenseRetriever(registry, store)
    bm25_retriever = BM25Retriever(registry, store)
    hybrid_retriever = HybridRetriever(dense_retriever, bm25_retriever, rrf_k=load_config().retrieval.hybrid_rrf_k)

    runner = OfflineEvaluationRunner(
        ExperimentRunner(
            dense_retriever=dense_retriever,
            bm25_retriever=bm25_retriever,
            hybrid_retriever=hybrid_retriever,
            reranker=CrossEncoderReranker(),
            context_optimizer=ContextOptimizer(),
            store=store,
            artifact_store=ExperimentArtifactStore(load_config().paths.experiments_dir),
        )
    )
    return runner, dense_retriever, bm25_retriever


def warm_retrievers(
    *,
    dense_retriever: DenseRetriever,
    bm25_retriever: BM25Retriever,
    collection_id: str,
    query: str,
) -> None:
    dense_retriever.retrieve(query, collection_id, top_k=1)
    bm25_retriever.retrieve(query, collection_id, top_k=1)


def run_report(spec: dict, dataset: EvaluationDataset, runtime_meta: dict, *, dispose_store: bool = True) -> dict:
    evaluation = spec.get("evaluation", {})
    top_k = int(evaluation.get("top_k", 5))
    strategies = list(evaluation.get("strategies", ["dense", "bm25", "hybrid"]))

    store: SQLiteMetadataStore = runtime_meta["store"]
    registry: CollectionIndexRegistry = runtime_meta["registry"]
    runner, dense_retriever, bm25_retriever = build_runner(store, registry)

    warm_retrievers(
        dense_retriever=dense_retriever,
        bm25_retriever=bm25_retriever,
        collection_id=dataset.collection_id,
        query=dataset.cases[0].query,
    )

    results = {}
    for query_rewrite in (False, True):
        key = "query_rewrite_on" if query_rewrite else "query_rewrite_off"
        results[key] = runner.run_dataset(
            dataset,
            strategies=strategies,
            top_k=top_k,
            rerank=False,
            budget=TokenBudget(),
            options=RetrievalOptions(query_rewrite=query_rewrite),
        )

    report = {
        "title": spec.get("title", "Mini Eval"),
        "description": spec.get("description", ""),
        "slice": spec.get("slice"),
        "source": spec.get("source", {}),
        "chunking": spec.get("chunking", {}),
        "evaluation": {
            "top_k": top_k,
            "strategies": strategies,
            "rerank": False,
        },
        "collection_id": dataset.collection_id,
        "chunk_count": runtime_meta["chunk_count"],
        "index_stats": runtime_meta["index_stats"],
        "cases": runtime_meta["resolved_cases"],
        "results": results,
    }
    if dispose_store:
        store.engine.dispose()
    return report


def print_summary(report: dict) -> None:
    print(
        json.dumps(
            {
                "collection_id": report["collection_id"],
                "chunk_count": report["chunk_count"],
                "results": {
                    key: value["summary"]
                    for key, value in report["results"].items()
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the real Chinese mini eval for the Python venv docs.")
    parser.add_argument("--spec-path", default=str(DEFAULT_SPEC_PATH))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    args = parser.parse_args()

    spec = load_spec(args.spec_path)
    dataset, runtime_meta = build_dataset(spec)
    report = run_report(spec, dataset, runtime_meta)

    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print_summary(report)
    print(f"Saved report to {report_path}")


if __name__ == "__main__":
    main()
