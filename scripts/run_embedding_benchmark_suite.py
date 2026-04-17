from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.models import RetrievalOptions, TokenBudget
from app.evaluation import EmbeddingBenchmarkRunner
from scripts.run_mini_eval_python_venv_zh import build_dataset, load_spec

DEFAULT_SPEC_PATHS = [
    Path("data/evaluation/mini-eval-python-venv-zh.yaml"),
    Path("data/evaluation/semantic-eval-python-design-faq-zh.yaml"),
]
DEFAULT_EMBEDDING_MODELS = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "BAAI/bge-small-zh-v1.5",
    "BAAI/bge-m3",
]
DEFAULT_REPORT_PATH = Path("data/artifacts/embedding-benchmark-suite-report.json")


def summarize_models(rows: list[dict]) -> dict[str, dict[str, float | None]]:
    summary: dict[str, dict[str, float | None]] = {}
    for item in rows:
        strategy_rows = {row["strategy"]: row for row in item.get("summary", [])}
        summary[item["model_name"]] = {
            "dense_mrr": strategy_rows.get("dense", {}).get("avg_mrr"),
            "dense_recall_at_k": strategy_rows.get("dense", {}).get("avg_recall_at_k"),
            "hybrid_mrr": strategy_rows.get("hybrid", {}).get("avg_mrr"),
            "hybrid_recall_at_k": strategy_rows.get("hybrid", {}).get("avg_recall_at_k"),
        }
    return summary


def pick_best_model(rows: list[dict], *, strategy: str, metric: str) -> dict | None:
    best = None
    best_value = float("-inf")
    for item in rows:
        strategy_row = next((row for row in item.get("summary", []) if row["strategy"] == strategy), None)
        if strategy_row is None:
            continue
        value = strategy_row.get(metric)
        if value is None:
            continue
        if float(value) > best_value:
            best_value = float(value)
            best = {
                "model_name": item["model_name"],
                "strategy": strategy,
                metric: value,
            }
    return best


def main() -> None:
    parser = argparse.ArgumentParser(description="Run embedding benchmarks on the real Chinese evaluation slices.")
    parser.add_argument("--spec-paths", nargs="+", default=[str(path) for path in DEFAULT_SPEC_PATHS])
    parser.add_argument("--embedding-models", nargs="+", default=list(DEFAULT_EMBEDDING_MODELS))
    parser.add_argument("--hybrid-rrf-k", type=int, default=10)
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    args = parser.parse_args()

    suite_rows = []
    for spec_path in args.spec_paths:
        spec = load_spec(spec_path)
        dataset, runtime_meta = build_dataset(spec)
        try:
            benchmark = EmbeddingBenchmarkRunner(runtime_meta["store"]).run_dataset(
                dataset,
                embedding_models=list(args.embedding_models),
                strategies=["dense", "hybrid"],
                hybrid_rrf_k=args.hybrid_rrf_k,
                top_k=int(spec.get("evaluation", {}).get("top_k", 5)),
                rerank=False,
                budget=TokenBudget(),
                options=RetrievalOptions(query_rewrite=False),
            )
            suite_rows.append(
                {
                    "spec_path": str(spec_path),
                    "title": spec.get("title"),
                    "slice": spec.get("slice"),
                    "collection_id": benchmark["collection_id"],
                    "case_count": benchmark["case_count"],
                    "hybrid_rrf_k": benchmark["hybrid_rrf_k"],
                    "models": benchmark["models"],
                    "model_summary": summarize_models(benchmark["models"]),
                    "best_dense_mrr": pick_best_model(benchmark["models"], strategy="dense", metric="avg_mrr"),
                    "best_hybrid_mrr": pick_best_model(benchmark["models"], strategy="hybrid", metric="avg_mrr"),
                }
            )
        finally:
            runtime_meta["store"].engine.dispose()

    report = {
        "embedding_models": list(args.embedding_models),
        "hybrid_rrf_k": args.hybrid_rrf_k,
        "specs": suite_rows,
    }

    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    console_summary = {
        "hybrid_rrf_k": args.hybrid_rrf_k,
        "specs": [
            {
                "slice": row["slice"],
                "title": row["title"],
                "best_dense_mrr": row["best_dense_mrr"],
                "best_hybrid_mrr": row["best_hybrid_mrr"],
            }
            for row in suite_rows
        ],
    }
    print(json.dumps(console_summary, ensure_ascii=False, indent=2))
    print(f"Saved embedding benchmark report to {report_path}")


if __name__ == "__main__":
    main()
