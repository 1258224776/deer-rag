# PROJECT_BACKGROUND_TEMP

## 这份文档的用途

这是一份临时背景说明文档，用来汇总当前项目讨论中的核心上下文，方便后续继续设计 `deer-rag` 时保持定位一致。

这份文件主要服务于项目规划，不是最终面向开源用户的 README，可以在后续项目稳定后删除或拆分。

## 当前整体背景

当前有两个核心项目：
- `agent-one`
- `deer-rag`

这两个项目的目标不是做成两个相似的 AI Demo，而是形成明确分工、互相补位的一套能力组合，用于展示在 Agent、RAG、检索优化、评测和 AI 工程这几个方向上的能力。

用户当前做这两个项目，一个重要目标是用于找工作。因此，这两个项目不仅要能运行，还要有清晰的技术叙事、项目边界和岗位映射价值。

## 当前核心判断

需要明确的是：`deer-rag` 必须首先是一个独立项目，而不是 `agent-one` 的附属模块。

它可以服务于 deep research，也可以被 `agent-one` 调用，但这只是应用场景和集成关系，不是它存在的前提。

因此，`deer-rag` 的定位应该是：

**一个独立的、模块化的 RAG 与检索优化系统，重点关注混合检索、重排、token 高效的上下文组装，以及评测与实验能力。**

而不是：
- 只服务 deep research 的内部知识库
- 只能辅助 `agent-one` 的配套组件
- 一个依附于某个 Agent 才成立的子系统

## 用户当前目标

用户希望做一个能够辅助 deep research 的系统，但这个系统不是单一项目，而是两个独立项目之间的协作：
- `agent-one` 负责动态研究任务
- `deer-rag` 负责独立的检索与证据能力

用户还明确希望 `deer-rag` 更侧重这些方面：
- token 消耗
- 模型微调或模型适配
- 检索优化
- 召回优化
- RAG 系统层面的工程能力

所以，`deer-rag` 的重点不是再做一个“上传 PDF 然后问答”的通用知识库，而是做成一个更偏检索基础设施、评测优化和证据交付的系统。

## deer-rag 的独立定位

当前讨论中，`deer-rag` 更合适的定位是：

- 一个独立的 retrieval backend
- 一个可复用的 evidence service
- 一个 RAG 优化实验平台
- 一个可评测的检索系统底座

典型应用场景可以包括：
- deep research workflow
- enterprise knowledge retrieval
- analyst copilots
- agentic evidence providers
- retrieval experiments for RAG systems

这里的关键点是：
- `deep research` 是 use case，不是 identity
- `agent-one` 是集成案例，不是项目定义

## agent-one 与 deer-rag 的关系

一句话定义：
- `agent-one` 是“会思考的研究员”
- `deer-rag` 是“证据引擎”

但这个说法只适用于二者集成时的关系，不应作为 `deer-rag` 的项目本体定义。

### agent-one 的职责

`agent-one` 负责动态研究任务本身：
- 任务规划
- 网页搜索
- 页面抓取
- 工具编排
- 报告生成

### deer-rag 的职责

`deer-rag` 负责独立的检索与证据能力：
- 文档摄取
- 索引构建
- 检索召回
- rerank 与去重
- token 成本控制
- evidence pack 交付
- 离线评测与实验比较

### 协作方式

在实际运行中，`agent-one` 可以把 `deer-rag` 作为众多信息源之一。

例如：
- `agent-one` 判断一个问题可能在私有资料中有答案
- 它通过 HTTP 请求调用 `deer-rag`
- `deer-rag` 返回相关片段、证据包、来源、分数、可引用信息
- `agent-one` 再把这些本地证据和网络搜索结果一起交给 LLM 综合分析

所以，`deer-rag` 的地位和“网页搜索”平级，它只是提供的是私有语料证据，而不是公开互联网证据。

## 为什么要拆成两个项目

拆开的原因很明确：两者职责不同，生命周期不同，求职叙事也不同。

### 1. 动态任务执行和静态知识检索不是一回事

`agent-one` 解决的是：当前问题怎么查、怎么推理、怎么组织结果。

