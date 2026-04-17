from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

import httpx
import yaml
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.api.dependencies import (
    get_bm25_retriever,
    get_chunk_size_compare_runner,
    get_config,
    get_context_optimizer,
    get_context_packer,
    get_dense_retriever,
    get_embedding_benchmark_runner,
    get_experiment_artifact_store,
    get_experiment_runner,
    get_hybrid_retriever,
    get_index_registry,
    get_ingestion_service,
    get_offline_evaluation_runner,
    get_reranker,
    get_reranker_benchmark_runner,
    get_retrieval_pipeline,
    get_store,
)
from app.api.schemas import (
    BuildIndexesRequest,
    BuildIndexesResponse,
    ChunkSizeCompareRequest,
    ChunkSizeCompareResponse,
    CollectionCreateRequest,
    CollectionListResponse,
    ContextEfficiencyExperimentRequest,
    ContextEfficiencyExperimentResponse,
    ContextEfficiencyDelta,
    ContextAssembleRequest,
    ContextAssembleResponse,
    EmbeddingBenchmarkRequest,
    EmbeddingBenchmarkResponse,
    ExperimentCompareRequest,
    ExperimentCompareResponse,
    ExperimentCompareSummary,
    ExperimentArtifactListResponse,
    EvaluationDatasetRunRequest,
    EvaluationDatasetRunResponse,
    ExperimentRunConfigRequest,
    ExperimentRunRequest,
    ExperimentRunResponse,
    IngestResultSummary,
    IngestResponse,
    IngestTextRequest,
    IngestWebRequest,
    RerankerBenchmarkRequest,
    RerankerBenchmarkResponse,
    RetrieveRequest,
    RetrieveResponse,
)
from app.core.models import Collection, RetrievalRunRecord
from app.evaluation import load_evaluation_dataset, load_experiment_config
from app.ingestion.parsers import HtmlParser, MarkdownParser, PdfParser, WebParser


router = APIRouter()


def _ensure_collection_exists(collection_id: str) -> None:
    if get_store().get_collection(collection_id) is None:
        raise HTTPException(status_code=404, detail="Collection not found")


def _build_ingest_response(result) -> IngestResponse:
    return IngestResponse(
        result=IngestResultSummary(
            document=result.document,
            chunk_count=len(result.chunks),
            was_duplicate=result.was_duplicate,
        )
    )


def _select_file_parser(filename: str):
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix == "pdf":
        return PdfParser(), "pdf"
    if suffix in {"md", "markdown", "txt"}:
        return MarkdownParser(), "text"
    if suffix in {"html", "htm"}:
        return HtmlParser(), "html"
    raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix or 'unknown'}")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/collections", response_model=CollectionListResponse)
def list_collections() -> CollectionListResponse:
    items = get_store().list_collections()
    return CollectionListResponse(items=items)


@router.post("/collections", response_model=Collection)
def create_collection(payload: CollectionCreateRequest) -> Collection:
    collection = Collection(
        name=payload.name,
        description=payload.description,
        domain=payload.domain,
        metadata=payload.metadata,
    )
    get_store().upsert_collection(collection)
    return collection


@router.post("/ingest/text", response_model=IngestResponse)
def ingest_text(payload: IngestTextRequest) -> IngestResponse:
    _ensure_collection_exists(payload.collection_id)

    result = get_ingestion_service().ingest_text(
        collection_id=payload.collection_id,
        title=payload.title,
        text=payload.text,
        source_uri=payload.source_uri,
        source_type=payload.source_type,
        raw_text_path=payload.raw_text_path,
        metadata=payload.metadata,
    )
    return _build_ingest_response(result)


