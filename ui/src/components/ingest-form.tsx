"use client";

import { useState } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import { FileUp, Link2, LoaderCircle, NotebookText } from "lucide-react";

import type { Collection, IngestResponse } from "@/lib/api";
import { ingestFile, ingestText, ingestWeb } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type IngestFormProps = {
  collections: Collection[];
  selectedCollectionId: string;
  onCollectionChange: (collectionId: string) => void;
  onComplete: (response: IngestResponse) => void;
};

export function IngestForm({
  collections,
  selectedCollectionId,
  onCollectionChange,
  onComplete,
}: IngestFormProps) {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState("text");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [textTitle, setTextTitle] = useState("Ops note");
  const [textSourceUri, setTextSourceUri] = useState("memory://ops-note");
  const [textBody, setTextBody] = useState(
    "deer-rag supports collection management, ingestion, index building, search, and experiment history from a single local UI.",
  );
  const [textMetadata, setTextMetadata] = useState('{"lang":"en","source":"ui"}');

  const [urlValue, setUrlValue] = useState("https://docs.python.org/3/library/venv.html");
  const [urlTitle, setUrlTitle] = useState("Python venv");
  const [urlMetadata, setUrlMetadata] = useState('{"lang":"en","source":"web"}');

  const [fileTitle, setFileTitle] = useState("");
  const [fileMetadata, setFileMetadata] = useState("{}");
  const [fileValue, setFileValue] = useState<File | null>(null);

  function parseMetadata(raw: string) {
    if (!raw.trim()) {
      return {};
    }

    try {
      return JSON.parse(raw) as Record<string, unknown>;
    } catch {
      throw new Error(t.common.metadataJsonInvalid);
    }
  }

  async function handleTextSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCollectionId) {
      setError(t.ingestForm.chooseCollectionBeforeIngesting);
      return;
    }

    try {
      setBusy(true);
      setError(null);
      const response = await ingestText({
        collection_id: selectedCollectionId,
        title: textTitle,
        text: textBody,
        source_uri: textSourceUri,
        source_type: "text",
        metadata: parseMetadata(textMetadata),
      });
      onComplete(response);
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : t.ingestForm.textIngestionFailed);
    } finally {
      setBusy(false);
    }
  }

  async function handleWebSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCollectionId) {
      setError(t.ingestForm.chooseCollectionBeforeIngesting);
      return;
    }

    try {
      setBusy(true);
      setError(null);
      const response = await ingestWeb({
        collection_id: selectedCollectionId,
        url: urlValue,
        title: urlTitle || undefined,
        metadata: parseMetadata(urlMetadata),
      });
      onComplete(response);
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : t.ingestForm.webIngestionFailed);
    } finally {
      setBusy(false);
    }
  }

  async function handleFileSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCollectionId) {
      setError(t.ingestForm.chooseCollectionBeforeIngesting);
      return;
    }
    if (!fileValue) {
      setError(t.ingestForm.selectFileFirst);
      return;
    }

    try {
      setBusy(true);
      setError(null);
      const response = await ingestFile({
        collectionId: selectedCollectionId,
        file: fileValue,
        title: fileTitle || undefined,
        metadataJson: JSON.stringify(parseMetadata(fileMetadata)),
      });
      onComplete(response);
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : t.ingestForm.fileIngestionFailed);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel-card p-5">
      <div className="mb-5 grid gap-4 md:grid-cols-[minmax(0,1fr)_220px]">
        <div>
          <p className="section-label mb-2">{t.ingestForm.sectionLabel}</p>
          <h2 className="font-[Bahnschrift,Aptos,sans-serif] text-3xl font-semibold tracking-tight text-[color:var(--ink)]">
            {t.ingestForm.heading}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[color:var(--muted)]">
            {t.ingestForm.intro}
          </p>
        </div>
        <label className="field-shell">
          <span className="field-label">{t.common.targetCollection}</span>
          <select
            value={selectedCollectionId}
            onChange={(event) => onCollectionChange(event.target.value)}
            className="field-input"
          >
            <option value="">{t.common.selectCollection}</option>
            {collections.map((collection) => (
              <option key={collection.id} value={collection.id}>
                {collection.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <Tabs.Root value={activeTab} onValueChange={setActiveTab}>
        <Tabs.List className="mb-5 grid grid-cols-3 gap-2 rounded-[22px] bg-black/4 p-1">
          <Tabs.Trigger
            value="text"
            className="flex items-center justify-center gap-2 rounded-[18px] px-4 py-3 text-sm font-semibold text-[color:var(--muted)] data-[state=active]:bg-white data-[state=active]:text-[color:var(--ink)]"
          >
            <NotebookText className="size-4" />
            {t.ingestForm.textTab}
          </Tabs.Trigger>
          <Tabs.Trigger
            value="web"
            className="flex items-center justify-center gap-2 rounded-[18px] px-4 py-3 text-sm font-semibold text-[color:var(--muted)] data-[state=active]:bg-white data-[state=active]:text-[color:var(--ink)]"
          >
            <Link2 className="size-4" />
            {t.ingestForm.urlTab}
          </Tabs.Trigger>
          <Tabs.Trigger
            value="file"
            className="flex items-center justify-center gap-2 rounded-[18px] px-4 py-3 text-sm font-semibold text-[color:var(--muted)] data-[state=active]:bg-white data-[state=active]:text-[color:var(--ink)]"
          >
            <FileUp className="size-4" />
            {t.ingestForm.fileTab}
          </Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="text">
          <form className="grid gap-4" onSubmit={handleTextSubmit}>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="field-shell">
                <span className="field-label">{t.common.title}</span>
                <input value={textTitle} onChange={(event) => setTextTitle(event.target.value)} className="field-input" />
              </label>
              <label className="field-shell">
                <span className="field-label">{t.common.sourceUri}</span>
                <input value={textSourceUri} onChange={(event) => setTextSourceUri(event.target.value)} className="field-input" />
              </label>
            </div>
            <label className="field-shell">
              <span className="field-label">{t.common.textBody}</span>
              <textarea value={textBody} onChange={(event) => setTextBody(event.target.value)} className="field-input min-h-44 resize-y" />
            </label>
            <label className="field-shell">
              <span className="field-label">{t.common.metadataJson}</span>
              <textarea
                value={textMetadata}
                onChange={(event) => setTextMetadata(event.target.value)}
                className="field-input min-h-28 resize-y font-[Cascadia_Code,Consolas,monospace] text-xs"
              />
            </label>
            <button type="submit" disabled={busy} className="button-primary w-full sm:w-fit">
              {busy ? <LoaderCircle className="size-4 animate-spin" /> : <NotebookText className="size-4" />}
              {t.ingestForm.ingestText}
            </button>
          </form>
        </Tabs.Content>

        <Tabs.Content value="web">
          <form className="grid gap-4" onSubmit={handleWebSubmit}>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="field-shell md:col-span-2">
                <span className="field-label">{t.common.url}</span>
                <input value={urlValue} onChange={(event) => setUrlValue(event.target.value)} className="field-input" />
              </label>
              <label className="field-shell">
                <span className="field-label">{t.ingestForm.optionalTitleOverride}</span>
                <input value={urlTitle} onChange={(event) => setUrlTitle(event.target.value)} className="field-input" />
              </label>
              <label className="field-shell">
                <span className="field-label">{t.common.metadataJson}</span>
                <input
                  value={urlMetadata}
                  onChange={(event) => setUrlMetadata(event.target.value)}
                  className="field-input font-[Cascadia_Code,Consolas,monospace] text-xs"
                />
              </label>
            </div>
            <button type="submit" disabled={busy} className="button-primary w-full sm:w-fit">
              {busy ? <LoaderCircle className="size-4 animate-spin" /> : <Link2 className="size-4" />}
              {t.ingestForm.fetchAndIngestUrl}
            </button>
          </form>
        </Tabs.Content>

        <Tabs.Content value="file">
          <form className="grid gap-4" onSubmit={handleFileSubmit}>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="field-shell">
                <span className="field-label">{t.ingestForm.optionalTitleOverride}</span>
                <input value={fileTitle} onChange={(event) => setFileTitle(event.target.value)} className="field-input" />
              </label>
              <label className="field-shell">
                <span className="field-label">{t.common.metadataJson}</span>
                <input
                  value={fileMetadata}
                  onChange={(event) => setFileMetadata(event.target.value)}
                  className="field-input font-[Cascadia_Code,Consolas,monospace] text-xs"
                />
              </label>
            </div>
            <label className="field-shell">
              <span className="field-label">{t.common.file}</span>
              <input
                type="file"
                onChange={(event) => setFileValue(event.target.files?.[0] ?? null)}
                className="field-input cursor-pointer file:mr-4 file:rounded-full file:border-0 file:bg-[color:var(--accent-soft)] file:px-4 file:py-2 file:text-sm file:font-semibold file:text-[color:var(--accent)]"
              />
            </label>
            <button type="submit" disabled={busy} className="button-primary w-full sm:w-fit">
              {busy ? <LoaderCircle className="size-4 animate-spin" /> : <FileUp className="size-4" />}
              {t.ingestForm.uploadAndIngestFile}
            </button>
          </form>
        </Tabs.Content>
      </Tabs.Root>

      {error ? <div className="mt-5 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
    </div>
  );
}
