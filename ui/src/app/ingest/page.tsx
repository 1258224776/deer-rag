"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Layers3, LoaderCircle, NotebookPen, Wrench } from "lucide-react";

import { IngestForm } from "@/components/ingest-form";
import { SubpageHeader } from "@/components/subpage-header";
import { buildIndexes, type BuildIndexesResponse, type Collection, type IngestResponse, listCollections } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { formatDateTime } from "@/lib/utils";

function IngestPageContent() {
  const { locale, t } = useI18n();
  const searchParams = useSearchParams();
  const initialCollectionId = searchParams.get("collection") ?? "";
  const backLabel = locale === "zh" ? "返回集合" : "Back to Collections";

  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState(initialCollectionId);
  const [loadingCollections, setLoadingCollections] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [lastIngest, setLastIngest] = useState<IngestResponse | null>(null);
  const [buildResult, setBuildResult] = useState<BuildIndexesResponse | null>(null);
  const [buildPending, setBuildPending] = useState(false);
  const [buildError, setBuildError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoadingCollections(true);
        setLoadError(null);
        const items = await listCollections();
        setCollections(items);
        if (!initialCollectionId && items.length > 0) {
          setSelectedCollectionId(items[0].id);
        }
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : t.ingestPage.loadCollectionsFailed);
      } finally {
        setLoadingCollections(false);
      }
    }

    void load();
  }, [initialCollectionId, t.ingestPage.loadCollectionsFailed]);

  async function handleBuildIndexes() {
    if (!selectedCollectionId) {
      setBuildError(t.ingestPage.chooseCollectionFirst);
      return;
    }

    try {
      setBuildPending(true);
      setBuildError(null);
      const response = await buildIndexes(selectedCollectionId);
      setBuildResult(response);
    } catch (error) {
      setBuildError(error instanceof Error ? error.message : t.ingestPage.buildFailed);
    } finally {
      setBuildPending(false);
    }
  }

  return (
    <div className="space-y-6">
      <SubpageHeader
        label={t.sidebar.nav.ingestLabel}
        title={t.ingestForm.heading}
        description={t.ingestForm.intro}
        backLabel={backLabel}
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_360px]">
        <div className="space-y-6">
          {loadingCollections ? (
            <div className="panel-card flex items-center gap-3 p-5 text-sm text-[color:var(--muted)]">
              <LoaderCircle className="size-4 animate-spin" />
              {t.ingestPage.loadingCollections}
            </div>
          ) : collections.length > 0 ? (
            <IngestForm
              collections={collections}
              selectedCollectionId={selectedCollectionId}
              onCollectionChange={setSelectedCollectionId}
              onComplete={(response) => {
                setLastIngest(response);
                setBuildResult(null);
                setBuildError(null);
              }}
            />
          ) : (
            <div className="panel-card p-8">
              <h1 className="font-[Bahnschrift,Aptos,sans-serif] text-3xl font-semibold text-[color:var(--ink)]">
                {t.ingestPage.emptyTitle}
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-[color:var(--muted)]">
                {t.ingestPage.emptyDescription}
              </p>
            </div>
          )}

          {loadError ? <div className="panel-card border-red-200 bg-red-50/80 p-4 text-sm text-red-700">{loadError}</div> : null}
        </div>

        <aside className="space-y-4">
          <div className="panel-card p-5">
            <span className="section-label">{t.common.nextStep}</span>
            <h2 className="mt-3 font-[Bahnschrift,Aptos,sans-serif] text-2xl font-semibold tracking-tight text-[color:var(--ink)]">
              {t.ingestPage.nextStepTitle}
            </h2>
            <p className="mt-3 text-sm leading-6 text-[color:var(--muted)]">
              {t.ingestPage.nextStepDescription}
            </p>
            <button type="button" className="button-primary mt-5 w-full" onClick={() => void handleBuildIndexes()} disabled={buildPending}>
              {buildPending ? <LoaderCircle className="size-4 animate-spin" /> : <Wrench className="size-4" />}
              {t.ingestPage.buildIndexes}
            </button>
            {buildError ? <p className="mt-3 text-sm text-red-700">{buildError}</p> : null}
          </div>

          <div className="panel-card p-5">
            <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-[color:var(--ink)]">
              <NotebookPen className="size-4 text-[color:var(--accent)]" />
              {t.common.latestIngest}
            </div>
            {lastIngest ? (
              <div className="space-y-3 text-sm text-[color:var(--muted)]">
                <p>
                  <span className="font-semibold text-[color:var(--ink)]">{lastIngest.result.document.title}</span>
                </p>
                <p>{lastIngest.result.chunk_count} {t.ingestPage.chunksCreated}</p>
                <p>{t.common.sourceLabel}: {lastIngest.result.document.source_uri}</p>
                <p>{t.common.ingestedLabel}: {formatDateTime(lastIngest.result.document.ingested_at)}</p>
                <p>{lastIngest.result.was_duplicate ? t.ingestPage.duplicateDetected : t.ingestPage.freshStored}</p>
              </div>
            ) : (
              <p className="text-sm leading-6 text-[color:var(--muted)]">
                {t.ingestPage.latestIngestEmpty}
              </p>
            )}
          </div>

          <div className="panel-card p-5">
            <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-[color:var(--ink)]">
              <Layers3 className="size-4 text-[color:var(--ember)]" />
              {t.common.latestBuild}
            </div>
            {buildResult ? (
              <div className="space-y-3 text-sm text-[color:var(--muted)]">
                <p>
                  <span className="font-semibold text-[color:var(--ink)]">{buildResult.collection_id}</span>
                </p>
                <p>{buildResult.chunk_count} {t.ingestPage.chunksAvailable}</p>
                <p>{buildResult.dense_indexed} {t.ingestPage.denseVectorsWritten}</p>
                <p>{buildResult.lexical_indexed} {t.ingestPage.lexicalRowsWritten}</p>
              </div>
            ) : (
              <p className="text-sm leading-6 text-[color:var(--muted)]">
                {t.ingestPage.latestBuildEmpty}
              </p>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

export default function IngestPage() {
  const { t } = useI18n();
  return (
    <Suspense fallback={<div className="panel-card p-6 text-sm text-[color:var(--muted)]">{t.ingestPage.preparing}</div>}>
      <IngestPageContent />
    </Suspense>
  );
}
