from __future__ import annotations

from itertools import combinations
from time import perf_counter

from app.context import ContextOptimizer
from app.core.interfaces import BaseReranker, BaseRetriever
from app.core.models import RetrievalRunRecord, TokenBudget
from app.evaluation.artifacts import ExperimentArtifactStore
from app.evaluation.metrics import jaccard_overlap, mean_reciprocal_rank, recall_at_k
from app.storage import SQLiteMetadataStore


class ExperimentRunner:
    def __init__(
        self,
        *,
        dense_retriever: BaseRetriever,
        bm25_retriever: BaseRetriever,
        hybrid_retriever: BaseRetriever,
        reranker: BaseReranker,
        context_optimizer: ContextOptimizer,
        store: SQLiteMetadataStore,
        artifact_store: ExperimentArtifactStore,
    ) -> None:
        self.retrievers = {
            "dense": dense_retriever,
            "bm25": bm25_retriever,
            "hybrid": hybrid_retriever,
        }
        self.reranker = reranker
        self.context_optimizer = context_optimizer
        self.store = store
        self.artifact_store = artifact_store

    def run(
        self,
        *,
        query: str,
        collection_id: str,
        strategies: list[str],
        top_k: int,
        candidate_k: int | None = None,
        rerank: bool = False,
        budget: TokenBudget | None = None,
        merge_adjacent: bool = True,
        compression_mode: str = "none",
        gold_chunk_ids: list[str] | None = None,
        save_artifact: bool = False,
        artifact_name: str | None = None,
    ) -> dict:
        budget = budget or TokenBudget()
        gold_chunk_ids = gold_chunk_ids or []
        strategies = list(dict.fromkeys(strategies))
        runs: list[dict] = []

        for strategy in strategies:
            retriever = self.retrievers[strategy]
            started = perf_counter()
            fetch_k = candidate_k or top_k
            candidates = retriever.retrieve(query, collection_id, top_k=fetch_k)
            reranked = False
            if rerank:
                results = self.reranker.rerank(query, candidates, top_k=top_k)
                reranked = True
            else:
                results = candidates[:top_k]

            optimization = self.context_optimizer.optimize(
                results,
                budget,
                merge_adjacent=merge_adjacent,
                compression_mode=compression_mode,
            )
            latency_ms = int((perf_counter() - started) * 1000)
            token_estimate = sum(item.token_estimate for item in results)
            selected_ids = [item.chunk_id for item in optimization.selected]
            result_ids = [item.chunk_id for item in results]

            run_record = RetrievalRunRecord(
                query=query,
                collection_id=collection_id,
                strategy_config={
                    "strategy": strategy,
                    "top_k": top_k,
                    "candidate_k": candidate_k,
                    "rerank": rerank,
                    "merge_adjacent": merge_adjacent,
                    "compression_mode": compression_mode,
                    "experiment": True,
                },
                candidate_count=len(candidates),
                reranked_count=len(results) if reranked else 0,
                kept_evidence_count=len(optimization.selected),
                token_estimate=optimization.token_estimate,
                latency_ms=latency_ms,
                evidence_ids=selected_ids,
                trace_steps=[
                    {"step": "retrieve", "strategy": strategy, "count": len(candidates)},
                    {"step": "rerank", "enabled": reranked, "count": len(results)},
                    {"step": "assemble", "selected_count": len(optimization.selected)},
                ],
            )
            self.store.log_retrieval_run(run_record)

            runs.append(
                {
                    "strategy": strategy,
                    "reranked": reranked,
                    "candidate_count": len(candidates),
                    "result_count": len(results),
                    "selected_count": len(optimization.selected),
                    "dropped_count": len(optimization.dropped),
                    "latency_ms": latency_ms,
                    "token_estimate": token_estimate,
                    "assembled_token_estimate": optimization.token_estimate,
                    "original_token_estimate": optimization.original_token_estimate,
                    "token_savings": optimization.token_savings,
                    "token_per_evidence": (
                        optimization.token_estimate / len(optimization.selected)
                        if optimization.selected
                        else 0.0
                    ),
                    "merged_count": optimization.merged_count,
                    "compression_mode": optimization.compression_mode,
                    "chunk_ids": selected_ids,
                    "result_chunk_ids": result_ids,
                    "metrics": {
                        "recall_at_k": recall_at_k(result_ids, gold_chunk_ids, top_k),
                        "mrr": mean_reciprocal_rank(result_ids, gold_chunk_ids),
                    },
                }
            )

        overlaps = {}
        for left, right in combinations(runs, 2):
            key = f"{left['strategy']}__{right['strategy']}"
            overlaps[key] = jaccard_overlap(left["result_chunk_ids"], right["result_chunk_ids"])

        result = {
            "query": query,
            "collection_id": collection_id,
            "strategies": runs,
            "overlap": overlaps,
        }
        if save_artifact:
            artifact_meta = self.artifact_store.save(result, name=artifact_name)
            result.update(artifact_meta)
        return result
