from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
import sys

from app.context import ContextOptimizer
from app.core.models import RetrievalOptions, TokenBudget
from app.evaluation import ExperimentArtifactStore, ExperimentRunner, OfflineEvaluationRunner
from app.retrieval import BM25Retriever, CrossEncoderReranker, DenseRetriever, HybridRetriever

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_mini_eval_python_venv_zh import build_dataset, load_spec, run_report

DEFAULT_SPEC_PATHS = [
    Path("data/evaluation/mini-eval-python-venv-zh.yaml"),
    Path("data/evaluation/semantic-eval-python-design-faq-zh.yaml"),
]
DEFAULT_REPORT_PATH = Path("data/artifacts/real-eval-suite-report.json")


def run_rrf_ablation(spec: dict, dataset, runtime_meta: dict, *, rrf_k_values: list[int]) -> dict:
    store = runtime_meta["store"]
    registry = runtime_meta["registry"]
    top_k = int(spec.get("evaluation", {}).get("top_k", 5))
    rows = []

    for rrf_k in rrf_k_values:
        dense = DenseRetriever(registry, store)
        bm25 = BM25Retriever(registry, store)
        hybrid = HybridRetriever(dense, bm25, rrf_k=rrf_k)
        runner = OfflineEvaluationRunner(
            ExperimentRunner(
                dense_retriever=dense,
                bm25_retriever=bm25,
                hybrid_retriever=hybrid,
                reranker=CrossEncoderReranker(),
                context_optimizer=ContextOptimizer(),
                store=store,
                artifact_store=ExperimentArtifactStore(Path("data/artifacts")),
            )
        )
        result = runner.run_dataset(
            dataset,
            strategies=["hybrid"],
            top_k=top_k,
            rerank=False,
            budget=TokenBudget(),
            options=RetrievalOptions(query_rewrite=False),
        )
        rows.append(
            {
                "rrf_k": rrf_k,
                "summary": result["summary"][0],
            }
        )

    best_by_mrr = max(rows, key=lambda row: row["summary"].get("avg_mrr") or float("-inf"))
    return {
        "slice": spec.get("slice"),
        "title": spec.get("title"),
        "collection_id": dataset.collection_id,
        "best_by_mrr": best_by_mrr,
        "rows": rows,
    }


def summarize_cases(report: dict) -> dict[str, list[dict]]:
    diagnostics: dict[str, list[dict]] = {}
    case_meta = report.get("cases", [])

    for mode, mode_result in report.get("results", {}).items():
        items: list[dict] = []
        for meta, case_result in zip(case_meta, mode_result.get("cases", []), strict=False):
            winners = pick_winners(case_result.get("strategies", []))
            items.append(
                {
                    "id": meta.get("id"),
                    "slice": meta.get("slice"),
                    "query_type": meta.get("query_type"),
                    "difficulty": meta.get("difficulty"),
                    "expected_winner": meta.get("expected_winner"),
                    "winner": winners,
                    "winner_matches_expectation": meta.get("expected_winner") in winners if meta.get("expected_winner") else None,
                }
            )
        diagnostics[mode] = items

    return diagnostics


def pick_winners(strategies: list[dict]) -> list[str]:
    if not strategies:
        return []

    def score_key(row: dict) -> tuple[float, float, float]:
        metrics = row.get("metrics", {})
        return (
            float(metrics.get("recall_at_k") or 0.0),
            float(metrics.get("mrr") or 0.0),
            float(metrics.get("ndcg_at_k") or 0.0),
        )

    best_score = max(score_key(row) for row in strategies)
    return [row["strategy"] for row in strategies if score_key(row) == best_score]


def aggregate_slice_summary(spec_reports: list[dict]) -> dict[str, dict[str, list[dict]]]:
    buckets: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for item in spec_reports:
        slice_name = item["report"].get("slice") or "unspecified"
        for mode, mode_result in item["report"].get("results", {}).items():
            for case_result in mode_result.get("cases", []):
                for strategy_result in case_result.get("strategies", []):
                    metrics = strategy_result.get("metrics", {})
                    prefix = buckets[mode][slice_name]
                    strategy = strategy_result["strategy"]
                    prefix[f"{strategy}:recall_at_k"].append(float(metrics.get("recall_at_k") or 0.0))
                    prefix[f"{strategy}:mrr"].append(float(metrics.get("mrr") or 0.0))
                    prefix[f"{strategy}:ndcg_at_k"].append(float(metrics.get("ndcg_at_k") or 0.0))

    output: dict[str, dict[str, list[dict]]] = {}
    for mode, slice_map in buckets.items():
        output[mode] = {}
        for slice_name, values in slice_map.items():
            rows = []
            for strategy in ("dense", "bm25", "hybrid"):
                rows.append(
                    {
                        "strategy": strategy,
                        "avg_recall_at_k": average(values.get(f"{strategy}:recall_at_k", [])),
                        "avg_mrr": average(values.get(f"{strategy}:mrr", [])),
                        "avg_ndcg_at_k": average(values.get(f"{strategy}:ndcg_at_k", [])),
                    }
                )
            output[mode][slice_name] = rows
    return output


def average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the real evaluation suite over multiple Chinese retrieval slices.")
    parser.add_argument("--spec-paths", nargs="+", default=[str(path) for path in DEFAULT_SPEC_PATHS])
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--rrf-k-values", nargs="*", type=int, default=[10, 20, 40, 60, 100])
    args = parser.parse_args()

    spec_reports = []
    rrf_reports = []

    for spec_path in args.spec_paths:
        spec = load_spec(spec_path)
        dataset, runtime_meta = build_dataset(spec)
        try:
            report = run_report(spec, dataset, runtime_meta, dispose_store=False)
            spec_reports.append(
                {
                    "spec_path": str(spec_path),
                    "report": report,
                    "case_diagnostics": summarize_cases(report),
                }
            )
            if args.rrf_k_values:
                rrf_reports.append(run_rrf_ablation(spec, dataset, runtime_meta, rrf_k_values=list(args.rrf_k_values)))
        finally:
            runtime_meta["store"].engine.dispose()

    suite_report = {
        "specs": spec_reports,
        "slice_summary": aggregate_slice_summary(spec_reports),
        "rrf_ablation": rrf_reports,
    }

    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(suite_report, ensure_ascii=False, indent=2), encoding="utf-8")

    console_summary = {
        "slice_summary": suite_report["slice_summary"],
        "rrf_best_by_spec": [
            {
                "slice": row["slice"],
                "title": row["title"],
                "best_rrf_k": row["best_by_mrr"]["rrf_k"],
                "best_hybrid_mrr": row["best_by_mrr"]["summary"].get("avg_mrr"),
            }
            for row in rrf_reports
        ],
    }
    print(json.dumps(console_summary, ensure_ascii=False, indent=2))
    print(f"Saved suite report to {report_path}")


if __name__ == "__main__":
    main()
