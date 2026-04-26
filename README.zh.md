# deer-rag

一个模块化 RAG 与检索优化系统，专注于混合检索、重排序、Token 高效上下文组装与评测。

[English](./README.md)

## 项目简介

`deer-rag` 是一个独立的检索基础设施项目。
它被设计为一个独立系统，用于在私有或领域特定语料库上构建、优化和评测检索管道。

它不绑定任何单一 Agent、单一产品或单一应用领域，可以用作：
- 独立检索后端
- Agent 系统的证据服务
- RAG 优化实验平台
- 私有语料检索系统
- 面向应用 AI 产品的可基准测试检索栈

## 项目聚焦

`deer-rag` 围绕基础 RAG 演示通常忽略的工程问题构建：
- 长文档与噪声语料上的检索质量
- 跨语义信号与词法信号的混合召回
- 重排序与证据去重
- Token 预算感知的上下文组装
- 离线评测与实验对比
- 可引用的证据交付

目标不只是检索出 chunk，而是构建一个可量化、可配置、在真实下游工作流中有实用价值的检索系统。

## 设计目标

- 提升复杂和领域特定查询的检索质量。
- 在证据到达模型前减少无效 Token 消耗。
- 使检索行为可检查、可解释、可调试。
- 支持可复现的检索调优实验。
- 暴露可被不同下游系统使用的干净 API。

## 核心能力

### 文档摄入

将原始材料转换为标准化的检索资产。

支持的输入格式：
- PDF
- Markdown / TXT / HTML
- 抓取的网页
- 代码仓库文本快照
- CSV 与半结构化文本文件

负责处理：
- 文本清洗
- 分块（Chunking）
- 元数据提取
- 去重
- Collection 管理
- 来源版本控制

### 多索引检索

`deer-rag` 围绕同一语料库的多种检索视图设计。

推荐索引类型：
- 稠密向量索引（语义检索）
- BM25 词法索引（关键词检索）
- 元数据索引（来源/日期/类型过滤）
- 可选实体索引（公司/人物/产品/时间实体）

支持混合检索，而不仅仅是纯向量搜索。

### 检索优化

检索层应具备模块化和实验友好性。

已支持或规划中的策略：
- 稠密检索
- BM25 检索
- 混合检索
- 多查询检索
- 查询改写
- 元数据过滤
- 父子检索
- MMR 去重
- 重排序（Rerank）

### 上下文优化

系统应优化有价值的证据，而非生成更长的提示词。

负责处理：
- Token 预算规划
- 证据裁剪
- 相邻 Chunk 合并
- 重复删除
- 保留来源的压缩
- 为下游消费者组装上下文

### 评测实验室

评测是系统设计的一部分，而不是事后补充。

建议指标：
- Recall@K
- MRR
- nDCG
- 金标证据命中率
- 引用覆盖率
- 每条有价值证据的 Token 消耗
- 延迟 / 成本 / 质量对比

### 证据 API

`deer-rag` 应返回证据包（Evidence Pack），而不是纯文本。

建议字段：
- snippet（摘录）
- title（标题）
- source（来源）
- chunk_id
- score（检索分数）
- rerank_score（重排序分数）
- token_estimate（Token 估算）
- metadata（元数据）
- citation_id（引用 ID）

## 典型使用场景

- 需要可引用证据的深度研究工作流
- 面向私有语料的企业知识检索
- 需要高召回检索的分析师 Copilot
- 需要外部证据提供者的 Agent 系统
- 针对分块、重排序与 Token 预算的 RAG 实验

## 推荐 MVP 路线

### 第一阶段
- Collection 管理
- 文件与网页摄入
- 分块
- 稠密检索
- BM25 检索
- 混合检索
- 重排序
- 可引用格式输出
- Token 成本统计

### 第二阶段
- 实验配置
- 检索策略对比
- 分块策略对比
- 延迟 / 成本 / 召回仪表盘
- 查询改写

### 第三阶段
- 元数据过滤
- 父子检索
- 证据压缩
- Embedding 与 Reranker 基准测试
- 难负例挖掘

