"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Beaker, History, LoaderCircle } from "lucide-react";

import { ExperimentTable } from "@/components/experiment-table";
import { SubpageHeader } from "@/components/subpage-header";
import {
  getArtifact,
  getDefaultRetrievalOptions,
  listArtifacts,
  listCollections,
  runExperiment,
  type ArtifactSummary,
  type Collection,
  type ExperimentResult,
} from "@/lib/api";
import { useI18n } from "@/lib/i18n";

function ExperimentsPageContent() {
  const { locale, t } = useI18n();
  const searchParams = useSearchParams();
  const initialCollectionId = searchParams.get("collection") ?? "";
  const backLabel = locale === "zh" ? "返回集合" : "Back to Collections";

  const [collections, setCollections] = useState<Collection[]>([]);
  const [artifacts, setArtifacts] = useState<ArtifactSummary[]>([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState(initialCollectionId);

  const [query, setQuery] = useState("deer-rag 支持哪些检索策略？");
  const [topK, setTopK] = useState(5);
  const [rerank, setRerank] = useState(false);
  const [queryRewrite, setQueryRewrite] = useState(false);
  const [artifactName, setArtifactName] = useState("实验基线");

  const [useDense, setUseDense] = useState(true);
  const [useBm25, setUseBm25] = useState(true);
  const [useHybrid, setUseHybrid] = useState(true);

  const [runPending, setRunPending] = useState(false);
  const [artifactPending, setArtifactPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ExperimentResult | null>(null);
  const [artifactPreview, setArtifactPreview] = useState<ExperimentResult | null>(null);
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setError(null);
        const [collectionItems, artifactItems] = await Promise.all([listCollections(), listArtifacts()]);
        setCollections(collectionItems);
        setArtifacts(artifactItems);
        if (!initialCollectionId && collectionItems.length > 0) {
          setSelectedCollectionId(collectionItems[0].id);
        }
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : t.experimentsPage.loadFailed);
      }
    }

    void load();
  }, [initialCollectionId, t.experimentsPage.loadFailed]);

  async function refreshArtifacts() {
    const items = await listArtifacts();
    setArtifacts(items);
  }

  async function handleRun(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const strategies = [
      useDense ? "dense" : null,
      useBm25 ? "bm25" : null,
      useHybrid ? "hybrid" : null,
    ].filter(Boolean) as Array<"dense" | "bm25" | "hybrid">;

    if (!selectedCollectionId) {
      setError(t.experimentsPage.chooseCollectionBeforeRun);
      return;
    }

    if (strategies.length === 0) {
      setError(t.experimentsPage.selectAtLeastOneStrategy);
      return;
    }

    try {
      setRunPending(true);
      setError(null);
      const experiment = await runExperiment({
        query,
        collection_id: selectedCollectionId,
        strategies,
        top_k: topK,
        rerank,
        save_artifact: true,
        artifact_name: artifactName || undefined,
        merge_adjacent: true,
        compression_mode: "extractive",
        options: getDefaultRetrievalOptions(queryRewrite),
      });
      setResult(experiment);
      setArtifactPreview(null);
      setSelectedArtifactId(experiment.artifact_id);
      await refreshArtifacts();
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : t.experimentsPage.runFailed);
    } finally {
      setRunPending(false);
    }
  }

  async function handleSelectArtifact(artifactId: string) {
    try {
      setArtifactPending(true);
      setError(null);
      setSelectedArtifactId(artifactId);
      const artifact = await getArtifact(artifactId);
      setArtifactPreview(artifact);
    } catch (artifactError) {
      setError(artifactError instanceof Error ? artifactError.message : t.experimentsPage.loadArtifactFailed);
    } finally {
      setArtifactPending(false);
    }
  }

  const sortedArtifacts = artifacts.slice().sort((left, right) => right.artifact_path.localeCompare(left.artifact_path));

  return (
    <div className="space-y-6">
      <SubpageHeader
        label={t.sidebar.nav.experimentsLabel}
        title={t.experimentsPage.heading}
        description={t.experimentsPage.intro}
        backLabel={backLabel}
      >
        <form className="grid gap-4" onSubmit={handleRun}>
          <div className="grid gap-4 xl:grid-cols-[240px_minmax(0,1fr)_120px_220px]">
            <label className="field-shell">
              <span className="field-label">{t.common.collection}</span>
              <select className="field-input" value={selectedCollectionId} onChange={(event) => setSelectedCollectionId(event.target.value)}>
                <option value="">{t.common.selectCollection}</option>
                {collections.map((collection) => (
                  <option key={collection.id} value={collection.id}>
                    {collection.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field-shell">
              <span className="field-label">{t.common.query}</span>
              <input className="field-input" value={query} onChange={(event) => setQuery(event.target.value)} />
            </label>
            <label className="field-shell">
              <span className="field-label">{t.common.topK}</span>
              <input
                type="number"
                min={1}
                className="field-input"
                value={topK}
                onChange={(event) => setTopK(Number(event.target.value))}
              />
            </label>
            <label className="field-shell">
              <span className="field-label">{t.experimentsPage.artifactName}</span>
              <input className="field-input" value={artifactName} onChange={(event) => setArtifactName(event.target.value)} />
            </label>
          </div>

          <div className="flex flex-wrap gap-3">
            <label className="eyebrow-chip cursor-pointer gap-2">
              <input type="checkbox" checked={useDense} onChange={(event) => setUseDense(event.target.checked)} />
              dense
            </label>
            <label className="eyebrow-chip cursor-pointer gap-2">
              <input type="checkbox" checked={useBm25} onChange={(event) => setUseBm25(event.target.checked)} />
              bm25
            </label>
            <label className="eyebrow-chip cursor-pointer gap-2">
              <input type="checkbox" checked={useHybrid} onChange={(event) => setUseHybrid(event.target.checked)} />
              hybrid
            </label>
            <label className="eyebrow-chip cursor-pointer gap-2">
              <input type="checkbox" checked={rerank} onChange={(event) => setRerank(event.target.checked)} />
              {t.common.rerank}
            </label>
            <label className="eyebrow-chip cursor-pointer gap-2">
              <input type="checkbox" checked={queryRewrite} onChange={(event) => setQueryRewrite(event.target.checked)} />
              {t.common.queryRewrite}
            </label>
            <button type="submit" className="button-primary">
              {runPending ? <LoaderCircle className="size-4 animate-spin" /> : <Beaker className="size-4" />}
              {t.experimentsPage.runExperiment}
            </button>
          </div>
        </form>
      </SubpageHeader>

      {error ? <div className="panel-card border-red-200 bg-red-50/80 p-4 text-sm text-red-700">{error}</div> : null}

      <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
        <aside className="panel-card p-5">
          <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-[color:var(--ink)]">
            <History className="size-4 text-[color:var(--accent)]" />
            {t.experimentsPage.artifactHistory}
          </div>
          <div className="space-y-3">
            {sortedArtifacts.length > 0 ? (
              sortedArtifacts.map((artifact) => (
                <button
                  key={artifact.artifact_id}
                  type="button"
                  onClick={() => void handleSelectArtifact(artifact.artifact_id)}
                  className={`w-full rounded-[22px] border px-4 py-3 text-left transition ${
                    selectedArtifactId === artifact.artifact_id
                      ? "border-transparent bg-[color:var(--ink)] text-white"
                      : "border-[color:var(--border)] bg-white/70 text-[color:var(--ink)] hover:border-[color:var(--accent)]"
                  }`}
                >
                  <div className="text-sm font-semibold">{artifact.artifact_id}</div>
                  <div className={`mt-1 text-xs ${selectedArtifactId === artifact.artifact_id ? "text-white/72" : "text-[color:var(--muted)]"}`}>
                    {artifact.artifact_path}
                  </div>
                  <div className={`mt-2 text-xs ${selectedArtifactId === artifact.artifact_id ? "text-white/72" : "text-[color:var(--muted)]"}`}>
                    {artifact.size_bytes} {t.common.bytes}
                  </div>
                </button>
              ))
            ) : (
              <p className="text-sm leading-6 text-[color:var(--muted)]">
                {t.experimentsPage.noArtifacts}
              </p>
            )}
          </div>
        </aside>

        <div className="space-y-6">
          <ExperimentTable
            title={t.experimentsPage.latestRunTitle}
            result={result}
            pending={runPending}
            emptyMessage={t.experimentsPage.latestRunEmpty}
          />
          <ExperimentTable
            title={artifactPending ? t.experimentsPage.selectedArtifactLoading : t.experimentsPage.selectedArtifactTitle}
            result={artifactPreview}
            pending={artifactPending}
            emptyMessage={t.experimentsPage.selectedArtifactEmpty}
          />
        </div>
      </div>
    </div>
  );
}

export default function ExperimentsPage() {
  const { t } = useI18n();
  return (
    <Suspense fallback={<div className="panel-card p-6 text-sm text-[color:var(--muted)]">{t.experimentsPage.preparing}</div>}>
      <ExperimentsPageContent />
    </Suspense>
  );
}
