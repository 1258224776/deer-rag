from __future__ import annotations


def recall_at_k(retrieved_ids: list[str], gold_ids: list[str], k: int) -> float | None:
    if not gold_ids or k <= 0:
        return None
    retrieved = set(retrieved_ids[:k])
    gold = set(gold_ids)
    return len(retrieved & gold) / len(gold)


def mean_reciprocal_rank(retrieved_ids: list[str], gold_ids: list[str]) -> float | None:
    if not gold_ids:
        return None
    gold = set(gold_ids)
    for index, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in gold:
            return 1.0 / index
    return 0.0


def ndcg_at_k(retrieved_ids: list[str], gold_ids: list[str], k: int) -> float | None:
    if not gold_ids or k <= 0:
        return None
    gold = set(gold_ids)
    dcg = 0.0
    for index, chunk_id in enumerate(retrieved_ids[:k], start=1):
        if chunk_id in gold:
            dcg += 1.0 / _log2(index + 1)

    ideal_hits = min(len(gold), k)
    if ideal_hits == 0:
        return None
    idcg = sum(1.0 / _log2(index + 1) for index in range(1, ideal_hits + 1))
    if idcg == 0:
        return None
    return dcg / idcg


def jaccard_overlap(left_ids: list[str], right_ids: list[str]) -> float:
    left = set(left_ids)
    right = set(right_ids)
    union = left | right
    if not union:
        return 1.0
    return len(left & right) / len(union)


def _log2(value: int) -> float:
    from math import log2

    return log2(value)
