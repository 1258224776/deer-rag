from __future__ import annotations

from app.evaluation.metrics import jaccard_overlap, mean_reciprocal_rank, ndcg_at_k, recall_at_k


def test_recall_at_k_returns_none_without_gold() -> None:
    assert recall_at_k(["a", "b"], [], 2) is None


def test_recall_at_k_uses_top_k_window() -> None:
    score = recall_at_k(["a", "b", "c"], ["c", "d"], 2)
    assert score == 0.0


def test_recall_at_k_counts_gold_hits() -> None:
    score = recall_at_k(["a", "b", "c"], ["b", "c"], 3)
    assert score == 1.0


def test_mean_reciprocal_rank_returns_none_without_gold() -> None:
    assert mean_reciprocal_rank(["a", "b"], []) is None


def test_mean_reciprocal_rank_returns_inverse_of_first_hit_rank() -> None:
    score = mean_reciprocal_rank(["x", "y", "z"], ["y", "other"])
    assert score == 0.5


def test_jaccard_overlap_returns_one_for_two_empty_lists() -> None:
    assert jaccard_overlap([], []) == 1.0


def test_jaccard_overlap_computes_set_overlap() -> None:
    score = jaccard_overlap(["a", "b", "c"], ["b", "c", "d"])
    assert score == 0.5


def test_ndcg_at_k_returns_none_without_gold() -> None:
    assert ndcg_at_k(["a", "b"], [], 2) is None


def test_ndcg_at_k_rewards_higher_ranked_hits() -> None:
    score = ndcg_at_k(["a", "b", "c"], ["a", "c"], 3)
    assert score is not None
    assert 0.9 <= score <= 1.0
