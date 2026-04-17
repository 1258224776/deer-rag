from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import os
import re

import httpx
import tiktoken

from app.core.models import EvidencePack, TokenBudget
from app.retrieval.text import extract_entity_terms, tokenize_text


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
        self.abstractive_api_key = os.getenv("OPENAI_API_KEY")
        self.abstractive_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.abstractive_model = os.getenv("DEER_RAG_ABSTRACTIVE_MODEL")

    def optimize(
        self,
        evidence: list[EvidencePack],
        budget: TokenBudget,
        *,
        merge_adjacent: bool = True,
        compression_mode: str = "none",
        query: str | None = None,
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

            trimmed = self._apply_per_evidence_budget(
                item,
                budget.per_evidence,
                compression_mode=compression_mode,
                query=query,
            )
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

    def _apply_per_evidence_budget(
        self,
        item: EvidencePack,
        per_evidence: int,
        *,
        compression_mode: str = "none",
        query: str | None = None,
    ) -> EvidencePack:
        normalized = self._normalize_tokens(item)
        compressed = self._compress_evidence(
            normalized,
            compression_mode=compression_mode,
            per_evidence=per_evidence,
            query=query,
        )
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

    def _compress_evidence(
        self,
        item: EvidencePack,
        *,
        compression_mode: str,
        per_evidence: int,
        query: str | None,
    ) -> EvidencePack:
        if compression_mode == "none":
            return item

        snippet = item.snippet.strip()
        if not snippet:
            return item

        token_limit = max(1, int(per_evidence * 0.75))
        compression_metadata = {
            **item.metadata,
            "compressed": True,
            "compression_mode": compression_mode,
        }
        if compression_mode == "extractive":
            compressed = self._extractive_compress(snippet, token_limit=token_limit, query=query)
        elif compression_mode == "abstractive":
            compressed, used_remote = self._abstractive_compress(snippet, token_limit=token_limit, query=query)
            compression_metadata["abstractive_remote"] = used_remote
            if not used_remote:
                compression_metadata["abstractive_fallback"] = "extractive"
        else:
            compressed = snippet

        if compressed == snippet:
            return item

        return item.model_copy(
            update={
                "snippet": compressed,
                "token_estimate": self._estimate_tokens(compressed),
                "metadata": compression_metadata,
            }
        )

    def _extractive_compress(self, text: str, token_limit: int, *, query: str | None = None) -> str:
        sentences = self._split_sentences(text)
        if not sentences:
            return self._trim_to_tokens(text, token_limit)
        if len(sentences) == 1:
            return self._head_tail_text(sentences[0], token_limit)

        query_terms = set(extract_entity_terms(query or "")) or set(tokenize_text(query or ""))
        corpus_terms = [token for token in tokenize_text(text) if len(token) >= 2]
        term_weights = Counter(corpus_terms)

        scored: list[tuple[float, int, str]] = []
        for index, sentence in enumerate(sentences):
            sentence_terms = set(tokenize_text(sentence))
            if not sentence_terms:
                continue
            overlap = sum(1 for term in sentence_terms if term in query_terms)
            keyword_weight = sum(term_weights.get(term, 0) for term in sentence_terms)
            entity_weight = len([term for term in query_terms if term in sentence_terms])
            structure_bonus = 1.0 if index == 0 else 0.0
            digit_bonus = 0.5 if any(char.isdigit() for char in sentence) else 0.0
            score = (overlap * 3.0) + keyword_weight + (entity_weight * 1.5) + structure_bonus + digit_bonus
            scored.append((score, index, sentence))

        if not scored:
            return self._trim_to_tokens(text, token_limit)

        chosen: list[tuple[int, str]] = []
        running_tokens = 0
        for _score, index, sentence in sorted(scored, key=lambda item: item[0], reverse=True):
            sentence_tokens = self._estimate_tokens(sentence)
            if sentence_tokens <= 0:
                continue
            if running_tokens + sentence_tokens > token_limit and chosen:
                continue
            chosen.append((index, sentence))
            running_tokens += sentence_tokens
            if running_tokens >= token_limit:
                break

        if not chosen:
            return self._trim_to_tokens(text, token_limit)

        chosen.sort(key=lambda item: item[0])
        compressed = " ".join(sentence for _index, sentence in chosen).strip()
        if self._estimate_tokens(compressed) > token_limit:
            return self._trim_to_tokens(compressed, token_limit)
        return compressed

    def _abstractive_compress(self, text: str, token_limit: int, *, query: str | None = None) -> tuple[str, bool]:
        if not self.abstractive_api_key or not self.abstractive_model:
            return self._extractive_compress(text, token_limit=token_limit, query=query), False

        prompt = (
            "Compress the following evidence into a concise citation-preserving summary. "
            "Keep named entities, dates, and quantitative facts. Do not invent facts.\n\n"
            f"Query: {query or 'N/A'}\n\nEvidence:\n{text}"
        )
        headers = {
            "Authorization": f"Bearer {self.abstractive_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.abstractive_model,
            "messages": [
                {"role": "system", "content": "You compress retrieval evidence for downstream RAG prompts."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": max(64, token_limit),
        }

        try:
            response = httpx.post(
                f"{self.abstractive_base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=15.0,
            )
            response.raise_for_status()
            body = response.json()
            content = body["choices"][0]["message"]["content"].strip()
        except Exception:
            return self._extractive_compress(text, token_limit=token_limit, query=query), False

        if not content:
            return self._extractive_compress(text, token_limit=token_limit, query=query), False
        return self._trim_to_tokens(content, token_limit), True

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

    def _split_sentences(self, text: str) -> list[str]:
        blocks = [block.strip() for block in re.split(r"[\r\n]+", text) if block.strip()]
        sentences: list[str] = []
        for block in blocks:
            parts = [part.strip() for part in re.split(r"(?<=[。！？.!?])\s+", block) if part.strip()]
            if parts:
                sentences.extend(parts)
            else:
                sentences.append(block)
        return sentences

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
        return max(1, len(tokenize_text(text)))

    def _effective_score(self, item: EvidencePack) -> float:
        if item.rerank_score is not None:
            return item.rerank_score
        return item.score
