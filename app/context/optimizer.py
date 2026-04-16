from __future__ import annotations

from dataclasses import dataclass

import tiktoken

from app.core.models import EvidencePack, TokenBudget


@dataclass
class OptimizationResult:
    selected: list[EvidencePack]
    dropped: list[dict]
    token_estimate: int
    original_token_estimate: int
    available_budget: int
    token_savings: int
    merged_count: int
    compression_mode: str


class ContextOptimizer:
    def __init__(self, encoder_name: str = "cl100k_base") -> None:
        try:
            self.encoder = tiktoken.get_encoding(encoder_name)
        except Exception:
            self.encoder = None

    def optimize(
        self,
        evidence: list[EvidencePack],
        budget: TokenBudget,
        *,
        merge_adjacent: bool = True,
        compression_mode: str = "none",
    ) -> OptimizationResult:
        original_token_estimate = sum(self._normalize_tokens(item).token_estimate for item in evidence)
        deduped, dedup_drops = self._deduplicate(evidence)
        merged_count = 0
        if merge_adjacent:
            deduped, merge_drops, merged_count = self._merge_adjacent(deduped)
            dedup_drops.extend(merge_drops)
        ranked = sorted(deduped, key=self._effective_score, reverse=True)

        selected: list[EvidencePack] = []
        dropped = list(dedup_drops)
        running_tokens = 0

        for item in ranked:
            if budget.max_evidence_count is not None and len(selected) >= budget.max_evidence_count:
                dropped.append({"chunk_id": item.chunk_id, "reason": "max_evidence_count"})
                continue

            trimmed = self._apply_per_evidence_budget(item, budget.per_evidence, compression_mode=compression_mode)
            if trimmed.token_estimate <= 0:
                dropped.append({"chunk_id": item.chunk_id, "reason": "empty_after_trim"})
                continue

            if running_tokens + trimmed.token_estimate > budget.available:
                dropped.append({"chunk_id": item.chunk_id, "reason": "budget_exceeded"})
                continue

            selected.append(trimmed)
            running_tokens += trimmed.token_estimate

        return OptimizationResult(
            selected=selected,
            dropped=dropped,
            token_estimate=running_tokens,
            original_token_estimate=original_token_estimate,
            available_budget=budget.available,
            token_savings=max(original_token_estimate - running_tokens, 0),
            merged_count=merged_count,
            compression_mode=compression_mode,
        )

    def _deduplicate(self, evidence: list[EvidencePack]) -> tuple[list[EvidencePack], list[dict]]:
        best: dict[str, EvidencePack] = {}
        drops: list[dict] = []

        for item in evidence:
            key = item.chunk_id or f"{item.source}:{item.snippet[:120]}"
            if key not in best:
                best[key] = self._normalize_tokens(item)
                continue

            current = best[key]
            candidate = self._normalize_tokens(item)
            if self._effective_score(candidate) > self._effective_score(current):
                best[key] = candidate
                drops.append({"chunk_id": current.chunk_id, "reason": "deduplicated_lower_score"})
            else:
                drops.append({"chunk_id": candidate.chunk_id, "reason": "deduplicated_lower_score"})

        return list(best.values()), drops

    def _normalize_tokens(self, item: EvidencePack) -> EvidencePack:
        if item.token_estimate > 0:
            return item
        return item.model_copy(update={"token_estimate": self._estimate_tokens(item.snippet)})

    def _apply_per_evidence_budget(self, item: EvidencePack, per_evidence: int, *, compression_mode: str = "none") -> EvidencePack:
        normalized = self._normalize_tokens(item)
        compressed = self._compress_evidence(normalized, compression_mode=compression_mode, per_evidence=per_evidence)
        normalized = self._normalize_tokens(compressed)
        if normalized.token_estimate <= per_evidence:
            return normalized

        trimmed_snippet = self._trim_to_tokens(normalized.snippet, per_evidence)
        trimmed_tokens = self._estimate_tokens(trimmed_snippet)
        return normalized.model_copy(
            update={
                "snippet": trimmed_snippet,
                "token_estimate": trimmed_tokens,
                "metadata": {
                    **normalized.metadata,
                    "trimmed_for_budget": True,
                    "compression_mode": compression_mode,
                },
            }
        )

    def _compress_evidence(self, item: EvidencePack, *, compression_mode: str, per_evidence: int) -> EvidencePack:
        if compression_mode == "none":
            return item

        snippet = item.snippet.strip()
        if not snippet:
            return item

        if compression_mode == "extractive":
            compressed = self._extractive_compress(snippet, token_limit=max(1, int(per_evidence * 0.75)))
        else:
            compressed = snippet

        if compressed == snippet:
            return item

        return item.model_copy(
            update={
                "snippet": compressed,
                "token_estimate": self._estimate_tokens(compressed),
                "metadata": {
                    **item.metadata,
                    "compressed": True,
                    "compression_mode": compression_mode,
                },
            }
        )

    def _extractive_compress(self, text: str, token_limit: int) -> str:
        paragraphs = [part.strip() for part in text.splitlines() if part.strip()]
        if not paragraphs:
            return self._trim_to_tokens(text, token_limit)

        if len(paragraphs) == 1:
            return self._head_tail_text(paragraphs[0], token_limit)

        candidate = f"{paragraphs[0]}\n\n{paragraphs[-1]}"
        if self._estimate_tokens(candidate) <= token_limit:
            return candidate
        return self._head_tail_text(candidate, token_limit)

    def _head_tail_text(self, text: str, token_limit: int) -> str:
        if token_limit <= 0:
            return ""
        if self.encoder is not None:
            tokens = self.encoder.encode(text)
            if len(tokens) <= token_limit:
                return text.strip()
            head = max(token_limit // 2, 1)
            tail = max(token_limit - head, 1)
            return f"{self.encoder.decode(tokens[:head]).strip()}\n...\n{self.encoder.decode(tokens[-tail:]).strip()}".strip()

        words = text.split()
        if len(words) <= token_limit:
            return text.strip()
        head = max(token_limit // 2, 1)
        tail = max(token_limit - head, 1)
        return f"{' '.join(words[:head]).strip()}\n...\n{' '.join(words[-tail:]).strip()}".strip()

    def _merge_adjacent(self, evidence: list[EvidencePack]) -> tuple[list[EvidencePack], list[dict], int]:
        by_doc: dict[str, list[EvidencePack]] = {}
        passthrough: list[EvidencePack] = []
        drops: list[dict] = []

        for item in evidence:
            chunk_index = item.metadata.get("chunk_index")
            if chunk_index is None:
                passthrough.append(item)
                continue
            by_doc.setdefault(item.document_id, []).append(item)

        merged: list[EvidencePack] = list(passthrough)
        merged_count = 0

        for doc_items in by_doc.values():
            ordered = sorted(doc_items, key=lambda item: int(item.metadata.get("chunk_index", 0)))
            current = ordered[0]
            merged_ids = [current.chunk_id]
            merged_indexes = [int(current.metadata.get("chunk_index", 0))]

            for next_item in ordered[1:]:
                next_index = int(next_item.metadata.get("chunk_index", 0))
                last_index = merged_indexes[-1]
                if next_index == last_index + 1:
                    current = self._merge_pair(current, next_item, merged_ids, merged_indexes)
                    merged_ids.append(next_item.chunk_id)
                    merged_indexes.append(next_index)
                    merged_count += 1
                    drops.append({"chunk_id": next_item.chunk_id, "reason": "merged_adjacent"})
                else:
                    merged.append(current)
                    current = next_item
                    merged_ids = [current.chunk_id]
                    merged_indexes = [int(current.metadata.get("chunk_index", 0))]

            merged.append(current)

        return merged, drops, merged_count

    def _merge_pair(
        self,
        left: EvidencePack,
        right: EvidencePack,
        merged_ids: list[str],
        merged_indexes: list[int],
    ) -> EvidencePack:
        merged_snippet = f"{left.snippet}\n\n{right.snippet}".strip()
        merged_chunk_ids = list(dict.fromkeys([*merged_ids, right.chunk_id]))
        merged_chunk_indexes = list(dict.fromkeys([*merged_indexes, int(right.metadata.get("chunk_index", 0))]))
        return left.model_copy(
            update={
                "snippet": merged_snippet,
                "token_estimate": self._estimate_tokens(merged_snippet),
                "score": max(left.score, right.score),
                "rerank_score": max(
                    left.rerank_score if left.rerank_score is not None else left.score,
                    right.rerank_score if right.rerank_score is not None else right.score,
                ),
                "metadata": {
                    **left.metadata,
                    "merged_adjacent": True,
                    "merged_chunk_ids": merged_chunk_ids,
                    "merged_chunk_indexes": merged_chunk_indexes,
                },
            }
        )

    def _trim_to_tokens(self, text: str, token_limit: int) -> str:
        if token_limit <= 0 or not text.strip():
            return ""

        if self.encoder is not None:
            tokens = self.encoder.encode(text)
            return self.encoder.decode(tokens[:token_limit]).strip()

        words = text.split()
        return " ".join(words[:token_limit]).strip()

    def _estimate_tokens(self, text: str) -> int:
        if not text.strip():
            return 0
        if self.encoder is not None:
            return len(self.encoder.encode(text))
        return max(1, len(text.split()))

    def _effective_score(self, item: EvidencePack) -> float:
        if item.rerank_score is not None:
            return item.rerank_score
        return item.score