`deer-rag` 解决的是：已有资料如何被组织、召回、优化和评测。

### 2. deer-rag 适合独立开源和复用

拆开之后：
- `deer-rag` 可以被 `agent-one` 使用
- `deer-rag` 也可以被其他 Agent 项目使用
- `deer-rag` 可以单独部署、单独维护、单独开源
- `agent-one` 不会因为嵌入过多底层检索逻辑而变得笨重

### 3. 更适合求职表达

两个项目拆开后，表达非常清晰：
- `agent-one` 展示 Agent 工作流与产品编排能力
- `deer-rag` 展示 RAG Infra、检索优化、召回优化、token 控制、评测体系能力

## deer-rag 当前强调的技术方向

结合用户目标和当前讨论，`deer-rag` 应优先强调以下方向：

### 1. 检索与召回优化

这是最核心的卖点之一。

建议围绕这些能力展开：
- dense retrieval
- BM25 retrieval
- hybrid retrieval
- multi-query retrieval
- query rewrite
- metadata filtering
- parent-child retrieval
- MMR 去重
- rerank

### 2. token 成本控制

重点不只是统计 token，而是做“面向预算的上下文组装”。
建议体现这些能力：
- token budget planning
- context trimming
- adjacent chunk merge
- evidence compression
- token per useful evidence 统计
- 不同策略下的成本比较

### 3. 模型适配 / 微调方向

用户提到了模型微调。

更合理的落地方式不是把大模型训练当主线，而是围绕检索系统做轻量适配：
- embedding model 对比
- reranker 对比
- query rewrite prompt 优化
- hard negative mining
- 针对特定语料域做 retriever / reranker 的小规模适配

### 4. 离线评测体系

这是项目从 Demo 走向工程系统的关键。

建议包括：
- Recall@K
- MRR
- nDCG
- gold evidence hit rate
- citation coverage
- latency / cost / quality 对比
- retriever / reranker / chunking 策略实验比较

### 5. 可解释证据输出

为了适配不同下游系统，`deer-rag` 不应只返回“相似文本”，还应返回结构化证据包。

建议 evidence pack 至少包含：
- snippet
- title
- source
- chunk_id
- score
- rerank_score
- token_estimate
- metadata
- citation_id

## deer-rag 不应该做成什么

为了避免项目定位跑偏，当前阶段不建议把 `deer-rag` 做成这些方向：
- 一个普通的聊天型知识库问答项目
- 一个只会向量检索的最小 RAG Demo
- 一个和 `agent-one` 职责高度重叠的 Agent 系统
- 一个一开始就追求超重 GraphRAG、超大图谱、复杂分布式部署的系统

换句话说，`deer-rag` 需要的是“工程深度”，而不是“功能堆砌”。

## 这个项目对找工作的意义

当前这两个项目不是孤立存在，而是服务于求职叙事。

### agent-one 更适合展示
- Agent workflow orchestration
- 工具调用与多来源信息整合
- 研究任务拆解与报告生成
- AI 产品工程能力

### deer-rag 更适合展示
- RAG systems engineering
- retrieval optimization
- recall optimization
- token-cost control
- evaluation pipeline design
- 可解释证据检索与交付

二者结合，可以覆盖两类岗位：
- Applied AI / Agent / AI 产品工程
- LLM Infra / RAG / 检索优化 / 评测工程

## 当前阶段建议

当前阶段应优先做清晰的系统骨架和叙事闭环，而不是过早做过重的功能。

建议优先级：
1. 明确项目定位与模块边界
2. 先完成 README、架构、路线图等文档
3. 先实现检索核心而不是复杂前端
4. 先把 hybrid retrieval、rerank、token-aware context assembly 做出来
5. 再逐步补评测、实验和高级特性

## 后续可删除说明

这份文件是临时背景汇总，主要用于后续继续开发时快速回忆项目初衷、分工和方向。

当以下内容已经稳定分散到正式文档中时，可以删除本文件：
- README
- 架构文档
- 路线图
- 开发计划
- 简历版项目描述
