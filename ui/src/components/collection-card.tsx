"use client";

import Link from "next/link";
import { ArrowUpRight, Clock3, FolderSearch, SearchCheck, Upload } from "lucide-react";

import type { Collection } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { formatDateTime, summarizeMetadata } from "@/lib/utils";

type CollectionCardProps = {
  collection: Collection;
};

export function CollectionCard({ collection }: CollectionCardProps) {
  const metadataRows = summarizeMetadata(collection.metadata);
  const { t } = useI18n();

  return (
    <article className="panel-card flex h-full flex-col gap-5 p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="eyebrow-chip">{collection.domain}</span>
            <span className="eyebrow-chip">{collection.id.slice(0, 8)}</span>
          </div>
          <div className="space-y-2">
            <h3 className="font-[Bahnschrift,Aptos,sans-serif] text-2xl font-semibold tracking-tight text-[color:var(--ink)]">
              {collection.name}
            </h3>
            <p className="max-w-[52ch] text-sm leading-6 text-[color:var(--muted)]">
              {collection.description || t.collectionCard.noDescription}
            </p>
          </div>
        </div>
        <div className="rounded-[22px] bg-[color:var(--ember-soft)] px-4 py-3 text-sm font-medium text-[color:var(--ember)]">
          {Object.keys(collection.metadata).length} {t.collectionCard.metadataFields}
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div className="metric-block">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-[color:var(--ink)]">
            <Clock3 className="size-4 text-[color:var(--accent)]" />
            {t.collectionCard.updated}
          </div>
          <p className="text-sm text-[color:var(--muted)]">{formatDateTime(collection.updated_at)}</p>
        </div>
        <div className="metric-block">
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-[color:var(--ink)]">
            <FolderSearch className="size-4 text-[color:var(--accent)]" />
            {t.collectionCard.metadataPreview}
          </div>
          <div className="space-y-1 text-sm text-[color:var(--muted)]">
            {metadataRows.length > 0 ? metadataRows.map((row) => <p key={row}>{row}</p>) : <p>{t.collectionCard.noMetadataStored}</p>}
          </div>
        </div>
      </div>

      <div className="mt-auto flex flex-wrap gap-3">
        <Link href={`/ingest?collection=${collection.id}`} className="button-primary">
          <Upload className="size-4" />
          {t.collectionCard.ingestIntoCollection}
        </Link>
        <Link href={`/search?collection=${collection.id}`} className="button-secondary">
          <SearchCheck className="size-4" />
          {t.collectionCard.searchNow}
        </Link>
        <Link href={`/experiments?collection=${collection.id}`} className="button-ghost">
          {t.collectionCard.inspectExperiments}
          <ArrowUpRight className="size-4" />
        </Link>
      </div>
    </article>
  );
}