@router.post("/ingest/files", response_model=IngestResponse)
async def ingest_file(
    collection_id: str = Form(...),
    title: str | None = Form(None),
    metadata_json: str = Form("{}"),
    file: UploadFile = File(...),
) -> IngestResponse:
    _ensure_collection_exists(collection_id)

    parser, source_type = _select_file_parser(file.filename or "")
    raw_bytes = await file.read()
    parsed_text = parser.parse(raw_bytes)

    try:
        metadata = json.loads(metadata_json) if metadata_json else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid metadata_json: {exc.msg}") from exc

    result = get_ingestion_service().ingest_text(
        collection_id=collection_id,
        title=title or file.filename or "uploaded-file",
        text=parsed_text,
        source_uri=file.filename or "uploaded-file",
        source_type=source_type,
        metadata=metadata,
    )
    return _build_ingest_response(result)


@router.post("/ingest/web", response_model=IngestResponse)
def ingest_web(payload: IngestWebRequest) -> IngestResponse:
    _ensure_collection_exists(payload.collection_id)

    try:
        response = httpx.get(payload.url, timeout=15.0, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {exc}") from exc

    parser = WebParser()
    parsed_text = parser.parse(response.text)
    result = get_ingestion_service().ingest_text(
        collection_id=payload.collection_id,
        title=payload.title or payload.url,
        text=parsed_text,
        source_uri=payload.url,
        source_type="web",
        metadata=payload.metadata,
    )
    return _build_ingest_response(result)


@router.post("/indexes/build", response_model=BuildIndexesResponse)
def build_indexes(payload: BuildIndexesRequest) -> BuildIndexesResponse:
    _ensure_collection_exists(payload.collection_id)

    result = get_index_registry().build_collection_indexes(payload.collection_id)
    get_dense_retriever.cache_clear()
    get_bm25_retriever.cache_clear()
    get_hybrid_retriever.cache_clear()
    get_offline_evaluation_runner.cache_clear()
    get_reranker_benchmark_runner.cache_clear()
    get_retrieval_pipeline.cache_clear()
    get_experiment_runner.cache_clear()
    return BuildIndexesResponse(**result)


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve(payload: RetrieveRequest) -> RetrieveResponse:
    _ensure_collection_exists(payload.collection_id)

    started = perf_counter()
    pipeline_result = get_retrieval_pipeline().run(
        query=payload.query,
        collection_id=payload.collection_id,
        strategy=payload.strategy,
        top_k=payload.top_k,
        candidate_k=payload.candidate_k,
        rerank=payload.rerank,
        options=payload.options,
    )
    results = pipeline_result.results
    latency_ms = int((perf_counter() - started) * 1000)
    token_estimate = sum(item.token_estimate for item in results)
    run_record = RetrievalRunRecord(
        query=payload.query,
        collection_id=payload.collection_id,
        strategy_config={
            "strategy": payload.strategy,
            "top_k": payload.top_k,
            "candidate_k": payload.candidate_k,
            "rerank": payload.rerank,
            "options": payload.options.model_dump(),
        },
        candidate_count=len(pipeline_result.candidates),
        reranked_count=len(results) if pipeline_result.reranked else 0,
        kept_evidence_count=len(results),
        token_estimate=token_estimate,
        latency_ms=latency_ms,
        evidence_ids=[item.chunk_id for item in results],
        trace_steps=[
            *pipeline_result.trace_steps,
            {"step": "rerank", "enabled": pipeline_result.reranked, "count": len(results)},
        ],
    )
    get_store().log_retrieval_run(run_record)

    return RetrieveResponse(
        strategy=payload.strategy,
        reranked=pipeline_result.reranked,
        results=results,
        metrics={
            "latency_ms": latency_ms,
            "result_count": len(results),
            "token_estimate": token_estimate,
            "rewritten_queries": pipeline_result.rewritten_queries,
            "applied_options": payload.options.model_dump(),
            **pipeline_result.diagnostics,
        },
    )


@router.post("/context/assemble", response_model=ContextAssembleResponse)
def assemble_context(payload: ContextAssembleRequest) -> ContextAssembleResponse:
    optimization = get_context_optimizer().optimize(
        payload.evidence,
        payload.budget,
        merge_adjacent=payload.merge_adjacent,
        compression_mode=payload.compression_mode,
    )
    context = get_context_packer().pack(optimization.selected, profile=payload.profile)
    return ContextAssembleResponse(
        context=context,
        selected=optimization.selected,
        dropped=optimization.dropped,
        metrics={
            "selected_count": len(optimization.selected),
            "dropped_count": len(optimization.dropped),
            "token_estimate": optimization.token_estimate,
            "original_token_estimate": optimization.original_token_estimate,
            "token_savings": optimization.token_savings,
            "available_budget": optimization.available_budget,
            "merged_count": optimization.merged_count,
            "compression_mode": optimization.compression_mode,
            "merge_adjacent": payload.merge_adjacent,
            "profile": payload.profile,
        },
    )


@router.post("/experiments/run", response_model=ExperimentRunResponse)
def run_experiment(payload: ExperimentRunRequest) -> ExperimentRunResponse:
    _ensure_collection_exists(payload.collection_id)

    result = get_experiment_runner().run(
        query=payload.query,
        collection_id=payload.collection_id,
        strategies=list(payload.strategies),
        top_k=payload.top_k,
        candidate_k=payload.candidate_k,
        rerank=payload.rerank,
        budget=payload.budget,
        merge_adjacent=payload.merge_adjacent,
        compression_mode=payload.compression_mode,
        gold_chunk_ids=payload.gold_chunk_ids,
        save_artifact=payload.save_artifact,
        artifact_name=payload.artifact_name,
        options=payload.options,
    )
    return ExperimentRunResponse(**result)


@router.post("/experiments/context-efficiency", response_model=ContextEfficiencyExperimentResponse)
def run_context_efficiency_experiment(payload: ContextEfficiencyExperimentRequest) -> ContextEfficiencyExperimentResponse:
    _ensure_collection_exists(payload.collection_id)

    runner = get_experiment_runner()
    baseline = runner.run(
        query=payload.query,
        collection_id=payload.collection_id,
        strategies=list(payload.strategies),
        top_k=payload.top_k,
        candidate_k=payload.candidate_k,
        rerank=payload.rerank,
        budget=payload.budget,
        merge_adjacent=payload.baseline_merge_adjacent,
        compression_mode=payload.baseline_compression_mode,
        gold_chunk_ids=payload.gold_chunk_ids,
        options=payload.options,
    )
    optimized = runner.run(
        query=payload.query,
        collection_id=payload.collection_id,
        strategies=list(payload.strategies),
        top_k=payload.top_k,
        candidate_k=payload.candidate_k,
        rerank=payload.rerank,
        budget=payload.budget,
        merge_adjacent=payload.optimized_merge_adjacent,
        compression_mode=payload.optimized_compression_mode,
        gold_chunk_ids=payload.gold_chunk_ids,
        options=payload.options,
    )

    baseline_by_strategy = {item["strategy"]: item for item in baseline["strategies"]}
    optimized_by_strategy = {item["strategy"]: item for item in optimized["strategies"]}
    deltas: list[ContextEfficiencyDelta] = []

    for strategy in payload.strategies:
        if strategy not in baseline_by_strategy or strategy not in optimized_by_strategy:
            continue
        base_item = baseline_by_strategy[strategy]
        opt_item = optimized_by_strategy[strategy]
        base_recall = base_item.get("metrics", {}).get("recall_at_k")
        opt_recall = opt_item.get("metrics", {}).get("recall_at_k")
        deltas.append(
            ContextEfficiencyDelta(
                strategy=strategy,
                assembled_token_delta=opt_item.get("assembled_token_estimate", 0) - base_item.get("assembled_token_estimate", 0),
                token_savings_delta=opt_item.get("token_savings", 0) - base_item.get("token_savings", 0),
                latency_delta_ms=opt_item.get("latency_ms", 0) - base_item.get("latency_ms", 0),
                recall_delta=(opt_recall - base_recall) if opt_recall is not None and base_recall is not None else None,
            )
        )

    return ContextEfficiencyExperimentResponse(
        baseline=ExperimentRunResponse(**baseline),
        optimized=ExperimentRunResponse(**optimized),
        deltas=deltas,
    )


@router.post("/experiments/chunk-size", response_model=ChunkSizeCompareResponse)
def run_chunk_size_compare(payload: ChunkSizeCompareRequest) -> ChunkSizeCompareResponse:
    _ensure_collection_exists(payload.collection_id)
    result = get_chunk_size_compare_runner().run(
        collection_id=payload.collection_id,
        query=payload.query,
        chunk_sizes=list(payload.chunk_sizes),
        overlap=payload.overlap,
        strategies=list(payload.strategies),
        top_k=payload.top_k,
        candidate_k=payload.candidate_k,
        rerank=payload.rerank,
        budget=payload.budget,
        merge_adjacent=payload.merge_adjacent,
        compression_mode=payload.compression_mode,
        gold_chunk_ids=payload.gold_chunk_ids,
        options=payload.options,
    )
    return ChunkSizeCompareResponse(**result)


@router.post("/experiments/run-config", response_model=ExperimentRunResponse)
def run_experiment_config(payload: ExperimentRunConfigRequest) -> ExperimentRunResponse:
    try:
        config = load_experiment_config(
            payload.config_path,
            allowed_dir=Path(get_config().paths.experiments_dir),
        )
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    request = ExperimentRunRequest.model_validate(config)
    return run_experiment(request)


@router.get("/experiments/artifacts", response_model=ExperimentArtifactListResponse)
def list_experiment_artifacts() -> ExperimentArtifactListResponse:
    return ExperimentArtifactListResponse(items=get_experiment_artifact_store().list())


@router.get("/experiments/artifacts/{artifact_id}")
def get_experiment_artifact(artifact_id: str) -> dict:
    try:
        return get_experiment_artifact_store().get(artifact_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/experiments/compare", response_model=ExperimentCompareResponse)
def compare_experiment_artifacts(payload: ExperimentCompareRequest) -> ExperimentCompareResponse:
    items: list[dict] = []
    store = get_experiment_artifact_store()

    for artifact_id in payload.artifact_ids:
        try:
            artifact = store.get(artifact_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        strategies = []
        for strategy_run in artifact.get("strategies", []):
            metrics = strategy_run.get("metrics", {})
            strategies.append(
                {
                    "strategy": strategy_run.get("strategy", "dense"),
                    "latency_ms": strategy_run.get("latency_ms", 0),
                    "token_estimate": strategy_run.get("token_estimate", 0),
                    "assembled_token_estimate": strategy_run.get("assembled_token_estimate", 0),
                    "original_token_estimate": strategy_run.get("original_token_estimate", 0),
                    "token_savings": strategy_run.get("token_savings", 0),
                    "token_per_evidence": strategy_run.get("token_per_evidence", 0.0),
                    "selected_count": strategy_run.get("selected_count", 0),
                    "merged_count": strategy_run.get("merged_count", 0),
                    "compression_mode": strategy_run.get("compression_mode", "none"),
                    "recall_at_k": metrics.get("recall_at_k"),
                    "mrr": metrics.get("mrr"),
                }
            )

        items.append(
            {
                "artifact_id": artifact.get("artifact_id", artifact_id),
                "query": artifact.get("query", ""),
                "collection_id": artifact.get("collection_id", ""),
                "strategies": strategies,
                "overlap": artifact.get("overlap", {}),
            }
        )

    return ExperimentCompareResponse(items=items)


@router.post("/experiments/compare-summary", response_model=ExperimentCompareSummary)
def compare_experiment_artifact_summary(payload: ExperimentCompareRequest) -> ExperimentCompareSummary:
    compare_result = compare_experiment_artifacts(payload)

    fastest: list[dict] = []
    most_token_efficient: list[dict] = []
    best_recall: list[dict] = []
    strategies = ("dense", "bm25", "hybrid")

    for strategy in strategies:
        strategy_rows = []
        for item in compare_result.items:
            for strategy_run in item.strategies:
                if strategy_run.strategy == strategy:
                    strategy_rows.append((item.artifact_id, strategy_run))

        if not strategy_rows:
            continue

        fastest_id, fastest_run = min(strategy_rows, key=lambda entry: entry[1].latency_ms)
        fastest.append(
            {
                "artifact_id": fastest_id,
                "strategy": strategy,
                "value": float(fastest_run.latency_ms),
            }
        )

        token_id, token_run = max(strategy_rows, key=lambda entry: entry[1].token_savings)
        most_token_efficient.append(
            {
                "artifact_id": token_id,
                "strategy": strategy,
                "value": float(token_run.token_savings),
            }
        )

        recall_rows = [entry for entry in strategy_rows if entry[1].recall_at_k is not None]
        if recall_rows:
            recall_id, recall_run = max(recall_rows, key=lambda entry: entry[1].recall_at_k or 0.0)
            best_recall.append(
                {
                    "artifact_id": recall_id,
                    "strategy": strategy,
                    "value": float(recall_run.recall_at_k or 0.0),
                }
            )

    return ExperimentCompareSummary(
        fastest=fastest,
        most_token_efficient=most_token_efficient,
        best_recall=best_recall,
    )


@router.post("/evaluation/run-dataset", response_model=EvaluationDatasetRunResponse)
def run_evaluation_dataset(payload: EvaluationDatasetRunRequest) -> EvaluationDatasetRunResponse:
    try:
        dataset = load_evaluation_dataset(
            payload.dataset_path,
            allowed_dir=Path(get_config().paths.evaluation_dir),
        )
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _ensure_collection_exists(dataset.collection_id)
    result = get_offline_evaluation_runner().run_dataset(
        dataset,
        strategies=list(payload.strategies),
        top_k=payload.top_k,
        candidate_k=payload.candidate_k,
        rerank=payload.rerank,
        budget=payload.budget,
        merge_adjacent=payload.merge_adjacent,
        compression_mode=payload.compression_mode,
        options=payload.options,
    )
    return EvaluationDatasetRunResponse(**result)


@router.post("/experiments/benchmark/embeddings", response_model=EmbeddingBenchmarkResponse)
def run_embedding_benchmark(payload: EmbeddingBenchmarkRequest) -> EmbeddingBenchmarkResponse:
    try:
        dataset = load_evaluation_dataset(
            payload.dataset_path,
            allowed_dir=Path(get_config().paths.evaluation_dir),
        )
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _ensure_collection_exists(dataset.collection_id)
    result = get_embedding_benchmark_runner().run_dataset(
        dataset,
        embedding_models=list(payload.embedding_models),
        strategies=list(payload.strategies),
        hybrid_rrf_k=payload.hybrid_rrf_k,
        top_k=payload.top_k,
        candidate_k=payload.candidate_k,
        rerank=payload.rerank,
        budget=payload.budget,
        merge_adjacent=payload.merge_adjacent,
        compression_mode=payload.compression_mode,
        options=payload.options,
    )
    return EmbeddingBenchmarkResponse(**result)


@router.post("/experiments/benchmark/rerankers", response_model=RerankerBenchmarkResponse)
def run_reranker_benchmark(payload: RerankerBenchmarkRequest) -> RerankerBenchmarkResponse:
    try:
        dataset = load_evaluation_dataset(
            payload.dataset_path,
            allowed_dir=Path(get_config().paths.evaluation_dir),
        )
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _ensure_collection_exists(dataset.collection_id)
    result = get_reranker_benchmark_runner().run_dataset(
        dataset,
        reranker_models=list(payload.reranker_models),
        strategy=payload.strategy,
        top_k=payload.top_k,
        candidate_k=payload.candidate_k,
        budget=payload.budget,
        merge_adjacent=payload.merge_adjacent,
        compression_mode=payload.compression_mode,
        options=payload.options,
    )
    return RerankerBenchmarkResponse(**result)
