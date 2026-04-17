export const apiBaseUrl = process.env.NEXT_PUBLIC_DEER_RAG_API_BASE_URL ?? "http://127.0.0.1:8010";

export type Collection = {
  id: string;
  name: string;
  description: string;
  domain: string;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
};

export type SourceDocument = {
  id: string;
  collection_id: string;
  title: string;
  source_uri: string;
  source_type: string;
  checksum: string;
  published_at: string | null;
  raw_text_path: string | null;
  ingested_at: string;
  metadata: Record<string, unknown>;
};

export type IngestResponse = {
  result: {
    document: SourceDocument;
    chunk_count: number;
    was_duplicate: boolean;
  };
};

export type BuildIndexesResponse = {
  collection_id: string;
  chunk_count: number;
  dense_indexed: number;
  lexical_indexed: number;
};

export type EvidencePack = {
  chunk_id: string;
  document_id: string;
  snippet: string;
  title: string;
  source: string;
  score: number;
  rerank_score: number | null;
  token_estimate: number;
  citation_id: string | null;
  metadata: Record<string, unknown>;
};

export type RetrievalOptions = {
  query_rewrite: boolean;
  metadata_filters: {
    source_types: string[];
    document_metadata: Record<string, unknown>;
    chunk_metadata: Record<string, unknown>;
    published_after: string | null;
    published_before: string | null;
    ingested_after: string | null;
    ingested_before: string | null;
  };
  freshness: {
    enabled: boolean;
    weight: number;
    half_life_days: number;
    date_field: string;
  };
  entity_aware: boolean;
  timeline_mode: boolean;
  timeline_order: "asc" | "desc";
  graph_expansion: {
    enabled: boolean;
    hops: number;
    max_neighbors: number;
    adjacency_weight: number;
    entity_weight: number;
  };
};

export type RetrieveResponse = {
  strategy: "dense" | "bm25" | "hybrid";
  reranked: boolean;
  results: EvidencePack[];
  metrics: Record<string, unknown>;
};

export type StrategyRun = {
  strategy: "dense" | "bm25" | "hybrid";
  reranked: boolean;
  candidate_count: number;
  result_count: number;
  selected_count: number;
  dropped_count: number;
  latency_ms: number;
  token_estimate: number;
  assembled_token_estimate: number;
  original_token_estimate: number;
  token_savings: number;
  token_per_evidence: number;
  merged_count: number;
  compression_mode: string;
  chunk_ids: string[];
  result_chunk_ids: string[];
  metrics: {
    recall_at_k: number | null;
    mrr: number | null;
  };
  rewritten_queries: string[];
  applied_options: Record<string, unknown>;
};

export type ExperimentResult = {
  query: string;
  collection_id: string;
  strategies: StrategyRun[];
  overlap: Record<string, number>;
  artifact_id: string | null;
  artifact_path: string | null;
};

export type ArtifactSummary = {
  artifact_id: string;
  artifact_path: string;
  size_bytes: number;
};

type CollectionListResponse = {
  items: Collection[];
};

type ArtifactListResponse = {
  items: ArtifactSummary[];
};

export function getDefaultRetrievalOptions(queryRewrite = false): RetrievalOptions {
  return {
    query_rewrite: queryRewrite,
    metadata_filters: {
      source_types: [],
      document_metadata: {},
      chunk_metadata: {},
      published_after: null,
      published_before: null,
      ingested_after: null,
      ingested_before: null,
    },
    freshness: {
      enabled: false,
      weight: 0.15,
      half_life_days: 180,
      date_field: "published_at",
    },
    entity_aware: false,
    timeline_mode: false,
    timeline_order: "asc",
    graph_expansion: {
      enabled: false,
      hops: 1,
      max_neighbors: 4,
      adjacency_weight: 0.08,
      entity_weight: 0.05,
    },
  };
}

function normalizeError(detail: unknown) {
  if (typeof detail === "string") {
    return detail;
  }

  if (detail && typeof detail === "object" && "message" in detail && typeof detail.message === "string") {
    return detail.message;
  }

  return "Request failed.";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!(init?.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let detail: unknown = null;

    try {
      detail = await response.json();
    } catch {
      detail = await response.text();
    }

    const message =
      detail && typeof detail === "object" && "detail" in detail
        ? normalizeError((detail as { detail: unknown }).detail)
        : normalizeError(detail);
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function listCollections() {
  const response = await request<CollectionListResponse>("/collections", {
    method: "GET",
  });
  return response.items;
}

export async function createCollection(payload: {
  name: string;
  description: string;
  domain: string;
  metadata: Record<string, unknown>;
}) {
  return request<Collection>("/collections", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function ingestText(payload: {
  collection_id: string;
  title: string;
  text: string;
  source_uri: string;
  source_type: string;
  metadata: Record<string, unknown>;
}) {
  return request<IngestResponse>("/ingest/text", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function ingestWeb(payload: {
  collection_id: string;
  url: string;
  title?: string;
  metadata: Record<string, unknown>;
}) {
  return request<IngestResponse>("/ingest/web", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function ingestFile(payload: {
  collectionId: string;
  file: File;
  title?: string;
  metadataJson?: string;
}) {
  const formData = new FormData();
  formData.set("collection_id", payload.collectionId);
  formData.set("file", payload.file);
  if (payload.title) {
    formData.set("title", payload.title);
  }
  formData.set("metadata_json", payload.metadataJson ?? "{}");

  return request<IngestResponse>("/ingest/files", {
    method: "POST",
    body: formData,
  });
}

export async function buildIndexes(collectionId: string) {
  return request<BuildIndexesResponse>("/indexes/build", {
    method: "POST",
    body: JSON.stringify({ collection_id: collectionId }),
  });
}

export async function retrieve(payload: {
  query: string;
  collection_id: string;
  strategy: "dense" | "bm25" | "hybrid";
  top_k: number;
  rerank: boolean;
  candidate_k?: number;
  options: RetrievalOptions;
}) {
  return request<RetrieveResponse>("/retrieve", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runExperiment(payload: {
  query: string;
  collection_id: string;
  strategies: Array<"dense" | "bm25" | "hybrid">;
  top_k: number;
  rerank: boolean;
  save_artifact: boolean;
  artifact_name?: string;
  merge_adjacent: boolean;
  compression_mode: "none" | "extractive" | "abstractive";
  options: RetrievalOptions;
}) {
  return request<ExperimentResult>("/experiments/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function listArtifacts() {
  const response = await request<ArtifactListResponse>("/experiments/artifacts", {
    method: "GET",
  });
  return response.items;
}

export async function getArtifact(artifactId: string) {
  return request<ExperimentResult>(`/experiments/artifacts/${artifactId}`, {
    method: "GET",
  });
}
