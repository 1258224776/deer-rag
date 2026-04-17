"use client";

import { Activity, Link2, SearchSlash, Sigma, Timer } from "lucide-react";

import type { RetrieveResponse } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { formatMetric } from "@/lib/utils";

type SearchResultsProps = {
  response: RetrieveResponse | null;
  pending: boolean;
  error: string | null;
};

export function SearchResults({ response, pending, error }: SearchResultsProps) {
  const { t } = useI18n();
  if (pending) {
    return (
      <div className="grid gap-4 lg:grid-cols-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="panel-card animate-pulse p-5">
            <div className="mb-4 h-4 w-24 rounded-full bg-black/8" />
            <div className="space-y-3">
              <div className="h-4 rounded-full bg-black/8" />
              <div className="h-4 w-4/5 rounded-full bg-black/8" />
              <div className="h-4 w-2/3 rounded-full bg-black/8" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel-card border-red-200 bg-red-50/80 p-5 text-sm text-red-700">
        {error}
      </div>
    );
  }

  if (!response) {
    return (
      <div className="panel-card p-8 text-center">
        <div className="mx-auto mb-4 inline-flex size-14 items-center justify-center rounded-full bg-[color:var(--accent-soft)] text-[color:var(--accent)]">
          <SearchSlash className="size-6" />
        </div>
        <h3 className="mb-2 font-[Bahnschrift,Aptos,sans-serif] text-2xl font-semibold text-[color:var(--ink)]">
          {t.searchResults.firstQueryTitle}
        </h3>
        <p className="mx-auto max-w-xl text-sm leading-6 text-[color:var(--muted)]">
          {t.searchResults.firstQueryDescription}
        </p>
      </div>
    );
  }

  const rewrittenQueries = Array.isArray(response.metrics.rewritten_queries)
    ? (response.metrics.rewritten_queries as string[])
    : [];

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-3">
        <div className="metric-block">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-[color:var(--ink)]">
            <Timer className="size-4 text-[color:var(--accent)]" />
            {t.searchResults.latency}
          </div>
          <p className="text-2xl font-semibold">{response.metrics.latency_ms as number} ms</p>
        </div>
        <div className="metric-block">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-[color:var(--ink)]">
            <Activity className="size-4 text-[color:var(--accent)]" />
            {t.searchResults.resultCount}
          </div>
          <p className="text-2xl font-semibold">{response.metrics.result_count as number}</p>
        </div>
        <div className="metric-block">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-[color:var(--ink)]">
            <Sigma className="size-4 text-[color:var(--accent)]" />
            {t.searchResults.tokenEstimate}
          </div>
          <p className="text-2xl font-semibold">{response.metrics.token_estimate as number}</p>
        </div>
      </div>

      {rewrittenQueries.length > 0 ? (
        <div className="panel-card p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-[color:var(--ink)]">
            <Link2 className="size-4 text-[color:var(--ember)]" />
            {t.searchResults.queryVariants}
          </div>
          <div className="flex flex-wrap gap-2">
            {rewrittenQueries.map((query) => (
              <span key={query} className="eyebrow-chip">
                {query}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        {response.results.length > 0 ? (
          response.results.map((result) => {
            const rrfSources = Array.isArray(result.metadata.rrf_sources) ? (result.metadata.rrf_sources as string[]) : [];

            return (
              <article key={result.chunk_id} className="panel-card flex flex-col gap-4 p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-2">
                    <span className="eyebrow-chip">{result.title || t.searchResults.untitledChunk}</span>
                    <h3 className="font-[Bahnschrift,Aptos,sans-serif] text-xl font-semibold tracking-tight text-[color:var(--ink)]">
                      {result.source || result.document_id}
                    </h3>
                  </div>
                  <div className="rounded-full bg-[color:var(--accent-soft)] px-3 py-2 text-sm font-semibold text-[color:var(--accent)]">
                    {t.searchResults.score} {formatMetric(result.score, 3)}
                  </div>
                </div>
                <p className="text-sm leading-7 text-[color:var(--muted)]">{result.snippet}</p>
                <div className="flex flex-wrap gap-2 text-xs text-[color:var(--muted)]">
                  <span className="eyebrow-chip">{t.searchResults.chunk} {result.chunk_id.slice(0, 8)}</span>
                  <span className="eyebrow-chip">{result.token_estimate} {t.searchResults.tokens}</span>
                  {result.rerank_score !== null ? <span className="eyebrow-chip">{t.common.rerank} {formatMetric(result.rerank_score, 3)}</span> : null}
                  {rrfSources.map((source) => (
                    <span key={source} className="eyebrow-chip">
                      {source}
                    </span>
                  ))}
                </div>
              </article>
            );
          })
        ) : (
          <div className="panel-card p-8 text-center xl:col-span-2">
            <h3 className="mb-2 font-[Bahnschrift,Aptos,sans-serif] text-2xl font-semibold text-[color:var(--ink)]">
              {t.searchResults.noHitsTitle}
            </h3>
            <p className="text-sm leading-6 text-[color:var(--muted)]">
              {t.searchResults.noHitsDescription}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
