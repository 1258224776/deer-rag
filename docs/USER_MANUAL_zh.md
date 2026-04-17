# deer-rag 使用说明书

## 1. 先用一句话理解它

`deer-rag` 不是聊天机器人，也不是报告生成器。
它更像一个“检索工作台”或“证据引擎”。

它负责的事情是：
- 把你的资料整理进一个语料集合
- 把资料切成可检索的块
- 建立 dense / BM25 / hybrid 检索索引
- 按查询找出最相关的证据
- 对不同检索策略做实验和评测

它不负责的事情是：
- 代替大模型写最终报告
- 自动做复杂的研究规划
- 替你管理完整业务流程

如果把整个项目压缩成一句话，就是：

> 先把资料变成可检索语料，再把“查得准不准”这件事做成可观察、可比较、可优化的系统。

## 2. 系统整体逻辑

系统的主链路是：

```text
创建 collection
  -> 摄入资料 ingest
  -> 切块 chunk
  -> 建索引 build indexes
  -> 检索 retrieve
  -> 组装上下文 / 返回证据
  -> 做实验和评测
```

你可以把它理解成 6 个阶段：

1. `collection`
   一个语料集合，类似“知识库容器”。

2. `ingest`
   把文本、文件或网页导入系统。

3. `chunk`
   把长文切成较小的检索单元，便于召回和排序。

4. `index`
   给这些 chunk 建立可检索索引。

5. `retrieve`
   用查询去召回最相关的证据。

6. `experiment / evaluation`
   比较不同检索策略，保存实验产物，做离线评测。

## 3. 你在 UI 里看到的 4 个页面是干嘛的

当前前端在 `ui/`，主页会跳到 `/collections`。

### `/collections`

这是“语料入口页”。

你在这里做的事情：
- 查看已有 collection
- 新建 collection
- 从某个 collection 跳到 ingest / search / experiments

适合理解成：

> 我准备把哪些资料放在一起检索？

一个 collection 可以是：
- 某个产品的知识库
- 某个客户项目的资料集合
- 某一批文档实验语料
- 某个垂直领域的专题语料

### `/ingest`

这是“导入资料页”。

你在这里做的事情：
- 选择 collection
- 导入文本
- 导入网页 URL
- 上传文件
- 手动触发 `Build indexes`

这个页面最重要的逻辑是：

> 导入资料不等于可以检索。

你导入完之后，还要执行一次 `Build indexes`，系统才会把新 chunk 写进 dense/BM25 索引里。

### `/search`

这是“检索页”。

你在这里做的事情：
- 选择 collection
- 输入 query
- 选择检索策略
- 打开或关闭 rerank
- 打开或关闭 query rewrite
- 查看证据结果、分数和检索指标

这个页面回答的问题是：

> 在这批语料里，这个问题能查到什么证据？

### `/experiments`

这是“策略对比页”。

你在这里做的事情：
- 对同一个 query 同时跑 dense / bm25 / hybrid
- 对比延迟、token、召回等结果
- 保存 artifact
- 查看历史 artifact

这个页面回答的问题是：

> 不是“能不能查到”，而是“哪种检索配置更好”。

## 4. 系统里几个最重要的概念

### Collection

语料容器。

你可以把它理解成：
- 一个知识库
- 一个实验语料集
- 一个独立的检索空间

不同 collection 之间默认彼此隔离。

### Source Document

原始文档记录。

比如：
- 一篇网页
- 一个 PDF
- 一份 Markdown
- 一段直接粘贴进去的文本

系统会记录它的：
- 标题
- 来源 URI
- 来源类型
- 校验和
- 摄入时间
- 元数据

### Chunk

切块后的最小检索单位。

RAG 系统很少直接拿整篇长文去做排序，通常会先切成 chunk，再对 chunk 做召回和重排。

### Index

索引是“让系统能查”的部分。

当前主要有：
- `dense`
  语义检索，适合语义相近但词面不完全重合的查询
