from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Collection(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str = ""
    domain: str = "general"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceDocument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    collection_id: str
    title: str
    source_uri: str
    source_type: str
    checksum: str
    published_at: datetime | None = None
    ingested_at: datetime = Field(default_factory=utc_now)
    raw_text_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    chunk_index: int
    text: str
    token_count: int = 0
    section_title: str | None = None
    parent_span: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TokenBudget(BaseModel):
    total: int = 6000
    reserve: int = 1000
    per_evidence: int = 600
    max_evidence_count: int | None = None

    @property
    def available(self) -> int:
        return max(self.total - self.reserve, 0)


class EvidencePack(BaseModel):
    chunk_id: str
    document_id: str
    snippet: str
    title: str = ""
    source: str = ""
    score: float = 0.0
    rerank_score: float | None = None
    token_estimate: int = 0
    citation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestionResult(BaseModel):
    document: SourceDocument
    chunks: list[Chunk] = Field(default_factory=list)
    text: str = ""
    was_duplicate: bool = False


class RetrievalRunRecord(BaseModel):
    query_id: str = Field(default_factory=lambda: str(uuid4()))
    query: str
    collection_id: str | None = None
    strategy_config: dict[str, Any] = Field(default_factory=dict)
    candidate_count: int = 0
    merged_count: int = 0
    reranked_count: int = 0
    kept_evidence_count: int = 0
    token_estimate: int = 0
    latency_ms: int = 0
    evidence_ids: list[str] = Field(default_factory=list)
    trace_steps: list[dict[str, Any]] = Field(default_factory=list)
    drop_reasons: list[dict[str, Any]] = Field(default_factory=list)
    score_snapshots: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
