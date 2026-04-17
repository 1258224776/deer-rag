"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { LoaderCircle, Search } from "lucide-react";

import { SearchResults } from "@/components/search-results";
import {
  getDefaultRetrievalOptions,
  listCollections,
  retrieve,
  type Collection,
  type RetrieveResponse,
} from "@/lib/api";
import { useI18n } from "@/lib/i18n";

function SearchPageContent() {
  const { t } = useI18n();
  const searchParams = useSearchParams();
  const initialCollectionId = searchParams.get("collection") ?? "";

  const [collections, setCollections] = useState<Collection[]>([]);
  const [loadingCollections, setLoadingCollections] = useState(true);
  const [selectedCollectionId, setSelectedCollectionId] = useState(initialCollectionId);

  const [query, setQuery] = useState("What retrieval strategies does deer-rag support?");
  const [strategy, setStrategy] = useState<"dense" | "bm25" | "hybrid">("hybrid");
  const [topK, setTopK] = useState(5);
  const [rerank, setRerank] = useState(false);
  const [queryRewrite, setQueryRewrite] = useState(false);

  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<RetrieveResponse | null>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoadingCollections(true);
        const items = await listCollections();
        setCollections(items);
        if (!initialCollectionId && items.length > 0) {
          setSelectedCollectionId(items[0].id);
        }
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : t.ingestPage.loadCollectionsFailed);
      } finally {
        setLoadingCollections(false);
      }
    }

    void load();
  }, [initialCollectionId, t.ingestPage.loadCollectionsFailed]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCollectionId) {
      setError(t.searchPage.chooseCollectionBeforeSearch);
      return;
    }

    try {
      setPending(true);
      setError(null);
      const result = await retrieve({
        query,
        collection_id: selectedCollectionId,
        strategy,
        top_k: topK,
        rerank,
        options: getDefaultRetrievalOptions(queryRewrite),
      });
      setResponse(result);
    } catch (searchError) {
      setError(searchError instanceof Error ? searchError.message : t.searchPage.searchFailed);
      setResponse(null);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="panel-card p-6">
        <span className="section-label">{t.sidebar.nav.searchLabel}</span>
        <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-[Bahnschrift,Aptos,sans-serif] text-4xl font-semibold tracking-tight text-[color:var(--ink)]">
              {t.searchPage.heading}
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-[color:var(--muted)]">
              {t.searchPage.intro}
            </p>
          </div>
        </div>

        <form className="mt-6 grid gap-4" onSubmit={handleSubmit}>
          <div className="grid gap-4 xl:grid-cols-[260px_180px_140px_minmax(0,1fr)]">
            <label className="field-shell">
              <span className="field-label">{t.common.collection}</span>
              <select
                className="field-input"
                value={selectedCollectionId}
                onChange={(event) => setSelectedCollectionId(event.target.value)}
                disabled={loadingCollections}
              >
                <option value="">{t.common.selectCollection}</option>
                {collections.map((collection) => (
                  <option key={collection.id} value={collection.id}>
                    {collection.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="field-shell">
              <span className="field-label">{t.common.strategy}</span>
              <select className="field-input" value={strategy} onChange={(event) => setStrategy(event.target.value as typeof strategy)}>
                <option value="dense">dense</option>
                <option value="bm25">bm25</option>
                <option value="hybrid">hybrid</option>
              </select>
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
              <span className="field-label">{t.common.query}</span>
              <input className="field-input" value={query} onChange={(event) => setQuery(event.target.value)} />
            </label>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <label className="eyebrow-chip cursor-pointer gap-2">
              <input type="checkbox" checked={rerank} onChange={(event) => setRerank(event.target.checked)} />
              {t.common.rerank}
            </label>
            <label className="eyebrow-chip cursor-pointer gap-2">
              <input type="checkbox" checked={queryRewrite} onChange={(event) => setQueryRewrite(event.target.checked)} />
              {t.common.queryRewrite}
            </label>
            <button type="submit" className="button-primary">
              {pending ? <LoaderCircle className="size-4 animate-spin" /> : <Search className="size-4" />}
              {t.searchPage.runRetrieval}
            </button>
          </div>
        </form>
      </section>

      <SearchResults response={response} pending={pending} error={error} />
    </div>
  );
}

export default function SearchPage() {
  const { t } = useI18n();
  return (
    <Suspense fallback={<div className="panel-card p-6 text-sm text-[color:var(--muted)]">{t.searchPage.preparing}</div>}>
      <SearchPageContent />
    </Suspense>
  );
}
