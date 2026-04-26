"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type Locale = "en" | "zh";

const STORAGE_KEY = "deer-rag-ui-locale";

const messages = {
  en: {
    common: {
      loading: "Loading...",
      cancel: "Cancel",
      collection: "Collection",
      collections: "Collections",
      query: "Query",
      topK: "Top K",
      strategy: "Strategy",
      description: "Description",
      domain: "Domain",
      name: "Name",
      metadataJson: "Metadata JSON",
      title: "Title",
      sourceUri: "Source URI",
      textBody: "Text body",
      url: "URL",
      file: "File",
      targetCollection: "Target collection",
      selectCollection: "Select a collection",
      latestIngest: "Latest ingest",
      latestBuild: "Latest build",
      nextStep: "Next step",
      sourceLabel: "Source",
      ingestedLabel: "Ingested at",
      yes: "Yes",
      no: "No",
      artifact: "Artifact",
      state: "State",
      refreshList: "Refresh list",
      queryRewrite: "Query rewrite",
      rerank: "Rerank",
      preparing: "Preparing...",
      metadataJsonInvalid: "Metadata must be valid JSON.",
      bytes: "bytes",
      milliseconds: "ms",
      compressionModeLabels: {
        none: "No compression",
        extractive: "Extractive compression",
        abstractive: "Abstractive compression",
      },
    },
    sidebar: {
      badge: "Standalone retrieval UI",
      description: "One surface for corpus setup, ingestion, retrieval diagnostics, and experiment history.",
      apiTarget: "Local API target",
      footer: "Keep the FastAPI server running separately. This shell only speaks HTTP to deer-rag.",
      language: "Language",
      english: "EN",
      chinese: "中文",
      nav: {
        collectionsLabel: "Collections",
        collectionsDescription: "Create and inspect corpora",
        ingestLabel: "Ingest",
        ingestDescription: "Send text, URLs, and files",
        searchLabel: "Search",
        searchDescription: "Run dense, BM25, and hybrid retrieval",
        experimentsLabel: "Experiments",
        experimentsDescription: "Compare strategies and artifacts",
      },
    },
    collectionsPage: {
      heading: "Corpus control room",
      intro:
        "Create logical collections before ingestion. Every later action in the UI is anchored to one collection ID, so this page is where the operational flow begins.",
      newCollection: "New collection",
      dialogTitle: "Create collection",
      dialogDescription:
        "Keep the first version simple. Name the corpus, describe what goes in it, and add only metadata you will actually filter on later.",
      totalCollections: "Total collections",
      stateTip:
        "Collections are lightweight. Create a focused corpus per experiment or per downstream product instead of overloading a single catch-all collection.",
      noCollectionsTitle: "No collections yet",
      noCollectionsDescription: "Create one collection first, then move to the Ingest page to add documents and build indexes.",
      createFailed: "Failed to create collection.",
      loadFailed: "Failed to load collections.",
      createAction: "Create collection",
    },
    collectionCard: {
      noDescription: "No description yet. This collection is ready for ingestion and retrieval.",
      metadataFields: "metadata fields",
      updated: "Updated",
      metadataPreview: "Metadata preview",
      noMetadataStored: "No metadata stored yet.",
      ingestIntoCollection: "Ingest into this collection",
      searchNow: "Search it now",
      inspectExperiments: "Inspect experiments",
    },
    ingestPage: {
      loadingCollections: "Loading collections...",
      emptyTitle: "Start from Collections first",
      emptyDescription:
        "This page needs an existing collection. Create one in the Collections view, then come back to push text, URLs, or files into it.",
      nextStepTitle: "Build indexes explicitly",
      nextStepDescription:
        "Ingestion stores raw documents and chunks. Retrieval will not work until the dense and BM25 indexes are rebuilt for the target collection.",
      buildIndexes: "Build indexes",
      chooseCollectionFirst: "Choose a collection first.",
      buildFailed: "Failed to build indexes.",
      duplicateDetected: "Duplicate document detected.",
      freshStored: "Fresh document stored.",
      latestIngestEmpty: "Submit any of the forms on the left. The document summary will appear here immediately after ingestion.",
      latestBuildEmpty:
        "Once indexes are built, this panel will confirm chunk count and the number of dense / lexical entries written.",
      loadCollectionsFailed: "Failed to load collections.",
      preparing: "Preparing ingest workspace...",
      chunksCreated: "chunks created",
      chunksAvailable: "chunks available",
      denseVectorsWritten: "dense vectors written",
      lexicalRowsWritten: "BM25 rows written",
    },
    ingestForm: {
      sectionLabel: "Ingestion workflow",
      heading: "Add corpus material",
      intro: "Text is fastest for a first pass, URLs prove the fetch-and-parse path, and files validate ingestion for local artifacts.",
      textTab: "Text",
      urlTab: "URL",
      fileTab: "File",
      optionalTitleOverride: "Optional title override",
      chooseCollectionBeforeIngesting: "Choose a collection before ingesting.",
      textIngestionFailed: "Text ingestion failed.",
      webIngestionFailed: "Web ingestion failed.",
      fileIngestionFailed: "File ingestion failed.",
      selectFileFirst: "Select a file first.",
      ingestText: "Ingest text",
      fetchAndIngestUrl: "Fetch and ingest URL",
      uploadAndIngestFile: "Upload and ingest file",
    },
    searchPage: {
      heading: "Inspect retrieval behavior",
      intro:
        "This page is intentionally diagnostic. You see snippets, raw scores, rewrite variants, and the retrieval strategy that produced them.",
      chooseCollectionBeforeSearch: "Choose a collection before running search.",
      searchFailed: "Search failed.",
      runRetrieval: "Run retrieval",
      preparing: "Preparing search workspace...",
    },
    searchResults: {
      firstQueryTitle: "Ready for the first query",
      firstQueryDescription:
        "Select a collection, choose a strategy, and run retrieval to inspect snippets, ranking scores, and query rewrites.",
      latency: "Latency",
      resultCount: "Result count",
      tokenEstimate: "Token estimate",
      queryVariants: "Query variants",
      untitledChunk: "Untitled chunk",
      score: "Score",
      chunk: "Chunk",
      tokens: "Tokens",
      noHitsTitle: "No hits returned",
      noHitsDescription: "Try another collection, relax the query, or switch from dense to BM25 / hybrid retrieval.",
    },
    experimentsPage: {
      heading: "Compare strategies with saved traces",
      intro:
        "Run side-by-side strategy comparisons, save artifacts, and reopen older runs from the artifact shelf without touching curl.",
      loadFailed: "Failed to load experiment page data.",
      chooseCollectionBeforeRun: "Choose a collection before running experiments.",
      selectAtLeastOneStrategy: "Select at least one strategy.",
      runFailed: "Experiment run failed.",
      loadArtifactFailed: "Failed to load artifact.",
      artifactHistory: "Artifact history",
      noArtifacts: "Run the first experiment with `save_artifact` enabled and history will start appearing here.",
      latestRunTitle: "Latest run",
      latestRunEmpty: "Launch an experiment to compare strategy latency, token usage, and retrieval metrics.",
      selectedArtifactLoading: "Loading artifact...",
      selectedArtifactTitle: "Selected artifact",
      selectedArtifactEmpty: "Pick any artifact from the history column to reopen a saved experiment payload.",
      runExperiment: "Run experiment",
      artifactName: "Artifact name",
      preparing: "Preparing experiment workspace...",
    },
    experimentTable: {
      snapshot: "Experiment snapshot",
      strategies: "Strategies",
      overlapPairs: "Overlap pairs",
      artifactSaved: "Artifact saved",
      strategy: "Strategy",
      latency: "Latency",
      candidates: "Candidates",
      selected: "Selected",
      tokens: "Tokens",
      savings: "Savings",
      recallAtK: "Recall@K",
      mrr: "MRR",
      overlapDiagnostics: "Overlap diagnostics",
    },
  },
  zh: {
    common: {
      loading: "加载中...",
      cancel: "取消",
      collection: "集合",
      collections: "集合",
      query: "查询",
      topK: "Top K",
      strategy: "策略",
      description: "描述",
      domain: "领域",
      name: "名称",
      metadataJson: "元数据 JSON",
      title: "标题",
      sourceUri: "来源 URI",
      textBody: "正文内容",
      url: "URL",
      file: "文件",
      targetCollection: "目标集合",
      selectCollection: "请选择集合",
      latestIngest: "最近一次摄入",
      latestBuild: "最近一次建索引",
      nextStep: "下一步",
      sourceLabel: "来源",
      ingestedLabel: "摄入时间",
      yes: "是",
      no: "否",
      artifact: "实验产物",
      state: "状态",
      refreshList: "刷新列表",
      queryRewrite: "查询改写",
      rerank: "重排",
      preparing: "准备中...",
      metadataJsonInvalid: "元数据必须是合法的 JSON。",
      bytes: "字节",
      milliseconds: "毫秒",
      compressionModeLabels: {
        none: "不压缩",
        extractive: "抽取压缩",
        abstractive: "摘要压缩",
      },
    },
    sidebar: {
      badge: "独立检索界面",
      description: "在一个界面里完成语料准备、摄入、检索诊断和实验历史查看。",
      apiTarget: "本地 API 地址",
      footer: "FastAPI 服务需要单独运行。这个前端只通过 HTTP 与 deer-rag 通信。",
      language: "语言",
      english: "EN",
      chinese: "中文",
      nav: {
        collectionsLabel: "集合",
        collectionsDescription: "创建并查看语料集合",
        ingestLabel: "摄入",
        ingestDescription: "提交文本、URL 和文件",
        searchLabel: "检索",
        searchDescription: "运行 dense、BM25 和 hybrid 检索",
        experimentsLabel: "实验",
        experimentsDescription: "对比策略和实验产物",
      },
    },
    collectionsPage: {
      heading: "语料控制台",
      intro:
        "先创建逻辑上的集合，再进行摄入。后续界面里的所有操作都围绕同一个 collection ID 展开，所以这里是整条操作链路的起点。",
      newCollection: "新建集合",
      dialogTitle: "创建集合",
      dialogDescription:
        "第一版先保持简单。给语料命名，写清内容边界，只添加后面真正会用于筛选的元数据。",
      totalCollections: "集合总数",
      stateTip:
        "集合本身很轻量。更好的方式是按实验或下游产品拆分语料，而不是把所有内容都堆进一个大而全的集合。",
      noCollectionsTitle: "还没有集合",
      noCollectionsDescription: "先创建一个集合，再去摄入页面添加文档并建立索引。",
      createFailed: "创建集合失败。",
      loadFailed: "加载集合失败。",
      createAction: "创建集合",
    },
    collectionCard: {
      noDescription: "还没有描述。这个集合已经可以开始做摄入和检索。",
      metadataFields: "个元数据字段",
      updated: "更新时间",
      metadataPreview: "元数据预览",
      noMetadataStored: "还没有元数据。",
      ingestIntoCollection: "向这个集合摄入",
      searchNow: "立即检索",
      inspectExperiments: "查看实验",
    },
    ingestPage: {
      loadingCollections: "正在加载集合...",
      emptyTitle: "先从集合开始",
      emptyDescription: "这个页面需要先有集合。先去集合页面创建一个，再回来把文本、URL 或文件摄入进来。",
      nextStepTitle: "显式建立索引",
      nextStepDescription:
        "摄入只会写入原始文档和分块。只有重新建立 dense 和 BM25 索引后，检索才能真正工作。",
      buildIndexes: "建立索引",
      chooseCollectionFirst: "请先选择集合。",
      buildFailed: "建立索引失败。",
      duplicateDetected: "检测到重复文档。",
      freshStored: "已写入新文档。",
      latestIngestEmpty: "提交左侧任一表单后，这里会立刻显示文档摘要。",
      latestBuildEmpty: "建立索引后，这里会显示分块数量，以及 dense / lexical 的写入条数。",
      loadCollectionsFailed: "加载集合失败。",
      preparing: "正在准备摄入工作区...",
      chunksCreated: "个分块已创建",
      chunksAvailable: "个分块可用",
      denseVectorsWritten: "条 dense 向量已写入",
      lexicalRowsWritten: "条 BM25 记录已写入",
    },
    ingestForm: {
      sectionLabel: "摄入流程",
      heading: "添加语料内容",
      intro: "第一次使用时文本最快，URL 能验证抓取和解析链路，文件则能验证本地文档摄入流程。",
      textTab: "文本",
      urlTab: "URL",
      fileTab: "文件",
      optionalTitleOverride: "可选标题覆盖",
      chooseCollectionBeforeIngesting: "摄入前请先选择集合。",
      textIngestionFailed: "文本摄入失败。",
      webIngestionFailed: "网页摄入失败。",
      fileIngestionFailed: "文件摄入失败。",
      selectFileFirst: "请先选择文件。",
      ingestText: "摄入文本",
      fetchAndIngestUrl: "抓取并摄入 URL",
      uploadAndIngestFile: "上传并摄入文件",
    },
    searchPage: {
      heading: "观察检索行为",
      intro:
        "这个页面刻意偏诊断型。你可以直接看到片段、原始分数、查询变体，以及最终触发结果的检索策略。",
      chooseCollectionBeforeSearch: "检索前请先选择集合。",
      searchFailed: "检索失败。",
      runRetrieval: "执行检索",
      preparing: "正在准备检索工作区...",
    },
    searchResults: {
      firstQueryTitle: "准备好跑第一条查询了",
      firstQueryDescription: "先选择集合和策略，再执行检索，就能查看片段、排序分数和查询改写结果。",
      latency: "延迟",
      resultCount: "结果数量",
      tokenEstimate: "Token 估算",
      queryVariants: "查询变体",
      untitledChunk: "未命名分块",
      score: "得分",
      chunk: "分块",
      tokens: "Token",
      noHitsTitle: "没有返回结果",
      noHitsDescription: "试试换一个集合、放宽查询，或者从 dense 切到 BM25 / hybrid。",
    },
    experimentsPage: {
      heading: "对比策略并保存结果",
      intro:
        "在同一个页面里运行多策略对比、保存实验产物，并从历史栏重新打开旧实验，不需要再手写 curl。",
      loadFailed: "加载实验页面数据失败。",
      chooseCollectionBeforeRun: "运行实验前请先选择集合。",
      selectAtLeastOneStrategy: "至少选择一种策略。",
      runFailed: "实验运行失败。",
      loadArtifactFailed: "加载实验产物失败。",
      artifactHistory: "实验产物历史",
      noArtifacts: "先运行一次开启 `save_artifact` 的实验，这里才会出现历史记录。",
      latestRunTitle: "最近一次运行",
      latestRunEmpty: "发起一次实验后，这里会对比各个策略的延迟、Token 用量和检索指标。",
      selectedArtifactLoading: "正在加载实验产物...",
      selectedArtifactTitle: "已选实验产物",
      selectedArtifactEmpty: "从左侧历史栏选择任一实验产物，即可重新查看保存的实验内容。",
      runExperiment: "运行实验",
      artifactName: "实验产物名称",
      preparing: "正在准备实验工作区...",
    },
    experimentTable: {
      snapshot: "实验快照",
      strategies: "策略数",
      overlapPairs: "重叠对数",
      artifactSaved: "是否已保存实验产物",
      strategy: "策略",
      latency: "延迟",
      candidates: "候选数",
      selected: "选中数",
      tokens: "Token 数",
      savings: "节省量",
      recallAtK: "Recall@K",
      mrr: "MRR",
      overlapDiagnostics: "重叠诊断",
    },
  },
} as const;

type Messages = (typeof messages)[Locale];

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: Messages;
};

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>("zh");

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved === "en" || saved === "zh") {
      setLocale(saved);
      document.documentElement.lang = saved;
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, locale);
    document.documentElement.lang = locale;
  }, [locale]);

  const value = useMemo<I18nContextValue>(
    () => ({
      locale,
      setLocale,
      t: messages[locale],
    }),
    [locale],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used within I18nProvider.");
  }
  return context;
}
