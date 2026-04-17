from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.models import Collection, EvidencePack, RetrievalOptions, SourceDocument, TokenBudget


class CollectionCreateRequest(BaseModel):
    name: str
    description: str = ""
    domain: str = "general"
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestTextRequest(BaseModel):
    collection_id: str
    title: str
    text: str
    source_uri: str
    source_type: str = "text"
    raw_text_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestWebRequest(BaseModel):
    collection_id: str
    url: str
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BuildIndexesRequest(BaseModel):
    collection_id: str


class RetrieveRequest(BaseModel):
    query: str
    collection_id: str
    top_k: int = Field(default=8, ge=1)
    strategy: Literal["dense", "bm25", "hybrid"] = "hybrid"
    rerank: bool = False
    candidate_k: int | None = Field(default=None, ge=1)
    options: RetrievalOptions = Field(default_factory=RetrievalOptions)


class BuildIndexesResponse(BaseModel):
    collection_id: str
    chunk_count: int
    dense_indexed: int
    lexical_indexed: int


class RetrieveResponse(BaseModel):
    strategy: str
    reranked: bool
    results: list[EvidencePack]
    metrics: dict[str, Any]


class CollectionListResponse(BaseModel):
    items: list[Collection]


class IngestResultSummary(BaseModel):
    document: SourceDocument
    chunk_count: int
    was_duplicate: bool


class IngestResponse(BaseModel):
    result: IngestResultSummary


class ContextAssembleRequest(BaseModel):
    evidence: list[EvidencePack]
    budget: TokenBudget = Field(default_factory=TokenBudget)
    profile: Literal["markdown", "plain", "agent"] = "markdown"
    merge_adjacent: bool = True
    compression_mode: Literal["none", "extractive", "abstractive"] = "none"


class ContextAssembleResponse(BaseModel):
    context: str
    selected: list[EvidencePack]
    dropped: list[dict[str, Any]]
    metrics: dict[str, Any]


class ExperimentRunRequest(BaseModel):
    query: str
    collection_id: str
    strategies: list[Literal["dense", "bm25", "hybrid"]] = Field(default_factory=lambda: ["dense", "bm25", "hybrid"])
    top_k: int = Field(default=8, ge=1)
    candidate_k: int | None = Field(default=None, ge=1)
    rerank: bool = False
    budget: TokenBudget = Field(default_factory=TokenBudget)
    merge_adjacent: bool = True
    compression_mode: Literal["none", "extractive", "abstractive"] = "none"
    gold_chunk_ids: list[str] = Field(default_factory=list)
    save_artifact: bool = False
    artifact_name: str | None = None
    options: RetrievalOptions = Field(default_factory=RetrievalOptions)


class ExperimentRunConfigRequest(BaseModel):
    config_path: str


class ChunkSizeCompareRequest(BaseModel):
    collection_id: str
    query: str
    chunk_sizes: list[int] = Field(min_length=2)
    overlap: int = 120
    strategies: list[Literal["dense", "bm25", "hybrid"]] = Field(default_factory=lambda: ["dense", "bm25", "hybrid"])
    top_k: int = Field(default=8, ge=1)
    candidate_k: int | None = Field(default=None, ge=1)
    rerank: bool = False
    budget: TokenBudget = Field(default_factory=TokenBudget)
    merge_adjacent: bool = True
    compression_mode: Literal["none", "extractive", "abstractive"] = "none"
    gold_chunk_ids: list[str] = Field(default_factory=list)
    options: RetrievalOptions = Field(default_factory=RetrievalOptions)


class ChunkSizeVariantResult(BaseModel):
    chunk_size: int
    overlap: int
    chunk_count: int
    avg_chunk_tokens: float
    experiment: ExperimentRunResponse | dict[str, Any]


class ChunkSizeCompareResponse(BaseModel):
    collection_id: str
    query: str
    variants: list[ChunkSizeVariantResult]


class ExperimentArtifactSummary(BaseModel):
    artifact_id: str
    artifact_path: str
    size_bytes: int


class ExperimentArtifactListResponse(BaseModel):
    items: list[ExperimentArtifactSummary]


class ExperimentCompareRequest(BaseModel):
    artifact_ids: list[str] = Field(min_length=2)


class ExperimentCompareStrategySummary(BaseModel):
    strategy: Literal["dense", "bm25", "hybrid"]
    latency_ms: int
    token_estimate: int
    assembled_token_estimate: int
    original_token_estimate: int = 0
    token_savings: int = 0
    token_per_evidence: float
    selected_count: int
    merged_count: int = 0
    compression_mode: Literal["none", "extractive", "abstractive"] | str = "none"
    recall_at_k: float | None = None
    mrr: float | None = None


class ExperimentCompareArtifactResult(BaseModel):
    artifact_id: str
    query: str
    collection_id: str
    strategies: list[ExperimentCompareStrategySummary]
    overlap: dict[str, float]


class ExperimentCompareResponse(BaseModel):
    items: list[ExperimentCompareArtifactResult]


class ExperimentCompareWinner(BaseModel):
    artifact_id: str
    strategy: Literal["dense", "bm25", "hybrid"]
    value: float


class ExperimentCompareSummary(BaseModel):
    fastest: list[ExperimentCompareWinner]
    most_token_efficient: list[ExperimentCompareWinner]
    best_recall: list[ExperimentCompareWinner]


