# Architecture

## System Role

`deer-rag` is a standalone retrieval and evidence service for deep research workloads.
It should be designed as a backend system, not as a prompt wrapper.

## High-Level Architecture

```text
raw sources
  -> ingestion pipeline
  -> normalized documents
  -> chunking + metadata extraction
  -> multi-index build
  -> retrieval pipeline
  -> rerank + dedup
  -> context optimizer
  -> evidence API
  -> downstream agent
```

## Major Components

### Ingestion Pipeline
Inputs:
- local files
- web pages
- scraped markdown
- repository exports

Outputs:
- normalized documents
- source metadata
- chunk records
- collection membership

Key responsibilities:
- parser routing by MIME / extension
- source fingerprinting
- version tracking
- duplicate detection

### Document Model
Recommended entities:
- Collection
- SourceDocument
- Chunk
- RetrievalRun
- ExperimentRun
- EvidencePack

Suggested minimum fields:

#### Collection
- id
- name
- description
- domain
- created_at

#### SourceDocument
- id
- collection_id
- title
- source_uri
- source_type
- checksum
- published_at
- ingested_at
- raw_text_path
- metadata_json

#### Chunk
- id
- document_id
- chunk_index
- text
- token_count
- section_title
- parent_span
- metadata_json

### Multi-Index Layer
Use multiple retrieval views over the same corpus.

Recommended indexes:
- DenseVectorIndex
- BM25Index
- MetadataFilterIndex
- optional EntityIndex

Why:
- dense is good for semantic generalization
- BM25 is good for exact entities and rare terms
- metadata filtering is essential in research workflows
- entity signals improve explainability and domain navigation

### Retrieval Pipeline
Suggested request flow:

1. normalize query
2. optional query rewrite
3. dense recall
4. BM25 recall
5. merge candidates
6. deduplicate by source/span
7. rerank candidates
8. apply metadata filters
9. assemble final evidence pack
10. return token-aware context bundle

### Context Optimizer
This layer is critical for production relevance.

Responsibilities:
- estimate token cost
- remove redundant evidence
- merge adjacent chunks when helpful
- preserve citation traceability
- fit final context into configurable budget

Recommended output modes:
- raw evidence mode
- compressed evidence mode
- agent-ready context mode

### Evaluation Layer
The evaluation layer should support reproducible experiments.

Inputs:
- query set
- expected evidence ids or documents
- retrieval configuration

Outputs:
- Recall@K
- MRR
- nDCG
- average latency
- average token budget usage
- evidence hit diagnostics

### Observability
Borrow the mindset from Langfuse and Helicone, but keep it lightweight.

Track per-query:
- query text
- retrieval strategy
- candidate counts
- rerank delta
- final kept evidence count
- token estimate
- latency
- failure reason

This makes the system debuggable and interview-ready.

## Integration with agent-one

`agent-one` should treat `deer-rag` as one of several evidence providers.

Recommended interaction:
- `agent-one` decides whether local/private knowledge is relevant
- it calls `deer-rag`
- `deer-rag` returns evidence packs with citations
- `agent-one` combines them with web evidence and writes the final report

This separation keeps responsibilities clean:
- `agent-one` owns planning and synthesis
- `deer-rag` owns retrieval quality and evidence packaging

## Recommended Service Boundaries

`deer-rag` owns:
- corpus ingestion
- chunking
- indexing
- retrieval optimization
- rerank
- token-aware context assembly
- experiment runs
- retrieval metrics

`agent-one` owns:
- query planning
- web search
- scraping
- report generation
- final answer synthesis
- multi-source reasoning

## Future Extensions

Near-term:
- entity-aware retrieval
- timeline mode
- source freshness weighting
- collection-level retrieval routing

Later:
- graph-enhanced retrieval
- domain-specific reranker tuning
- query difficulty estimation
- adaptive retrieval policy based on token budget