- `bm25`
  关键词检索，适合专有名词、稀有词、术语、精确短语
- `hybrid`
  把 dense 和 bm25 的结果融合，兼顾语义与关键词

### Evidence

检索结果不是一整篇文档，而是一组证据项。

每个 evidence 通常包含：
- `snippet`
- `title`
- `source`
- `chunk_id`
- `score`
- `rerank_score`
- `token_estimate`
- `metadata`

### Artifact

artifact 是实验结果快照。

它的作用是：
- 保存一次实验的配置和结果
- 方便回看
- 方便比较不同方案

如果你把 deer-rag 当实验平台用，artifact 很重要。

## 5. 三种检索策略分别是什么

### dense

语义检索。

优点：
- 对“意思接近、措辞不同”的问题更友好

缺点：
- 对专有名词、精确关键词，有时不如 BM25 稳

适合：
- 概念问法
- 语义归纳型问法

### bm25

关键词检索。

优点：
- 对术语、函数名、配置名、产品名、路径名很稳

缺点：
- 不擅长处理“换种说法”的语义问题

适合：
- 文档问答
- API 字段检索
- 专有词密集语料

### hybrid

dense + bm25 融合。

优点：
- 通常是默认最稳的选择
- 兼顾语义和关键词

缺点：
- 配置空间更大，调优更复杂

如果你刚开始使用，不确定选什么，先用 `hybrid`。

## 6. 为什么一定要先 Build Indexes

这是新手最容易卡住的一点。

系统里“摄入资料”和“建索引”是分开的两步：

1. `ingest`
   把文档写进元数据存储，并切成 chunk。

2. `build indexes`
   把这些 chunk 编译成真正可检索的索引文件。

如果只 ingest、不 build indexes，会出现这类现象：
- 文档看起来已经导入成功
- 但 `/search` 里查不到东西
- 或者只能查到旧内容

所以最稳的使用顺序永远是：

```text
创建 collection
  -> ingest
  -> build indexes
  -> search
```

## 7. 这个系统在磁盘上都存了什么

当前项目是单机、本地文件型设计。

默认会用到这些目录和文件：

- `data/metadata.sqlite3`
  元数据数据库，保存 collection、document、chunk、retrieval run 等信息
- `data/raw/`
  原始文本持久化目录
- `data/indexes/<collection_id>/`
  每个 collection 的索引目录
- `data/artifacts/`
  实验结果产物目录
- `data/evaluation/`
  评测数据集目录

你可以粗略理解成：

- SQLite 管“目录信息”和“记录”
- `data/indexes/` 管真正的检索索引
- `data/artifacts/` 管实验快照

## 8. 第一次使用时，最推荐的操作顺序

如果你只是想先看懂、先跑通，建议完全按这个顺序来。

### 第一步：启动整套系统

在仓库根目录执行：

```powershell
.\dev.ps1 -OpenBrowser
```

它会：
- 起后端 API
- 起前端 UI
- 自动写前端 `.env.local`
- 打开浏览器

停止时执行：

```powershell
.\dev-stop.ps1
```

### 第二步：打开 `/collections`

这里是总入口。

你先新建一个 collection，比如：
- 名称：`my-first-demo`
- 域：`demo`
- 描述：随便写一句即可

### 第三步：进入 `/ingest`

选择刚才的 collection，然后导入一段最简单的文本。

推荐你第一次就用文本方式，不要先用文件或网页。

例如可以导入：

```text
deer-rag is a modular retrieval system. It supports dense retrieval, BM25 retrieval, hybrid retrieval, and experiment tracking.
```

### 第四步：点击 `Build indexes`

这一步是把刚才导入的 chunk 建成可检索索引。

只要这一步成功，右侧会显示最近一次 build 的结果，例如：
- chunk 数量
- dense 写入数量
- lexical 写入数量

### 第五步：进入 `/search`

先选中刚才的 collection，再输入一个问题，例如：

```text
What retrieval strategies does deer-rag support?
```

