# deer-rag

A modular RAG and retrieval optimization system focused on hybrid retrieval, reranking, token-efficient context assembly, and evaluation.

[中文文档](./README.zh.md)

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

## Current API

Implemented endpoints:
- `GET /health`
- `GET /collections`
- `POST /collections`
- `POST /ingest/text`
- `POST /ingest/files`
- `POST /ingest/web`
- `POST /indexes/build`
- `POST /retrieve` with `strategy = dense | bm25 | hybrid`
- `POST /context/assemble`
- `POST /experiments/run`
- `POST /experiments/context-efficiency`
- `POST /experiments/chunk-size`
- `POST /experiments/run-config`
- `GET /experiments/artifacts`
- `GET /experiments/artifacts/{artifact_id}`
- `POST /experiments/compare`
- `POST /experiments/compare-summary`
- `POST /evaluation/run-dataset`
- `POST /experiments/benchmark/embeddings`
- `POST /experiments/benchmark/rerankers`

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

### Windows one-click launcher

```
start-deer-rag.cmd
```

This starts the FastAPI backend and opens the standalone UI in a browser automatically.

### Manual startup

See [docs/QUICKSTART.md](./docs/QUICKSTART.md) for:
- installation
- local API startup
- minimal ingestion / indexing / retrieval flow
- smoke tests

### Standalone UI

The repository includes a Next.js-based standalone UI at `ui/`.
It supports English and Chinese (switchable in the sidebar) and covers the full workflow:
ingestion, index building, search, and experiment comparison.

To run the UI separately:

```bash
cd ui
npm install
npm run dev
```

The UI connects to the FastAPI backend at `http://localhost:8000` by default.

### Configuration

By default the server runs on built-in defaults.
To use a custom config file, set the environment variable before starting:

```bash
DEER_RAG_CONFIG=path/to/config.yaml uvicorn app.api.app:app --reload
```

If the env var is set and the file does not exist, the server will raise an error rather than silently falling back to defaults.

## Real Mini Eval

The repository includes a real Chinese end-to-end retrieval mini-eval at [data/evaluation/mini-eval-python-venv-zh.yaml](./data/evaluation/mini-eval-python-venv-zh.yaml).

It uses a version-pinned source document:
- Python 3.14 zh-CN docs: `venv --- 创建虚拟环境`
- source URL: `https://docs.python.org/zh-cn/3.14/library/venv.html`

The eval script fetches that page, parses it, ingests it, builds dense + BM25 indexes, resolves gold chunks from chunk indexes, and runs offline evaluation:

```bash
python scripts/run_mini_eval_python_venv_zh.py
```

Current local baseline on this 1-document / 5-query setup:

| setup | dense Recall@5 | dense MRR | bm25 Recall@5 | bm25 MRR | hybrid Recall@5 | hybrid MRR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| query rewrite off | 0.80 | 0.550 | 1.00 | 0.900 | 1.00 | 0.767 |
| query rewrite on | 0.80 | 0.500 | 1.00 | 0.900 | 0.80 | 0.700 |

This is intentionally small. Its purpose is not to claim benchmark completeness, but to prove a real and reproducible `ingest -> build index -> run eval -> inspect metrics` loop with non-placeholder gold evidence.

With the current Chinese default embedding, this slice is still lexical-heavy: `bm25` remains strongest, while `query rewrite` slightly hurts rank quality instead of helping.

## Real Eval Suite

There is also a slice-based suite runner:

```bash
python scripts/run_real_eval_suite.py
```

It currently runs:
- a `lexical` slice over the Python `venv` docs
- a `semantic` slice over the Python design FAQ

Current suite-level findings:
- On the `lexical` slice, `bm25` remains the strongest ranker (`MRR 0.900`), while `dense` improves to `MRR 0.550` under the Chinese default embedding.
- On the `semantic` slice, switching away from the old English embedding removes the pathological dense baseline: `dense MRR` rises from `0.0625` to `0.458`, which makes it competitive with `bm25` (`0.500`) instead of effectively random.
- On the `semantic` slice, lowering `rrf_k` to `10` is still the best setting we measured; the default config now matches that observation.

## Embedding Benchmark

There is also a dedicated embedding benchmark runner:

```bash
python scripts/run_embedding_benchmark_suite.py --hybrid-rrf-k 10
```

Current semantic-slice dense results on the same Chinese conceptual queries:

| model | dense Recall@5 | dense MRR |
| --- | ---: | ---: |
| `sentence-transformers/all-MiniLM-L6-v2` | 0.25 | 0.0625 |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | 0.75 | 0.4375 |
| `BAAI/bge-small-zh-v1.5` | 0.75 | 0.4583 |
| `BAAI/bge-m3` | 0.75 | 0.3958 |

Based on that benchmark, the repository now defaults to:
- dense embedding model: `BAAI/bge-small-zh-v1.5`
- reranker model: `BAAI/bge-reranker-base` (Chinese-aligned, same model family as the embedding model)
- hybrid RRF parameter: `10`

`bge-m3` produced the best hybrid result on the lexical slice, but `bge-small-zh-v1.5` is the best practical default here because it gives the strongest dense result on the semantic Chinese slice while staying relatively light.

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

The ingestion, indexing, retrieval, context optimization, and offline evaluation paths are all implemented.
The repository includes a real Chinese mini-eval, a slice-based eval suite, and an embedding benchmark with evidence-backed default settings.
A standalone Next.js UI with English/Chinese i18n is available and connects to the FastAPI backend.
Config loading now supports a `DEER_RAG_CONFIG` environment variable and raises explicit errors on missing files.

The current gap is not missing endpoints or missing features.
The current gap is benchmark depth: expanding the eval slices to cover more documents, harder query classes, and evidence-backed comparisons for rewrite, rerank, and chunking strategies.

## Next Steps

1. Expand the mini-eval into a multi-document Chinese benchmark with harder query classes.
2. Benchmark query rewrite, rerank, and chunking against the same gold set to establish which options actually help.
3. Add a Chinese-aligned reranker benchmark slice to validate the `bge-reranker-base` default.
4. Improve metadata quality so freshness and timeline retrieval have stronger evaluation evidence.
5. Add harder retrieval cases: multi-hop, negation, time-conditioned, and cross-document reasoning.
6. Pre-compute chunk adjacency and document metadata to move graph expansion cost from query time to index time.
