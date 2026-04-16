# deer-rag

`deer-rag` 是一个模块化的 RAG 与检索优化系统，重点关注混合检索、重排、token 高效的上下文组装，以及评测与实验能力。

## 项目概述

`deer-rag` 是一个独立的检索基础设施项目。
它的目标是作为一个可单独存在的系统，用来构建、优化和评测面向私有语料或垂直领域语料的检索 pipeline。

它不依赖单一 Agent，不绑定某个产品，也不只服务某一个应用场景。
它可以被用作：
- 独立的 retrieval backend
- Agent 系统的 evidence service
- RAG 优化实验平台
- 私有知识语料的检索系统
- 可评测的 applied AI 检索底座

## deer-rag 重点解决什么问题

`deer-rag` 关注的是那些基础 RAG Demo 通常不会认真处理的工程问题：
- 长文档和噪声语料下的检索质量
- 语义检索与关键词检索并存时的混合召回
- 重排、去重与证据筛选
- 面向 token 预算的上下文组装
- 离线评测与实验对比
- 可引用、可追踪的证据交付

这个项目的目标不只是“检索出几个 chunk”，而是做一个可衡量、可配置、可优化、可复用的检索系统。

## 设计目标

- 提升复杂问题和垂直领域问题下的检索质量。
- 在证据进入模型之前减少无效 token 消耗。
- 让检索行为可观测、可解释、可调试。
- 支持可复现的实验与检索调优。
- 提供能被不同下游系统复用的通用 API。

## 核心能力

### Ingestion
把原始资料转成标准化的检索资产。

支持的输入：
- PDF
- Markdown / TXT / HTML
- 网页抓取结果
- 仓库文本快照
- CSV 与半结构化文本文件

主要职责：
- 清洗
- 切块
- 元数据提取
- 去重
- collection 管理
- 来源版本管理

### Multi-Index Retrieval
`deer-rag` 的核心不是单一向量检索，而是同一语料上的多视图索引。

建议保留以下索引类型：
- Dense index：语义检索
- BM25 index：关键词检索
- Metadata index：按来源、日期、类型过滤
- Optional entity index：人物、公司、产品、时间等实体索引

这样才能真正支持 hybrid retrieval，而不是单一向量召回。

### Retrieval Optimization
检索层应该是模块化、可实验、可比较的。

建议支持或规划支持：
- dense retrieval
- BM25 retrieval
- hybrid retrieval
- multi-query retrieval
- query rewrite
- metadata filtering
- parent-child retrieval
- MMR 去重
- rerank

### Context Optimization
系统优化的目标应该是“有效证据”，而不是更长的 prompt。

主要职责：
- token 预算规划
- 证据裁剪
- 相邻 chunk 合并
- 重复内容移除
- 保留来源链路的压缩
- 面向下游系统的 context packing

### Evaluation Lab
评测层不是补丁，而应该是系统能力的一部分。

建议支持的指标：
- Recall@K
- MRR
- nDCG
- gold evidence 命中率
- citation coverage
- token per useful evidence
- latency / cost / quality 对比

### Evidence API
`deer-rag` 返回的应该是 evidence pack，而不是纯文本块。

建议字段：
- snippet
- title
- source
- chunk_id
- score
- rerank_score
- token_estimate
- metadata
- citation_id

## 典型应用场景

- 需要可引用证据的 deep research 工作流
- 面向私有语料的企业知识检索
- 需要高召回检索的 analyst copilot
- 需要外部证据服务的 Agent 系统
- 用于 chunking、rerank、token budgeting 的 RAG 实验平台

## 推荐 MVP

### Phase 1
- collection 管理
- 文件与网页摄取
- chunking
- dense retrieval
- BM25 retrieval
- hybrid retrieval
- rerank
- citation-ready output
- token cost statistics

### Phase 2
- experiment configuration
- retrieval strategy comparison
- chunk strategy comparison
- latency / cost / recall dashboard
- query rewrite

### Phase 3
- metadata filtering
- parent-child retrieval
- evidence compression
- embedding 与 reranker benchmark
- hard negative mining

### Phase 4
- entity-aware retrieval
- timeline retrieval
- graph-enhanced retrieval
- lightweight domain adaptation

## API 草案

第一批接口建议如下：
- `POST /collections`
- `GET /collections`
- `POST /ingest/files`
- `POST /ingest/web`
- `POST /retrieve`
- `POST /retrieve/hybrid`
- `POST /retrieve/brief`
- `POST /context/assemble`
- `POST /experiments/run`
- `GET /experiments/{id}`
- `GET /metrics/query/{id}`

## 建议技术栈

- API：FastAPI
- Dense index：FAISS
- Lexical index：BM25
- Parsing：PyMuPDF、trafilatura、BeautifulSoup
- Embeddings：sentence-transformers 或 OpenAI-compatible embeddings
- Rerank：cross-encoder 或 ColBERT 风格 benchmark 接口
- Metadata store：SQLite 或 Postgres
- Config：YAML
- Evaluation artifacts：本地实验结果存储

## 快速开始

运行说明见 [docs/QUICKSTART.md](./docs/QUICKSTART.md)，其中包含：
- 安装方式
- 本地启动 API
- 最小 ingest / index / retrieve 流程
- smoke tests

## 集成示例：deer-rag + agent-one

`agent-one` 是 `deer-rag` 的一个下游集成示例。

在这个组合里：
- `agent-one` 负责规划、网页搜索、抓取、编排与报告生成。
- `deer-rag` 负责资料摄取、索引构建、检索优化、上下文组装与证据交付。

这个组合里的一句话关系是：
- `agent-one` 是研究员。
- `deer-rag` 是证据引擎。

但这只是一个集成案例，不是 `deer-rag` 的项目定义。

## 开源叙事

`deer-rag` 刻意聚焦在 AI 系统里的“检索层”。

它要展示的是：
- 模块化检索架构
- 检索优化与评测能力
- token 高效的上下文组装
- 面向证据的系统设计

## 求职价值

这个项目适合映射这些方向的岗位：
- RAG 系统工程
- 检索优化
- Applied AI Infra
- 评测与 benchmark 工程
- LLM 产品后端开发

## 仓库状态

当前仓库处于架构设计和基础脚手架阶段。
现阶段优先级是先完成检索核心，再逐步补齐优化层和评测层。

## 下一步开发顺序

1. 实现 collection 与 ingestion 模型。
2. 实现 dense + BM25 hybrid retrieval。
3. 增加 rerank 和 MMR 去重。
4. 增加 token-budget-aware context assembly。
5. 增加 experiment runner 与离线评测。
6. 增加面向下游系统的集成示例，例如 `agent-one`。
