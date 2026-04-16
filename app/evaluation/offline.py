from __future__ import annotations

from collections import defaultdict

from app.core.models import TokenBudget
from app.evaluation.dataset import EvaluationDataset
from app.evaluation.metrics import ndcg_at_k
from app.evaluation.runner import ExperimentRunner


class OfflineEvaluationRunner:
    def __init__(self, experiment_runner: ExperimentRunner) -> None:
        self.experiment_runner = experiment_runner

    def run_dataset(
        self,
        dataset: EvaluationDataset,
        *,
        strategies: list[str],
        top_k: int,
        candidate_k: int | None = None,
        rerank: bool = False,
        budget: TokenBudget | None = None,
        merge_adjacent: bool = True,
        compression_mode: str = "none",
    ) -> dict:
        case_results: list[dict] = []
        aggregates: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

        for index, case in enumerate(dataset.cases):
            run_result = self.experiment_runner.run(
                query=case.query,
                collection_id=dataset.collection_id,
                strategies=list(strategies),
                top_k=case.top_k or top_k,
                candidate_k=case.candidate_k if case.candidate_k is not None else candidate_k,
                rerank=case.rerank if case.rerank is not None else rerank,
                budget=budget,
                merge_adjacent=merge_adjacent,
                compression_mode=compression_mode,
                gold_chunk_ids=case.gold_chunk_ids,
            )

            strategy_runs = []
            for strategy_run in run_result["strategies"]:
                ndcg = ndcg_at_k(strategy_run.get("result_chunk_ids", []), case.gold_chunk_ids, case.top_k or top_k)
                strategy_runs.append(
                    {
                        **strategy_run,
                        "metrics": {
                            **strategy_run.get("metrics", {}),
                            "ndcg_at_k": ndcg,
                        },
                    }
                )
                strategy = strategy_run["strategy"]
                aggregates[strategy]["latency_ms"].append(float(strategy_run.get("latency_ms", 0)))
                aggregates[strategy]["token_estimate"].append(float(strategy_run.get("assembled_token_estimate", 0)))
                if strategy_run.get("metrics", {}).get("recall_at_k") is not None:
                    aggregates[strategy]["recall_at_k"].append(float(strategy_run["metrics"]["recall_at_k"]))
                if strategy_run.get("metrics", {}).get("mrr") is not None:
                    aggregates[strategy]["mrr"].append(float(strategy_run["metrics"]["mrr"]))
                if ndcg is not None:
                    aggregates[strategy]["ndcg_at_k"].append(float(ndcg))

            case_results.append(
                {
                    "case_index": index,
                    "query": case.query,
                    "gold_chunk_ids": list(case.gold_chunk_ids),
                    "strategies": strategy_runs,
                }
            )

        summary = []
        for strategy in strategies:
            metrics = aggregates.get(strategy, {})
            summary.append(
                {
                    "strategy": strategy,
                    "avg_latency_ms": _average(metrics.get("latency_ms", [])),
                    "avg_token_estimate": _average(metrics.get("token_estimate", [])),
                    "avg_recall_at_k": _average(metrics.get("recall_at_k", [])),
                    "avg_mrr": _average(metrics.get("mrr", [])),
                    "avg_ndcg_at_k": _average(metrics.get("ndcg_at_k", [])),
                }
            )

        return {
            "collection_id": dataset.collection_id,
            "case_count": len(dataset.cases),
            "summary": summary,
            "cases": case_results,
        }


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)
