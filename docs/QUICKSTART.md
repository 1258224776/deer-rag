# Quick Start

## 1. Install

```bash
pip install -e .
```

For local development and tests:

```bash
pip install -e .[dev]
```

## 2. Run the API

```bash
uvicorn app.main:app --reload
```

Default local address:

```text
http://127.0.0.1:8000
```

For local full-stack development on Windows PowerShell, use the helper script from the repo root:

```powershell
.\dev.ps1 -OpenBrowser
```

That starts:
- backend API on `http://127.0.0.1:8010`
- Next.js UI on `http://localhost:3000/collections`

To stop both:

```powershell
.\dev-stop.ps1
```

All `curl` examples below are intentionally written as single-line commands so they paste cleanly in bash, zsh, and PowerShell. On Windows PowerShell, prefer `curl.exe` if `curl` is aliased to `Invoke-WebRequest`.

## 3. Minimal Workflow

### Create a collection

```bash
curl -X POST http://127.0.0.1:8000/collections -H "Content-Type: application/json" -d '{"name":"demo","description":"demo corpus"}'
```

### Ingest text

```bash
curl -X POST http://127.0.0.1:8000/ingest/text -H "Content-Type: application/json" -d '{"collection_id":"<collection-id>","title":"doc-1","text":"hello world","source_uri":"memory://doc-1","source_type":"text"}'
```

### Build indexes

```bash
curl -X POST http://127.0.0.1:8000/indexes/build -H "Content-Type: application/json" -d '{"collection_id":"<collection-id>"}'
```

### Retrieve evidence

```bash
curl -X POST http://127.0.0.1:8000/retrieve -H "Content-Type: application/json" -d '{"query":"hello","collection_id":"<collection-id>","strategy":"hybrid","top_k":5,"rerank":true}'
```

### Assemble context

```bash
curl -X POST http://127.0.0.1:8000/context/assemble -H "Content-Type: application/json" -d '{"evidence":[],"budget":{"total":4000,"reserve":1000,"per_evidence":400},"profile":"agent","merge_adjacent":true,"compression_mode":"extractive"}'
```

Supported context profiles:
- `markdown`
- `plain`
- `agent`

Supported compression modes:
- `none`
- `extractive`

### Run an experiment

```bash
curl -X POST http://127.0.0.1:8000/experiments/run -H "Content-Type: application/json" -d '{"query":"hello","collection_id":"<collection-id>","strategies":["dense","bm25","hybrid"],"top_k":5,"merge_adjacent":true,"compression_mode":"extractive"}'
```

### Compare context-efficiency variants

```bash
curl -X POST http://127.0.0.1:8000/experiments/context-efficiency -H "Content-Type: application/json" -d '{"query":"hello","collection_id":"<collection-id>","strategies":["dense","hybrid"],"top_k":5,"baseline_merge_adjacent":false,"baseline_compression_mode":"none","optimized_merge_adjacent":true,"optimized_compression_mode":"extractive"}'
```

This runs a baseline and an optimized context configuration on the same query, then returns token, latency, and recall deltas per strategy.

### Compare chunk sizes on the same corpus

```bash
curl -X POST http://127.0.0.1:8000/experiments/chunk-size -H "Content-Type: application/json" -d '{"collection_id":"<collection-id>","query":"hello","chunk_sizes":[256,512],"overlap":64,"strategies":["dense","hybrid"],"top_k":5}'
```

This rebuilds temporary chunk variants from stored raw documents and compares retrieval behavior across chunk sizes.

### Run an experiment from YAML config

Example config file:

```yaml
query: "hello"
collection_id: "<collection-id>"
strategies:
  - "dense"
  - "bm25"
  - "hybrid"
top_k: 5
rerank: true
save_artifact: true
artifact_name: "baseline-run"
budget:
  total: 4000
  reserve: 1000
  per_evidence: 400
```

Save it under `data/experiments/baseline.yaml`, then run:

```bash
curl -X POST http://127.0.0.1:8000/experiments/run-config -H "Content-Type: application/json" -d '{"config_path":"data/experiments/baseline.yaml"}'
```

`config_path` must stay within the configured experiments directory. By default, that is `data/experiments/`.

When `save_artifact` is `true`, the response includes `artifact_id` and `artifact_path`.

### List saved experiment artifacts

```bash
curl http://127.0.0.1:8000/experiments/artifacts
```

### Fetch one experiment artifact

```bash
curl http://127.0.0.1:8000/experiments/artifacts/<artifact-id>
```

### Compare saved experiment artifacts

```bash
curl -X POST http://127.0.0.1:8000/experiments/compare -H "Content-Type: application/json" -d '{"artifact_ids":["artifact-a","artifact-b"]}'
```

This returns per-artifact strategy summaries for quick comparison across latency, token usage, selected evidence count, and retrieval metrics.

### Compare summary winners

```bash
curl -X POST http://127.0.0.1:8000/experiments/compare-summary -H "Content-Type: application/json" -d '{"artifact_ids":["artifact-a","artifact-b"]}'
```

This returns the fastest artifact, the most token-efficient artifact, and the best recall artifact for each retrieval strategy.

### Run an offline evaluation dataset

Example dataset format:

```yaml
collection_id: "<collection-id>"
cases:
  - query: "what is the architecture?"
    gold_chunk_ids:
      - "<chunk-id-1>"
      - "<chunk-id-2>"
```

API:

```bash
curl -X POST http://127.0.0.1:8000/evaluation/run-dataset -H "Content-Type: application/json" -d '{"dataset_path":"data/evaluation/sample_dataset.yaml","strategies":["dense","hybrid"],"top_k":5}'
```

CLI:

```bash
python scripts/run_offline_eval.py data/evaluation/sample_dataset.yaml --top-k 5 --strategies dense hybrid
```

## 4. Run Smoke Tests

```bash
python -m pytest tests/test_api_smoke.py
```