建议第一次这样试：
- strategy 选 `hybrid`
- `rerank` 先关掉
- `query rewrite` 先关掉
- `top_k` 用默认值

这时你应该会看到：
- 返回的 snippet
- score
- source
- 一些检索指标

### 第六步：进入 `/experiments`

这里不是为了“查答案”，而是为了“比较方案”。

你可以用同一个 query 同时跑：
- `dense`
- `bm25`
- `hybrid`

看它们在：
- latency
- token_estimate
- recall
- overlap

上的差异。

如果保存 artifact，后面还能反复回看。

## 9. 你会经常看到的几个开关是什么意思

### `top_k`

最终返回多少条结果。

数值越大：
- 候选更多
- 可能召回更全
- 也可能带来更多噪声

### `rerank`

先粗召回，再用重排器重新排序。

通常作用是：
- 让最相关的结果排得更靠前

代价是：
- 更慢

### `query rewrite`

系统先把原始 query 改写成一个或多个变体，再去检索。

有时会带来帮助：
- 不同表达方式能覆盖更多相关内容

有时也会带来副作用：
- 引入噪声
- 让排序变差

它不是“永远更好”的开关，所以 deer-rag 把它做成了可实验选项。

## 10. 这个系统的后端模块各负责什么

如果你想从“用户视角”往“系统视角”多理解一步，可以这样记：

- `app/ingestion/`
  负责导入、解析、切块、去重
- `app/indexing/`
  负责构建 dense/BM25 索引
- `app/retrieval/`
  负责检索主流程、query rewrite、混合检索、rerank
- `app/context/`
  负责把证据压到 token 预算里，做上下文优化
- `app/evaluation/`
  负责实验、评测、benchmark、artifact
- `app/storage/`
  负责元数据和运行记录持久化
- `app/api/`
  负责 FastAPI 接口层
- `ui/`
  负责可视化操作界面

## 11. 这个系统和“最终回答”是什么关系

很多人第一次接触这类项目时，会把它理解成“输入问题，直接输出最终答案”。

`deer-rag` 不是这个定位。

它更接近：

> 先把正确证据找出来，再把这些证据交给别的系统或人去生成最终回答。

所以它的价值不只是“能不能查到”，而是：
- 查到的东西是否可解释
- 是否可追踪来源
- 是否能重复做实验
- 是否能比较不同策略

## 12. 常见问题

### 为什么打开 `http://127.0.0.1:8010/` 是 404？

因为后端根路径没有首页。

后端主要提供的是：
- API
- `/docs`
- `/redoc`

真正的前端入口是：
- `http://localhost:3000`

### 为什么明明 ingest 成功了，却查不到？

最常见原因是没点 `Build indexes`。

### 为什么系统说 duplicate？

因为系统会根据文本 checksum 做去重。

这表示你导入的内容和同 collection 里已有内容高度相同。

### 为什么 search 页一定要先选 collection？

因为 deer-rag 不是全局混查。

检索是在指定 collection 内完成的。

### experiments 和 search 有什么本质区别？

`search` 是看单次检索结果。

`experiments` 是比较多个策略，并把结果保存下来。

## 13. 你可以怎么把它当成工作流来用

最简单的日常工作流是：

1. 按主题创建 collection
2. 持续 ingest 新资料
3. 每次更新后 build indexes
4. 在 search 页做人工检查
5. 在 experiments 页比较不同检索配置
6. 逐步确定你自己的默认策略

如果你只是想把它当知识检索工具用，到 `/search` 基本就够了。

如果你想把它当 RAG 优化平台用，重点就会转到 `/experiments` 和 `data/artifacts/`。

## 14. 一句话总结

第一次使用时，只记住下面这条就够了：

```text
collection 是语料库，ingest 是导入资料，build indexes 是让资料变得可查，search 是查证据，experiments 是比较哪种查法更好。
```

如果你已经把这句话理解了，deer-rag 的整体逻辑就已经通了。
