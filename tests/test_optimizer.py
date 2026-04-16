from __future__ import annotations

from app.context.optimizer import ContextOptimizer
from app.core.models import EvidencePack, TokenBudget


def make_evidence(
    *,
    chunk_id: str,
    document_id: str = "doc-1",
    snippet: str,
    score: float = 1.0,
    rerank_score: float | None = None,
    token_estimate: int = 0,
    chunk_index: int | None = None,
) -> EvidencePack:
    metadata = {}
    if chunk_index is not None:
        metadata["chunk_index"] = chunk_index
    return EvidencePack(
        chunk_id=chunk_id,
        document_id=document_id,
        snippet=snippet,
        title="Doc",
        source="memory://doc",
        score=score,
        rerank_score=rerank_score,
        token_estimate=token_estimate,
        metadata=metadata,
    )


def test_optimizer_deduplicates_by_chunk_id_and_keeps_higher_score() -> None:
    optimizer = ContextOptimizer()
    budget = TokenBudget(total=100, reserve=0, per_evidence=100)
    low = make_evidence(chunk_id="dup", snippet="low", score=0.2, token_estimate=10)
    high = make_evidence(chunk_id="dup", snippet="high", score=0.9, token_estimate=10)

    result = optimizer.optimize([low, high], budget, merge_adjacent=False)

    assert len(result.selected) == 1
    assert result.selected[0].snippet == "high"
    assert any(item["reason"] == "deduplicated_lower_score" for item in result.dropped)


def test_optimizer_merges_adjacent_chunks_from_same_document() -> None:
    optimizer = ContextOptimizer()
    budget = TokenBudget(total=200, reserve=0, per_evidence=200)
    first = make_evidence(chunk_id="c1", snippet="first", chunk_index=0, token_estimate=10)
    second = make_evidence(chunk_id="c2", snippet="second", chunk_index=1, token_estimate=10)

    result = optimizer.optimize([first, second], budget, merge_adjacent=True)

    assert result.merged_count == 1
    assert len(result.selected) == 1
    assert "first" in result.selected[0].snippet
    assert "second" in result.selected[0].snippet
    assert result.selected[0].metadata["merged_adjacent"] is True


def test_optimizer_preserves_zero_rerank_score_when_merging() -> None:
    optimizer = ContextOptimizer()
    budget = TokenBudget(total=200, reserve=0, per_evidence=200)
    left = make_evidence(chunk_id="c1", snippet="left", score=0.8, rerank_score=0.0, chunk_index=0, token_estimate=10)
    right = make_evidence(chunk_id="c2", snippet="right", score=0.6, rerank_score=None, chunk_index=1, token_estimate=10)

    result = optimizer.optimize([left, right], budget, merge_adjacent=True)

    assert len(result.selected) == 1
    assert result.selected[0].rerank_score == 0.6


def test_optimizer_trims_to_budget_and_reports_savings() -> None:
    optimizer = ContextOptimizer()
    budget = TokenBudget(total=30, reserve=0, per_evidence=10, max_evidence_count=1)
    item = make_evidence(
        chunk_id="long",
        snippet="alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu",
        token_estimate=20,
    )

    result = optimizer.optimize([item], budget, merge_adjacent=False, compression_mode="extractive")

    assert len(result.selected) == 1
    assert result.selected[0].token_estimate <= 10
    assert result.token_savings >= 0
    assert result.compression_mode == "extractive"
