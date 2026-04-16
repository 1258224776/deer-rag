# deer-rag

A modular RAG and retrieval optimization system focused on hybrid retrieval, reranking, token-efficient context assembly, and evaluation.

## Overview

`deer-rag` is an independent retrieval infrastructure project.
It is designed as a standalone system for building, optimizing, and evaluating retrieval pipelines over private or domain-specific corpora.

It is not tied to a single agent, a single product, or a single application domain.
It can be used as:
- a standalone retrieval backend
- an evidence service for agent systems
- an experimentation platform for RAG optimization
- a private corpus retrieval system
- a benchmarkable retrieval stack for applied AI products

## What deer-rag Focuses On

`deer-rag` is built around the engineering problems that basic RAG demos usually ignore:
- retrieval quality on long and noisy corpora
- hybrid recall across semantic and lexical signals
- reranking and evidence deduplication
- token-budget-aware context assembly
- offline evaluation and experiment comparison
- citation-ready evidence delivery

The goal is not just to retrieve chunks.
The goal is to build a retrieval system that is measurable, configurable, and useful in real downstream workflows.

## Design Goals

- Improve retrieval quality for complex and domain-specific queries.
- Reduce wasted tokens before evidence reaches a model.
- Make retrieval behavior inspectable, explainable, and debuggable.
- Support reproducible experiments for retrieval tuning.
- Expose clean APIs that can be used by different downstream systems.

## Core Capabilities

### Ingestion
Convert raw materials into normalized retrieval assets.

Supported inputs:
- PDF
- Markdown / TXT / HTML
- scraped webpages
- repository text snapshots
- CSV and semi-structured text files

Responsibilities:
- cleaning
- chunking
- metadata extraction
- deduplication
- collection management
- source versioning

### Multi-Index Retrieval
`deer-rag` is designed around multiple retrieval views over the same corpus.

Recommended index types:
- dense index for semantic retrieval
- BM25 index for lexical retrieval
- metadata index for source/date/type filtering
- optional entity index for company/person/product/time entities

This supports hybrid retrieval instead of vector-only search.

### Retrieval Optimization
The retrieval layer should be modular and experiment-friendly.

Supported or planned strategies:
- dense retrieval
- BM25 retrieval
- hybrid retrieval
- multi-query retrieval
- query rewrite
- metadata filtering
- parent-child retrieval
- MMR deduplication
- rerank

### Context Optimization
The system should optimize for useful evidence, not longer prompts.

Responsibilities:
- token budget planning
- evidence trimming
- adjacent chunk merge
- duplicate removal
- source-preserving compression
- context packing for downstream consumers

### Evaluation Lab
Evaluation is part of the system design, not an afterthought.

Suggested metrics:
- Recall@K
- MRR
- nDCG
- gold evidence hit rate
- citation coverage
- token per useful evidence
- latency / cost / quality comparison

### Evidence API
`deer-rag` should return evidence packs, not plain text blobs.

Recommended fields:
- snippet
- title
- source
- chunk_id
- score
- rerank_score
- token_estimate
- metadata
- citation_id

## Typical Use Cases

- deep research workflows that need citation-ready evidence
- enterprise knowledge retrieval over private corpora
- analyst copilots that require high-recall retrieval
- agent systems that need external evidence providers
- RAG experiments for chunking, reranking, and token budgeting

## Recommended MVP

### Phase 1
- collection management
- file and web ingestion
- chunking
- dense retrieval
- BM25 retrieval
- hybrid retrieval
- rerank
- citation-ready output
- token cost statistics

### Phase 2
- experiment configuration
- retrieval strategy comparison
- chunk strategy comparison
- latency / cost / recall dashboard
- query rewrite

### Phase 3
- metadata filtering
- parent-child retrieval
- evidence compression
- embedding and reranker benchmark
- hard negative mining

### Phase 4
- entity-aware retrieval
- timeline retrieval
- graph-enhanced retrieval
- lightweight domain adaptation

## API Draft

Initial endpoints:
- `POST /collections`
- `GET /collections`
- `POST /ingest/files`
- `POST /ingest/web`
- `POST /retrieve`
- `POST /retrieve/hybrid`
- `POST /retrieve/brief`
- `POST /context/assemble`
- `POST /experiments/run`
- `GET /experiments/{id}`
- `GET /metrics/query/{id}`

## Suggested Stack

- API: FastAPI
- Dense index: FAISS
- Lexical index: BM25
- Parsing: PyMuPDF, trafilatura, BeautifulSoup
- Embeddings: sentence-transformers or OpenAI-compatible embeddings
- Rerank: cross-encoder or ColBERT-style benchmark interface
- Metadata store: SQLite or Postgres
- Config: YAML
- Evaluation artifacts: local experiment store

## Quick Start

See [docs/QUICKSTART.md](./docs/QUICKSTART.md) for:
- installation
- local API startup
- minimal ingestion / indexing / retrieval flow
- smoke tests

## Example Integration: deer-rag + agent-one

`agent-one` is one possible downstream consumer of `deer-rag`.

In that setup:
- `agent-one` handles planning, web search, scraping, orchestration, and report generation.
- `deer-rag` handles corpus ingestion, indexing, retrieval optimization, context packing, and evidence delivery.

One-line relationship in that integration:
- `agent-one` is the researcher.
- `deer-rag` is the evidence engine.

This is an integration example, not the project definition.

## Open-Source Narrative

`deer-rag` is intentionally focused on the retrieval layer of AI systems.

It is meant to demonstrate:
- modular retrieval architecture
- retrieval optimization and evaluation discipline
- token-efficient context assembly
- evidence-oriented system design

## Hiring Value

This project maps well to roles involving:
- RAG systems engineering
- retrieval optimization
- applied AI infrastructure
- evaluation and benchmarking
- LLM product backend development

## Repo Status

This repository is currently in the architecture and scaffold stage.
The current priority is building the retrieval core first, then the optimization and evaluation layers.

## Next Steps

1. Implement collection and ingestion models.
2. Build dense + BM25 hybrid retrieval.
3. Add rerank and MMR deduplication.
4. Add token-budget-aware context assembly.
5. Add experiment runner and offline evaluation.
6. Add integration examples for downstream systems such as `agent-one`.