class ContextEfficiencyExperimentRequest(BaseModel):
    query: str
    collection_id: str
    strategies: list[Literal["dense", "bm25", "hybrid"]] = Field(default_factory=lambda: ["dense", "bm25", "hybrid"])
    top_k: int = Field(default=8, ge=1)
    candidate_k: int | None = Field(default=None, ge=1)
    rerank: bool = False
    budget: TokenBudget = Field(default_factory=TokenBudget)
    gold_chunk_ids: list[str] = Field(default_factory=list)
    baseline_merge_adjacent: bool = False
    baseline_compression_mode: Literal["none", "extractive", "abstractive"] = "none"
    optimized_merge_adjacent: bool = True
    optimized_compression_mode: Literal["none", "extractive", "abstractive"] = "extractive"
    options: RetrievalOptions = Field(default_factory=RetrievalOptions)


class ContextEfficiencyDelta(BaseModel):
    strategy: Literal["dense", "bm25", "hybrid"]
    assembled_token_delta: int
    token_savings_delta: int
    latency_delta_ms: int
    recall_delta: float | None = None


class ContextEfficiencyExperimentResponse(BaseModel):
    baseline: ExperimentRunResponse
    optimized: ExperimentRunResponse
    deltas: list[ContextEfficiencyDelta]


class EvaluationDatasetRunRequest(BaseModel):
    dataset_path: str
    strategies: list[Literal["dense", "bm25", "hybrid"]] = Field(default_factory=lambda: ["dense", "bm25", "hybrid"])
    top_k: int = Field(default=8, ge=1)
    candidate_k: int | None = Field(default=None, ge=1)
    rerank: bool = False
    budget: TokenBudget = Field(default_factory=TokenBudget)
    merge_adjacent: bool = True
    compression_mode: Literal["none", "extractive", "abstractive"] = "none"
    options: RetrievalOptions = Field(default_factory=RetrievalOptions)


class EvaluationStrategySummary(BaseModel):
    strategy: Literal["dense", "bm25", "hybrid"]
    avg_latency_ms: float | None = None
    avg_token_estimate: float | None = None
    avg_recall_at_k: float | None = None
    avg_mrr: float | None = None
    avg_ndcg_at_k: float | None = None


class EvaluationCaseResult(BaseModel):
    case_index: int
    query: str
    gold_chunk_ids: list[str]
    strategies: list[dict[str, Any]]


class EvaluationDatasetRunResponse(BaseModel):
    collection_id: str
    case_count: int
    summary: list[EvaluationStrategySummary]
    cases: list[EvaluationCaseResult]


class StrategyMetrics(BaseModel):
    recall_at_k: float | None = None
    mrr: float | None = None


class StrategyRunResult(BaseModel):
    strategy: Literal["dense", "bm25", "hybrid"]
    reranked: bool
    candidate_count: int
    result_count: int
    selected_count: int
    dropped_count: int
    latency_ms: int
    token_estimate: int
    assembled_token_estimate: int
    original_token_estimate: int = 0
    token_savings: int = 0
    token_per_evidence: float
    merged_count: int = 0
    compression_mode: Literal["none", "extractive", "abstractive"] | str = "none"
    chunk_ids: list[str]
    result_chunk_ids: list[str] = Field(default_factory=list)
    metrics: StrategyMetrics
    rewritten_queries: list[str] = Field(default_factory=list)
    applied_options: dict[str, Any] = Field(default_factory=dict)


class ExperimentRunResponse(BaseModel):
    query: str
    collection_id: str
    strategies: list[StrategyRunResult]
    overlap: dict[str, float]
    artifact_id: str | None = None
    artifact_path: str | None = None


class EmbeddingBenchmarkRequest(BaseModel):
    dataset_path: str
    embedding_models: list[str] = Field(min_length=2)
    strategies: list[Literal["dense", "hybrid"]] = Field(default_factory=lambda: ["dense", "hybrid"])
    hybrid_rrf_k: int | None = Field(default=None, ge=1)
    top_k: int = Field(default=8, ge=1)
    candidate_k: int | None = Field(default=None, ge=1)
    rerank: bool = False
    budget: TokenBudget = Field(default_factory=TokenBudget)
    merge_adjacent: bool = True
    compression_mode: Literal["none", "extractive", "abstractive"] = "none"
    options: RetrievalOptions = Field(default_factory=RetrievalOptions)


class EmbeddingBenchmarkModelResult(BaseModel):
    model_name: str
    summary: list[EvaluationStrategySummary]


class EmbeddingBenchmarkResponse(BaseModel):
    collection_id: str
    case_count: int
    hybrid_rrf_k: int
    models: list[EmbeddingBenchmarkModelResult]


class RerankerBenchmarkRequest(BaseModel):
    dataset_path: str
    reranker_models: list[str] = Field(min_length=2)
    strategy: Literal["dense", "bm25", "hybrid"] = "hybrid"
    top_k: int = Field(default=8, ge=1)
    candidate_k: int | None = Field(default=None, ge=1)
    budget: TokenBudget = Field(default_factory=TokenBudget)
    merge_adjacent: bool = True
    compression_mode: Literal["none", "extractive", "abstractive"] = "none"
    options: RetrievalOptions = Field(default_factory=RetrievalOptions)


class RerankerBenchmarkModelResult(BaseModel):
    model_name: str
    summary: list[EvaluationStrategySummary]


class RerankerBenchmarkResponse(BaseModel):
    collection_id: str
    case_count: int
    models: list[RerankerBenchmarkModelResult]
