"use client";

import { BarChart3, Clock3, Layers2, Save } from "lucide-react";

import type { ExperimentResult } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { formatMetric } from "@/lib/utils";

type ExperimentTableProps = {
  title: string;
  result: ExperimentResult | null;
  pending: boolean;
  emptyMessage: string;
};

export function ExperimentTable({ title, result, pending, emptyMessage }: ExperimentTableProps) {
  const { t } = useI18n();

  function getCompressionModeLabel(mode: string) {
    if (mode === "extractive") {
      return t.common.compressionModeLabels.extractive;
    }
    if (mode === "abstractive") {
      return t.common.compressionModeLabels.abstractive;
    }
    return t.common.compressionModeLabels.none;
  }

  if (pending) {
    return (
      <div className="panel-card animate-pulse p-5">
        <div className="mb-5 h-4 w-36 rounded-full bg-black/8" />
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-12 rounded-2xl bg-black/8" />
          ))}
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="panel-card p-8 text-center">
        <h3 className="mb-2 font-[Bahnschrift,Aptos,sans-serif] text-2xl font-semibold text-[color:var(--ink)]">
          {title}
        </h3>
        <p className="mx-auto max-w-xl text-sm leading-6 text-[color:var(--muted)]">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="panel-card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[color:var(--border)] px-5 py-4">
        <div>
          <p className="section-label mb-2">{t.experimentTable.snapshot}</p>
          <h3 className="font-[Bahnschrift,Aptos,sans-serif] text-2xl font-semibold tracking-tight text-[color:var(--ink)]">
            {title}
          </h3>
          <p className="mt-2 text-sm text-[color:var(--muted)]">{result.query}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="eyebrow-chip">{result.collection_id}</span>
          {result.artifact_id ? <span className="eyebrow-chip">{t.common.artifact} {result.artifact_id}</span> : null}
        </div>
      </div>

      <div className="grid gap-3 border-b border-[color:var(--border)] px-5 py-4 md:grid-cols-3">
        <div className="metric-block">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-[color:var(--ink)]">
            <BarChart3 className="size-4 text-[color:var(--accent)]" />
            {t.experimentTable.strategies}
          </div>
          <p className="text-2xl font-semibold">{result.strategies.length}</p>
        </div>
        <div className="metric-block">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-[color:var(--ink)]">
            <Layers2 className="size-4 text-[color:var(--accent)]" />
            {t.experimentTable.overlapPairs}
          </div>
          <p className="text-2xl font-semibold">{Object.keys(result.overlap).length}</p>
        </div>
        <div className="metric-block">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-[color:var(--ink)]">
            <Save className="size-4 text-[color:var(--accent)]" />
            {t.experimentTable.artifactSaved}
          </div>
          <p className="text-2xl font-semibold">{result.artifact_id ? t.common.yes : t.common.no}</p>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-black/[0.03] text-[color:var(--muted)]">
            <tr>
              <th className="px-5 py-3 font-medium">{t.experimentTable.strategy}</th>
              <th className="px-5 py-3 font-medium">{t.experimentTable.latency}</th>
              <th className="px-5 py-3 font-medium">{t.experimentTable.candidates}</th>
              <th className="px-5 py-3 font-medium">{t.experimentTable.selected}</th>
              <th className="px-5 py-3 font-medium">{t.experimentTable.tokens}</th>
              <th className="px-5 py-3 font-medium">{t.experimentTable.savings}</th>
              <th className="px-5 py-3 font-medium">{t.experimentTable.recallAtK}</th>
              <th className="px-5 py-3 font-medium">{t.experimentTable.mrr}</th>
            </tr>
          </thead>
          <tbody>
            {result.strategies.map((strategy) => (
              <tr key={strategy.strategy} className="border-t border-[color:var(--border)]">
                <td className="px-5 py-4 align-top">
                  <div className="font-semibold text-[color:var(--ink)]">{strategy.strategy}</div>
                  <div className="mt-1 text-xs text-[color:var(--muted)]">{getCompressionModeLabel(strategy.compression_mode)}</div>
                </td>
                <td className="px-5 py-4 align-top">
                  <div className="flex items-center gap-2 font-medium text-[color:var(--ink)]">
                    <Clock3 className="size-4 text-[color:var(--accent)]" />
                    {strategy.latency_ms} {t.common.milliseconds}
                  </div>
                </td>
                <td className="px-5 py-4 align-top">{strategy.candidate_count}</td>
                <td className="px-5 py-4 align-top">{strategy.selected_count}</td>
                <td className="px-5 py-4 align-top">{strategy.assembled_token_estimate}</td>
                <td className="px-5 py-4 align-top">{strategy.token_savings}</td>
                <td className="px-5 py-4 align-top">{formatMetric(strategy.metrics.recall_at_k)}</td>
                <td className="px-5 py-4 align-top">{formatMetric(strategy.metrics.mrr)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {Object.keys(result.overlap).length > 0 ? (
        <div className="border-t border-[color:var(--border)] px-5 py-4">
          <p className="mb-3 text-sm font-semibold text-[color:var(--ink)]">{t.experimentTable.overlapDiagnostics}</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(result.overlap).map(([pair, value]) => (
              <span key={pair} className="eyebrow-chip">
                {pair}: {formatMetric(value)}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
