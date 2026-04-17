"use client";

import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Database, LoaderCircle, Plus, RefreshCcw, X } from "lucide-react";

import { CollectionCard } from "@/components/collection-card";
import { type Collection, createCollection, listCollections } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function CollectionsPage() {
  const { t } = useI18n();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [createPending, setCreatePending] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [domain, setDomain] = useState("general");
  const [metadata, setMetadata] = useState("{}");

  async function loadCollections(silent = false) {
    try {
      if (silent) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);
      const items = await listCollections();
      setCollections(items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : t.collectionsPage.loadFailed);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    async function initialLoad() {
      try {
        setLoading(true);
        setError(null);
        const items = await listCollections();
        setCollections(items);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : t.collectionsPage.loadFailed);
      } finally {
        setLoading(false);
      }
    }

    void initialLoad();
  }, [t.collectionsPage.loadFailed]);

  async function handleCreateCollection(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    try {
      setCreatePending(true);
      setError(null);
      const parsedMetadata = metadata.trim() ? (JSON.parse(metadata) as Record<string, unknown>) : {};
      const created = await createCollection({
        name,
        description,
        domain,
        metadata: parsedMetadata,
      });
      setCollections((current) => [created, ...current]);
      setDialogOpen(false);
      setName("");
      setDescription("");
      setDomain("general");
      setMetadata("{}");
    } catch (creationError) {
      setError(creationError instanceof Error ? creationError.message : t.collectionsPage.createFailed);
    } finally {
      setCreatePending(false);
    }
  }

  const sortedCollections = collections
    .slice()
    .sort((left, right) => new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime());

  return (
    <div className="space-y-6">
      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.4fr)_320px]">
        <div className="panel-card p-6">
          <span className="section-label">{t.common.collections}</span>
          <h1 className="mt-3 font-[Bahnschrift,Aptos,sans-serif] text-4xl font-semibold tracking-tight text-[color:var(--ink)]">
            {t.collectionsPage.heading}
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-[color:var(--muted)]">
            {t.collectionsPage.intro}
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Dialog.Root open={dialogOpen} onOpenChange={setDialogOpen}>
              <Dialog.Trigger asChild>
                <button type="button" className="button-primary">
                  <Plus className="size-4" />
                  {t.collectionsPage.newCollection}
                </button>
              </Dialog.Trigger>
              <Dialog.Portal>
                <Dialog.Overlay className="fixed inset-0 bg-black/30 backdrop-blur-sm" />
                <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,680px)] -translate-x-1/2 -translate-y-1/2 rounded-[32px] bg-[color:var(--background-strong)] p-6 shadow-[0_30px_90px_rgba(0,0,0,0.22)] outline-none">
                  <div className="mb-5 flex items-start justify-between gap-4">
                    <div>
                      <Dialog.Title className="font-[Bahnschrift,Aptos,sans-serif] text-3xl font-semibold tracking-tight text-[color:var(--ink)]">
                        {t.collectionsPage.dialogTitle}
                      </Dialog.Title>
                      <Dialog.Description className="mt-2 text-sm leading-6 text-[color:var(--muted)]">
                        {t.collectionsPage.dialogDescription}
                      </Dialog.Description>
                    </div>
                    <Dialog.Close asChild>
                      <button type="button" className="button-ghost">
                        <X className="size-4" />
                      </button>
                    </Dialog.Close>
                  </div>

                  <form className="grid gap-4" onSubmit={handleCreateCollection}>
                    <div className="grid gap-4 md:grid-cols-2">
                      <label className="field-shell">
                        <span className="field-label">{t.common.name}</span>
                        <input value={name} onChange={(event) => setName(event.target.value)} className="field-input" required />
                      </label>
                      <label className="field-shell">
                        <span className="field-label">{t.common.domain}</span>
                        <input value={domain} onChange={(event) => setDomain(event.target.value)} className="field-input" />
                      </label>
                    </div>
                    <label className="field-shell">
                      <span className="field-label">{t.common.description}</span>
                      <textarea
                        value={description}
                        onChange={(event) => setDescription(event.target.value)}
                        className="field-input min-h-28 resize-y"
                      />
                    </label>
                    <label className="field-shell">
                      <span className="field-label">{t.common.metadataJson}</span>
                      <textarea
                        value={metadata}
                        onChange={(event) => setMetadata(event.target.value)}
                        className="field-input min-h-28 resize-y font-[Cascadia_Code,Consolas,monospace] text-xs"
                      />
                    </label>
                    <div className="flex flex-wrap justify-end gap-3">
                      <Dialog.Close asChild>
                        <button type="button" className="button-secondary">
                          {t.common.cancel}
                        </button>
                      </Dialog.Close>
                      <button type="submit" className="button-primary" disabled={createPending}>
                        {createPending ? <LoaderCircle className="size-4 animate-spin" /> : <Plus className="size-4" />}
                        {t.collectionsPage.createAction}
                      </button>
                    </div>
                  </form>
                </Dialog.Content>
              </Dialog.Portal>
            </Dialog.Root>

            <button type="button" className="button-secondary" onClick={() => void loadCollections(true)} disabled={refreshing}>
              {refreshing ? <LoaderCircle className="size-4 animate-spin" /> : <RefreshCcw className="size-4" />}
              {t.common.refreshList}
            </button>
          </div>
        </div>

        <div className="panel-card flex flex-col gap-4 p-6">
          <span className="section-label">{t.common.state}</span>
          <div className="metric-block">
            <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-[color:var(--ink)]">
              <Database className="size-4 text-[color:var(--accent)]" />
              {t.collectionsPage.totalCollections}
            </div>
            <p className="text-4xl font-semibold">{collections.length}</p>
          </div>
          <div className="rounded-[22px] bg-[color:var(--ember-soft)] p-4 text-sm leading-6 text-[color:var(--ember)]">
            {t.collectionsPage.stateTip}
          </div>
        </div>
      </section>

      {error ? <div className="panel-card border-red-200 bg-red-50/80 p-4 text-sm text-red-700">{error}</div> : null}

      {loading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="panel-card h-72 animate-pulse bg-white/70" />
          ))}
        </div>
      ) : sortedCollections.length > 0 ? (
        <div className="grid gap-4 xl:grid-cols-2">
          {sortedCollections.map((collection) => (
            <CollectionCard key={collection.id} collection={collection} />
          ))}
        </div>
      ) : (
        <div className="panel-card p-10 text-center">
          <h2 className="font-[Bahnschrift,Aptos,sans-serif] text-3xl font-semibold text-[color:var(--ink)]">
            {t.collectionsPage.noCollectionsTitle}
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-[color:var(--muted)]">
            {t.collectionsPage.noCollectionsDescription}
          </p>
        </div>
      )}
    </div>
  );
}