### 第四阶段
- 实体感知检索
- 时间线检索
- 图增强检索
- 轻量领域适配

## 当前 API

已实现的端点：
- `GET /health`
- `GET /collections`
- `POST /collections`
- `POST /ingest/text`
- `POST /ingest/files`
- `POST /ingest/web`
- `POST /indexes/build`
- `POST /retrieve`，`strategy = dense | bm25 | hybrid`
- `POST /context/assemble`
- `POST /experiments/run`
- `POST /experiments/context-efficiency`
- `POST /experiments/chunk-size`
- `POST /experiments/run-config`
- `GET /experiments/artifacts`
- `GET /experiments/artifacts/{artifact_id}`
- `POST /experiments/compare`
- `POST /experiments/compare-summary`
- `POST /evaluation/run-dataset`
- `POST /experiments/benchmark/embeddings`
- `POST /experiments/benchmark/rerankers`

## 推荐技术栈

- API：FastAPI
- 稠密索引：FAISS
- 词法索引：BM25
- 文档解析：PyMuPDF、trafilatura、BeautifulSoup
- Embedding：sentence-transformers 或兼容 OpenAI 的 Embedding 接口
- Rerank：Cross-Encoder 或 ColBERT 风格基准接口
- 元数据存储：SQLite 或 Postgres
- 配置：YAML
- 评测产物：本地实验存储

## 快速上手

### Windows 一键启动

```
start-deer-rag.cmd
```

自动启动 FastAPI 后端并在浏览器中打开独立 UI。

### 手动启动

参见 [docs/QUICKSTART.md](./docs/QUICKSTART.md)，涵盖：
- 安装
- 本地 API 启动
- 最小化摄入 / 建索引 / 检索流程
- 冒烟测试

### 独立 UI

仓库在 `ui/` 目录下包含一个基于 Next.js 的独立 UI。
支持中文与英文切换（在侧边栏切换），覆盖完整工作流：文档摄入、索引构建、检索查询、实验对比。

单独运行 UI：

```bash
cd ui
npm install
npm run dev
```

UI 默认连接到 `http://localhost:8000` 的 FastAPI 后端。

### 配置

服务默认使用内置配置运行。
如需使用自定义配置文件，启动前设置环境变量：

```bash
DEER_RAG_CONFIG=path/to/config.yaml uvicorn app.api.app:app --reload
```

如果设置了环境变量但文件不存在，服务会抛出错误，而不是静默回退到默认值。

## 真实中文小型评测

仓库包含一个真实的中文端到端检索小型评测，位于 [data/evaluation/mini-eval-python-venv-zh.yaml](./data/evaluation/mini-eval-python-venv-zh.yaml)。

使用版本锁定的来源文档：
- Python 3.14 zh-CN 文档：`venv --- 创建虚拟环境`
- 来源 URL：`https://docs.python.org/zh-cn/3.14/library/venv.html`

评测脚本自动抓取页面、解析、摄入、构建 dense + BM25 索引，从 chunk 索引解析金标 chunk，并运行离线评测：

```bash
python scripts/run_mini_eval_python_venv_zh.py
```

当前本地基准（1 篇文档 / 5 条查询）：

| 配置 | dense Recall@5 | dense MRR | bm25 Recall@5 | bm25 MRR | hybrid Recall@5 | hybrid MRR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 关闭查询改写 | 0.80 | 0.550 | 1.00 | 0.900 | 1.00 | 0.767 |
| 开启查询改写 | 0.80 | 0.500 | 1.00 | 0.900 | 0.80 | 0.700 |

这个评测集规模有意保持较小。其目的不是声称基准完整性，而是证明一个真实可复现的 `摄入 -> 建索引 -> 运行评测 -> 查看指标` 闭环。

在当前中文默认 Embedding 下，这个切片仍然偏词法主导：`bm25` 表现最强，而 `query rewrite` 反而略微降低了排序质量。

## 真实评测套件

还提供了一个基于切片的套件运行器：

```bash
python scripts/run_real_eval_suite.py
```

