from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import exp
from typing import Any

from app.core.interfaces import BaseReranker, BaseRetriever
from app.core.models import Chunk, RetrievalOptions, SourceDocument
from app.core.models import EvidencePack
from app.retrieval.query_rewrite import RuleBasedQueryRewriter
from app.retrieval.text import contains_token, extract_entity_terms
from app.storage import SQLiteMetadataStore


@dataclass
class RetrievalPipelineResult:
    query: str
    rewritten_queries: list[str]
    candidates: list[EvidencePack]
    results: list[EvidencePack]
    reranked: bool
    trace_steps: list[dict[str, Any]]
    diagnostics: dict[str, Any]


class RetrievalPipeline:
    def __init__(
        self,
        *,
        retrievers: dict[str, BaseRetriever],
        reranker: BaseReranker,
        store: SQLiteMetadataStore,
        query_rewriter: RuleBasedQueryRewriter | None = None,
    ) -> None:
        self.retrievers = retrievers
        self.reranker = reranker
        self.store = store
        self.query_rewriter = query_rewriter or RuleBasedQueryRewriter()

    def run(
        self,
        *,
        query: str,
        collection_id: str,
        strategy: str,
        top_k: int,
        candidate_k: int | None = None,
        rerank: bool = False,
        options: RetrievalOptions | None = None,
    ) -> RetrievalPipelineResult:
        options = options or RetrievalOptions()
        retriever = self.retrievers[strategy]
        fetch_k = candidate_k or top_k
        rewritten_queries = self.query_rewriter.rewrite(query) if options.query_rewrite else [query]
        trace_steps: list[dict[str, Any]] = []

        raw_candidates: list[EvidencePack] = []
        for rewritten_query in rewritten_queries:
            hits = retriever.retrieve(rewritten_query, collection_id, top_k=fetch_k)
            trace_steps.append({"step": "retrieve", "query": rewritten_query, "count": len(hits)})
            raw_candidates.extend(
                item.model_copy(
                    update={
                        "metadata": {
                            **item.metadata,
                            "query_variant": rewritten_query,
                        }
                    }
                )
                for item in hits
            )

        candidates = self._merge_variant_hits(raw_candidates)
        graph_added = 0
        if options.graph_expansion.enabled:
            candidates, graph_added = self._expand_graph(
                collection_id=collection_id,
                query=query,
                candidates=candidates,
                options=options,
                fetch_k=fetch_k,
            )
            trace_steps.append({"step": "graph_expand", "enabled": True, "added": graph_added})

        before_filter = len(candidates)
        candidates = self._apply_metadata_filters(candidates, options)
        trace_steps.append(
            {
                "step": "filter",
                "before": before_filter,
                "after": len(candidates),
            }
        )

        entity_matches = 0
        if options.entity_aware:
            candidates, entity_matches = self._apply_entity_boost(query, candidates)
            trace_steps.append({"step": "entity_boost", "matches": entity_matches})

        freshness_applied = 0
        if options.freshness.enabled:
            candidates, freshness_applied = self._apply_freshness_boost(candidates, options)
            trace_steps.append({"step": "freshness_boost", "applied": freshness_applied})

        ranked_candidates = sorted(candidates, key=self._effective_score, reverse=True)
        reranked = False
        if rerank:
            results = self.reranker.rerank(query, ranked_candidates[:fetch_k], top_k=top_k)
            reranked = True
        else:
            results = ranked_candidates[:top_k]

        if options.timeline_mode:
            results = self._order_timeline(results, options.timeline_order)
            trace_steps.append({"step": "timeline_order", "order": options.timeline_order, "count": len(results)})

        return RetrievalPipelineResult(
            query=query,
            rewritten_queries=rewritten_queries,
            candidates=ranked_candidates,
            results=results,
            reranked=reranked,
            trace_steps=trace_steps,
            diagnostics={
                "graph_added": graph_added,
                "filtered_out": max(before_filter - len(candidates), 0),
                "entity_matches": entity_matches,
                "freshness_applied": freshness_applied,
            },
        )

    def _merge_variant_hits(self, hits: list[EvidencePack]) -> list[EvidencePack]:
        merged: dict[str, EvidencePack] = {}
        variant_map: dict[str, list[str]] = {}
        for item in hits:
            variant = str(item.metadata.get("query_variant", ""))
            variant_map.setdefault(item.chunk_id, [])
            if variant and variant not in variant_map[item.chunk_id]:
                variant_map[item.chunk_id].append(variant)

            if item.chunk_id not in merged or self._effective_score(item) > self._effective_score(merged[item.chunk_id]):
                merged[item.chunk_id] = item

        results: list[EvidencePack] = []
        for chunk_id, item in merged.items():
            variants = variant_map.get(chunk_id, [])
            bonus = max(len(variants) - 1, 0) * 0.02
            results.append(
                item.model_copy(
                    update={
                        "score": item.score + bonus,
                        "metadata": {
                            **item.metadata,
                            "query_variants": variants,
                            "rewrite_bonus": bonus,
                        },
                    }
                )
            )
        return results

    def _apply_metadata_filters(self, candidates: list[EvidencePack], options: RetrievalOptions) -> list[EvidencePack]:
        filters = options.metadata_filters
        if (
            not filters.source_types
            and not filters.document_metadata
            and not filters.chunk_metadata
            and filters.published_after is None
            and filters.published_before is None
            and filters.ingested_after is None
            and filters.ingested_before is None
        ):
            return candidates

        filtered: list[EvidencePack] = []
        published_after = self._parse_datetime(filters.published_after)
        published_before = self._parse_datetime(filters.published_before)
        ingested_after = self._parse_datetime(filters.ingested_after)
        ingested_before = self._parse_datetime(filters.ingested_before)
        for item in candidates:
            if filters.source_types:
                source_type = str(item.metadata.get("source_type", ""))
                if source_type not in filters.source_types:
                    continue

            document_metadata = item.metadata.get("document_metadata", {})
            chunk_metadata = item.metadata.get("chunk_metadata", {})
            if not self._metadata_subset_matches(filters.document_metadata, document_metadata):
                continue
            if not self._metadata_subset_matches(filters.chunk_metadata, chunk_metadata):
                continue

            published_at = self._parse_datetime(item.metadata.get("published_at"))
            ingested_at = self._parse_datetime(item.metadata.get("ingested_at"))
            if published_after is not None and (published_at is None or published_at < published_after):
                continue
            if published_before is not None and (published_at is None or published_at > published_before):
                continue
            if ingested_after is not None and (ingested_at is None or ingested_at < ingested_after):
                continue
            if ingested_before is not None and (ingested_at is None or ingested_at > ingested_before):
                continue

            filtered.append(item)
        return filtered

    def _apply_entity_boost(self, query: str, candidates: list[EvidencePack]) -> tuple[list[EvidencePack], int]:
        entity_terms = extract_entity_terms(query)
        if not entity_terms:
            return candidates, 0

        boosted: list[EvidencePack] = []
        matched_candidates = 0
        for item in candidates:
            matches = [
                term
                for term in entity_terms
                if contains_token(item.title, term) or contains_token(item.snippet, term) or contains_token(item.source, term)
            ]
            if not matches:
                boosted.append(item)
                continue

            matched_candidates += 1
            bonus = min(0.12, 0.04 * len(matches))
            boosted.append(
                item.model_copy(
                    update={
                        "score": item.score + bonus,
                        "metadata": {
                            **item.metadata,
                            "entity_matches": matches,
                            "entity_bonus": bonus,
                        },
                    }
                )
            )
        return boosted, matched_candidates

    def _apply_freshness_boost(
        self,
        candidates: list[EvidencePack],
        options: RetrievalOptions,
    ) -> tuple[list[EvidencePack], int]:
        boosted: list[EvidencePack] = []
        applied = 0
        now = datetime.now(timezone.utc)
        half_life = max(options.freshness.half_life_days, 1)
        for item in candidates:
            date_value = self._parse_datetime(item.metadata.get(options.freshness.date_field))
            if date_value is None:
                boosted.append(item)
                continue

            age_days = max((now - date_value).total_seconds() / 86400.0, 0.0)
            freshness_ratio = exp(-age_days / float(half_life))
            bonus = options.freshness.weight * freshness_ratio
            applied += 1
            boosted.append(
                item.model_copy(
                    update={
                        "score": item.score + bonus,
                        "metadata": {
                            **item.metadata,
                            "freshness_bonus": bonus,
                            "freshness_age_days": age_days,
                        },
                    }
                )
            )
        return boosted, applied

    def _expand_graph(
        self,
        *,
        collection_id: str,
        query: str,
        candidates: list[EvidencePack],
        options: RetrievalOptions,
        fetch_k: int,
    ) -> tuple[list[EvidencePack], int]:
        existing = {item.chunk_id: item for item in candidates}
        added = 0
        query_entities = extract_entity_terms(query)
        adjacency_limit = max(options.graph_expansion.max_neighbors, 1)
        neighbor_indexes_by_doc: dict[str, set[int]] = {}

        for seed in candidates[:fetch_k]:
            chunk_index = seed.metadata.get("chunk_index")
            if chunk_index is None:
                continue

            for distance in range(1, options.graph_expansion.hops + 1):
                indexes = neighbor_indexes_by_doc.setdefault(seed.document_id, set())
                indexes.add(int(chunk_index) - distance)
                indexes.add(int(chunk_index) + distance)

        neighbor_records = self.store.get_chunk_records_by_document_indexes(collection_id, neighbor_indexes_by_doc)
        neighbor_record_map = {
            (record["chunk"].document_id, record["chunk"].chunk_index): record
            for record in neighbor_records
        }

        for seed in candidates[:fetch_k]:
            chunk_index = seed.metadata.get("chunk_index")
            if chunk_index is None:
                continue
            for distance in range(1, options.graph_expansion.hops + 1):
                for neighbor_index in (int(chunk_index) - distance, int(chunk_index) + distance):
                    record = neighbor_record_map.get((seed.document_id, neighbor_index))
                    if record is None or added >= adjacency_limit * fetch_k:
                        continue
                    neighbor = record["chunk"]
                    if neighbor.id in existing:
                        continue
                    candidate = self._build_expanded_candidate(
                        chunk=neighbor,
                        document=record["document"],
                        score=(seed.score * 0.5) + (options.graph_expansion.adjacency_weight / distance),
                        retrieval="graph-adjacent",
                        metadata={
                            "graph_seed_chunk_id": seed.chunk_id,
                            "graph_distance": distance,
                        },
                    )
                    existing[neighbor.id] = candidate
                    added += 1

        if query_entities:
            entity_candidates = self._retrieve_entity_candidates(
                collection_id=collection_id,
                query_entities=query_entities,
                limit=adjacency_limit,
                weight=options.graph_expansion.entity_weight,
            )
            for item in entity_candidates:
                if item.chunk_id in existing:
                    continue
                existing[item.chunk_id] = item
                added += 1

        merged = sorted(existing.values(), key=self._effective_score, reverse=True)
        return merged, added

    def _retrieve_entity_candidates(
        self,
        *,
        collection_id: str,
        query_entities: list[str],
        limit: int,
        weight: float,
    ) -> list[EvidencePack]:
        bm25_retriever = self.retrievers.get("bm25")
        if bm25_retriever is None or not query_entities or limit <= 0:
            return []

        entity_query = " ".join(query_entities)
        fetch_k = max(limit * 4, limit)
        hits = bm25_retriever.retrieve(entity_query, collection_id, top_k=fetch_k)

        candidates: list[EvidencePack] = []
        for hit in hits:
            matches = [
                term
                for term in query_entities
                if contains_token(hit.snippet, term) or contains_token(hit.title, term) or contains_token(hit.source, term)
            ]
            if not matches:
                continue

            score = hit.score + (weight * len(matches))
            candidates.append(
                hit.model_copy(
                    update={
                        "score": score,
                        "metadata": {
                            **hit.metadata,
                            "retrieval": "graph-entity",
                            "entity_terms": query_entities,
                            "graph_entity_matches": matches,
                            "graph_entity_source_retrieval": hit.metadata.get("retrieval"),
                        },
                    }
                )
            )
            if len(candidates) >= limit:
                break

        return sorted(candidates, key=self._effective_score, reverse=True)[:limit]

    def _build_expanded_candidate(
        self,
        *,
        chunk: Chunk,
        document: SourceDocument,
        score: float,
        retrieval: str,
        metadata: dict[str, Any],
    ) -> EvidencePack:
        return EvidencePack(
            chunk_id=chunk.id,
            document_id=document.id,
            snippet=chunk.text,
            title=document.title,
            source=document.source_uri,
            score=score,
            token_estimate=chunk.token_count,
            metadata={
                "chunk_index": chunk.chunk_index,
                "section_title": chunk.section_title,
                "document_metadata": document.metadata,
                "chunk_metadata": chunk.metadata,
                "source_type": document.source_type,
                "published_at": document.published_at.isoformat() if document.published_at is not None else None,
                "ingested_at": document.ingested_at.isoformat(),
                "retrieval": retrieval,
                **metadata,
            },
        )

    def _order_timeline(self, results: list[EvidencePack], order: str) -> list[EvidencePack]:
        dated: list[tuple[datetime, EvidencePack]] = []
        undated: list[EvidencePack] = []
        for item in results:
            date_value = self._parse_datetime(item.metadata.get("published_at")) or self._parse_datetime(item.metadata.get("ingested_at"))
            if date_value is None:
                undated.append(item)
                continue
            dated.append((date_value, item))

        dated.sort(key=lambda entry: entry[0], reverse=order == "desc")
        return [item for _date, item in dated] + undated

    def _metadata_subset_matches(self, expected: dict[str, Any], actual: dict[str, Any]) -> bool:
        for key, value in expected.items():
            if actual.get(key) != value:
                return False
        return True

    def _parse_datetime(self, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
            except ValueError:
                return None
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
        return None

    def _effective_score(self, item: EvidencePack) -> float:
        if item.rerank_score is not None:
            return item.rerank_score
        return item.score
