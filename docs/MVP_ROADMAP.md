# MVP Roadmap

## Phase 1: Retrieval Core
Goal: make `deer-rag` useful as a standalone service.

Deliverables:
- collection CRUD
- document ingestion for files and webpages
- chunking pipeline
- dense retrieval
- BM25 retrieval
- hybrid retrieval
- rerank interface
- citation-ready evidence response
- token usage estimation

Success criteria:
- can ingest a collection and retrieve relevant evidence through HTTP
- can compare dense vs BM25 vs hybrid on the same query
- can return source-linked evidence packs

## Phase 2: Optimization Layer
Goal: show engineering depth beyond basic RAG.

Deliverables:
- experiment config files
- retrieval strategy comparison runner
- chunk-size comparison runner
- top-k and rerank ablation
- query rewrite option
- simple experiment report output

Success criteria:
- can run reproducible experiments
- can compare recall, latency, and token cost across strategies

## Phase 3: Context Efficiency
Goal: optimize downstream LLM usage.

Deliverables:
- token budget planner
- evidence deduplication
- adjacent chunk merge
- context compression mode
- final context packing profiles

Success criteria:
- can reduce context size while preserving useful evidence
- can report token savings clearly

## Phase 4: Evaluation and Benchmarking
Goal: turn the project into a retrieval lab.

Deliverables:
- offline evaluation dataset format
- Recall@K / MRR / nDCG metrics
- gold evidence hit reporting
- embedding benchmark
- reranker benchmark

Success criteria:
- can justify retrieval choices with measurable results
- can show benchmark outputs in docs or dashboard

## Phase 5: Research-Specific Retrieval
Goal: move from generic RAG toward deep research relevance.

Deliverables:
- metadata-aware retrieval
- source freshness weighting
- entity-aware retrieval
- timeline-oriented retrieval mode
- lightweight graph expansion experiments

Success criteria:
- supports research-style questions better than generic top-k retrieval
- improves explainability for evidence selection