当前包含：
- `lexical` 切片：Python `venv` 文档
- `semantic` 切片：Python 设计 FAQ

套件级别的当前发现：
- 在 `lexical` 切片上，`bm25` 仍是最强排序器（`MRR 0.900`），中文默认 Embedding 下 `dense` 提升至 `MRR 0.550`。
- 在 `semantic` 切片上，切换到中文 Embedding 消除了旧英文 Embedding 的病态基准：`dense MRR` 从 `0.0625` 升至 `0.458`，与 `bm25`（`0.500`）形成有效竞争，而不是接近随机。
- 在 `semantic` 切片上，将 `rrf_k` 降至 `10` 仍是我们测量到的最佳设置；默认配置现已与该观测对齐。

## Embedding 基准测试

还提供了一个专用的 Embedding 基准测试脚本：

```bash
python scripts/run_embedding_benchmark_suite.py --hybrid-rrf-k 10
```

在相同中文概念查询上的 semantic 切片 dense 结果：

| 模型 | dense Recall@5 | dense MRR |
| --- | ---: | ---: |
| `sentence-transformers/all-MiniLM-L6-v2` | 0.25 | 0.0625 |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | 0.75 | 0.4375 |
| `BAAI/bge-small-zh-v1.5` | 0.75 | 0.4583 |
| `BAAI/bge-m3` | 0.75 | 0.3958 |

基于该基准，仓库当前默认为：
- 稠密 Embedding 模型：`BAAI/bge-small-zh-v1.5`
- Reranker 模型：`BAAI/bge-reranker-base`（与 Embedding 模型同系列，中文对齐）
- 混合检索 RRF 参数：`10`

`bge-m3` 在词法切片上产生了最佳混合结果，但 `bge-small-zh-v1.5` 是目前最优实用默认值——它在中文语义切片上给出最强 dense 结果，同时模型体积保持轻量。

## 集成示例：deer-rag + agent-one

`agent-one` 是 `deer-rag` 的一个可能下游消费者。

在该集成中：
- `agent-one` 负责规划、网页搜索、抓取、编排和报告生成。
- `deer-rag` 负责语料摄入、索引构建、检索优化、上下文组装和证据交付。

一句话关系：
- `agent-one` 是研究员。
- `deer-rag` 是证据引擎。

这是一个集成示例，不是项目的定义。

## 开源定位

`deer-rag` 专注于 AI 系统的检索层。

旨在展示：
- 模块化检索架构
- 检索优化与评测纪律
- Token 高效上下文组装
- 以证据为导向的系统设计

## 简历价值

该项目与以下方向的岗位高度匹配：
- RAG 系统工程
- 检索优化
- 应用 AI 基础设施
- 评测与基准测试
- LLM 产品后端开发

## 仓库现状

文档摄入、索引构建、检索、上下文优化、离线评测路径均已实现。
仓库包含真实中文小型评测、基于切片的评测套件，以及有数据支撑默认值的 Embedding 基准测试。
提供基于 Next.js 的独立 UI，支持中英文切换，与 FastAPI 后端直连。
配置加载现支持 `DEER_RAG_CONFIG` 环境变量，对缺失文件抛出明确错误而非静默回退。

当前缺口不是缺少端点或功能，而是基准测试的深度：将现有评测切片扩展为覆盖更多文档、更难查询类别，以及对查询改写、重排序和分块策略的有数据支撑的横向对比。

## 下一步计划

1. 将小型评测扩展为多文档中文基准，引入更难的查询类别。
2. 在相同金标集上对查询改写、重排序和分块进行对比，明确哪些选项真正有效。
3. 增加中文对齐的 Reranker 基准切片，验证 `bge-reranker-base` 的默认选择。
4. 提升元数据质量，使新鲜度和时间线检索具备更充分的评测依据。
5. 补充更难的检索场景：多跳推理、否定查询、时间条件查询和跨文档推理。
6. 预计算 Chunk 邻接关系和文档元数据，将图扩展的计算成本从查询时前移至建索引阶段。
