# 私募基金知识库 Agent - 架构设计文档

> 项目代号:`pe-kb-mvp`
> 目标:基于飞书团队空间文档,构建面向内部员工与合格投资者的私募基金知识问答 Agent,通过飞书机器人交付
> 版本:v0.1 (MVP)
> 最后更新:2026-04-18

---

## 目录

1. [项目背景与目标](#1-项目背景与目标)
2. [整体架构](#2-整体架构)
3. [技术选型](#3-技术选型)
4. [服务职责划分](#4-服务职责划分)
5. [核心数据流](#5-核心数据流)
6. [数据模型](#6-数据模型)
7. [关键设计决策](#7-关键设计决策)
8. [项目目录结构](#8-项目目录结构)
9. [部署与启动](#9-部署与启动)
10. [MVP 范围与后续迭代](#10-mvp-范围与后续迭代)
11. [附录](#11-附录)

---

## 1. 项目背景与目标

### 1.1 业务场景

私募基金管理公司的内部知识(研报、产品说明书、合同模板、投资决策会议纪要、法规合规文档等)高度依赖飞书团队空间(Wiki / 云文档)协作。随着文档体量增长,员工获取信息的效率下降,新人上手周期长,客户咨询响应不及时。

本项目目标是构建一个**内部知识问答 Agent**,通过飞书机器人接入,让员工和合格投资者通过自然语言提问即可获得带引用的准确回答。

### 1.2 核心需求

- **文档来源**:飞书团队空间(Wiki + 云文档 + 多维表格)
- **交付渠道**:飞书机器人(单聊 + 群聊 @)
- **合规要求**
  - 涉及私募产品具体信息(净值、收益、持仓)必须校验合格投资者身份
  - 文档权限透传(用户在飞书无权限的文档,Agent 也不能返回其内容)
  - 所有对话留痕 5 年以上,支持监管追溯
  - 输出内容不能包含"保本""稳赚""零风险"等违规表述
- **质量要求**
  - 回答必须基于知识库,不得幻觉编造
  - 每个关键结论必须有引用来源(文档名称 + 路径)

### 1.3 非目标(MVP 不做)

- 不做面向外部客户的 C 端问答(仅限内部员工与已认证合格投资者)
- 不做交易执行、订单下单等"写操作"
- 不做语音、图表生成等多模态输出(后续迭代)
- 不做多 Agent 协作(MVP 单 Agent 完成闭环)

---

## 2. 整体架构

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         飞书客户端                                │
│  (用户在群聊/单聊 @机器人 提问,接收带引用的回答卡片)              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│           飞书开放平台 (事件订阅 / 长连接 WebSocket)               │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┴───────────────────┐
         ▼                                       ▼
┌──────────────────┐                  ┌──────────────────────┐
│  bot_service     │                  │  sync_service        │
│  (TS/NestJS)     │                  │  (Python)            │
│                  │                  │                      │
│ · 接收消息事件    │                  │ · 监听文档变更事件    │
│ · 权限校验        │◄─────HTTP──────►│ · 拉取 Wiki/Docx     │
│ · 消息卡片渲染    │                  │ · Block→Markdown     │
│ · 会话管理        │                  │ · 分块 + Embedding   │
└────────┬─────────┘                  └──────────┬───────────┘
         │                                       │
         │ HTTP (问答请求)                        │
         ▼                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    rag_service (Python/FastAPI)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Retriever  │  │   Reranker  │  │   Agent Orchestrator    │  │
│  │  BM25+向量  │─►│ bge-rerank  │─►│  (合规校验+LLM调用)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└──────┬────────────────────┬──────────────────────┬─────────────┘
       │                    │                      │
       ▼                    ▼                      ▼
┌─────────────┐      ┌─────────────┐       ┌────────────────┐
│   Qdrant    │      │ PostgreSQL  │       │   LLM API      │
│  (向量库)   │      │  (元数据/   │       │  (通义/Claude) │
│             │      │   权限/日志) │       │                │
└─────────────┘      └─────────────┘       └────────────────┘
```

### 2.2 一次问答的调用链路

```
用户 @机器人 提问 ("X基金最新净值是多少")
        │
        ▼
  bot_service 接收事件 (取出 user_open_id + 问题)
        │
        ▼
  合规意图分类 (包含"净值" → 需合格投资者)
        │
        ├── 未认证 ──► 返回合规话术 + 审计
        │
        └── 已认证 ──► 查 PG 拿到可访问文档列表
                        │
                        ▼
                Qdrant 带权限 filter 检索 (向量 + doc_id filter, top 8)
                        │
                        ▼
                LLM 生成答案 (通义千问 + 引用来源)
                        │
                        ▼
                输出合规扫描 (屏蔽违禁词 + 加风险提示)
                        │
                        ▼
                消息卡片返回飞书 (答案 + 引用按钮 + 审计落库)
```

### 2.3 分层说明

| 层级 | 组件 | 职责 |
|------|------|------|
| 接入层 | 飞书开放平台 | 事件订阅、消息下发、文档 API |
| 网关/机器人层 | bot_service | 飞书事件解析、卡片渲染、会话管理 |
| Agent 服务层 | rag_service | 合规校验、检索、LLM 编排、审计 |
| 数据同步层 | sync_service | 文档拉取、解析、向量化入库 |
| 存储层 | Qdrant / PostgreSQL / Redis | 向量、元数据、缓存 |
| 模型层 | 通义 / Claude / Embedding API | LLM 推理、向量化 |

---

## 3. 技术选型

### 3.1 语言与框架

| 服务 | 语言 | 框架 | 选型理由 |
|------|------|------|---------|
| bot_service | TypeScript | NestJS + `@larksuiteoapi/node-sdk` | 飞书 Node SDK 最成熟,事件订阅和卡片交互开发效率高 |
| rag_service | Python 3.11 | FastAPI | RAG 生态 Python 最强,FastAPI 性能和开发效率兼备 |
| sync_service | Python 3.11 | FastAPI + `lark-oapi` | 文档解析生态 Python 压倒性优势 |

**为什么混合架构,不选单一语言?**

知识库核心能力(文档解析、Embedding、向量检索、LLM 编排)在 Python 生态有碾压性优势:LlamaIndex、LangGraph、Unstructured、FlagEmbedding、rank-bm25 等关键库都是 Python 一等公民。飞书侧的事件订阅、卡片交互用 TS 更简洁,前端工程师也能协作。两者通过 HTTP/gRPC 解耦,后续可独立扩展。

### 3.2 存储

| 组件 | 选型 | 用途 | 备选方案 |
|------|------|------|---------|
| 向量库 | Qdrant | Embedding 存储、向量检索、payload 过滤 | Milvus(规模大时) / PGVector(规模小时) |
| 关系库 | PostgreSQL 16 | 文档元数据、权限、审计日志 | MySQL(次选) |
| 缓存 | Redis 7 | 会话状态、限流、token 缓存 | - |
| 对象存储 | OSS / MinIO(可选) | 原始文档镜像、图片 | - |

**为什么 Qdrant 而非 Milvus?**

MVP 阶段 Qdrant 部署更轻(单二进制即可),Rust 编写性能好;payload filter 能力强,天然支持按 document_id 做权限过滤;规模到亿级向量时再考虑迁移 Milvus。

### 3.3 LLM 与 Embedding

| 能力 | 首选 | 备选 | 说明 |
|------|------|------|------|
| LLM(对话) | 通义千问 Qwen-Max | Claude Sonnet / DeepSeek | 数据不出境,金融场景合规;中文表现好 |
| Embedding | 通义 text-embedding-v3 (1024维) | bge-m3(自部署) | 部署成本低;如要自主可控可换 bge-m3 |
| Reranker | bge-reranker-v2-m3(自部署) | 通义 rerank API | 提升 Top-K 精排效果,尤其对中文长文本 |

**双模型策略(后续迭代)**:对外问答用国产模型(数据不出境),复杂推理、代码生成用 Claude(走合规的 API 代理)。

### 3.4 Agent 编排

MVP 阶段采用**手写 Python 工作流**(`app/agent/workflow.py`),状态少、逻辑清晰,便于审计。

未来升级选项:涉及多轮澄清、工具调用、多 Agent 协作时升级到 **LangGraph**;如需让业务同学低代码配置工作流,可引入 **Dify / Coze**。

### 3.5 可观测性(后续迭代)

- Trace:Langfuse 或 Phoenix,记录每次 LLM 调用的 prompt/response/延迟
- Metrics:Prometheus + Grafana(服务延迟、QPS、错误率)
- 日志:ELK / Loki(结构化日志聚合)

---

## 4. 服务职责划分

### 4.1 bot_service(TypeScript / NestJS)

**核心职责**
- 接收飞书事件(p2p 消息、群 @ 消息、卡片交互回调)
- 用户身份识别(open_id / union_id)
- 调用 rag_service 的 `/chat` 接口
- 渲染飞书消息卡片(答案 + 引用来源 + 交互按钮)
- 会话上下文管理(多轮对话)

**不做的事**
- 不做文档解析、向量化
- 不直接调用 LLM
- 不做权限配置管理(权限配置由飞书原生 + sync 服务维护)

### 4.2 rag_service(Python / FastAPI)

**核心职责**
- `/chat`:Agent 主工作流入口
- `/search`:纯检索接口(测试用)
- `/health`:健康检查
- 合规校验(意图识别、合格投资者校验、输出扫描)
- 混合检索(向量 + BM25)+ Rerank
- LLM 调用 + Prompt 组装
- 审计日志写入

### 4.3 sync_service(Python)

**核心职责**
- 定时全量同步(首次 & 兜底)
- 订阅飞书文档变更事件(`drive.file.edit_v1` 等),实时增量更新
- 拉取 Wiki 节点树 / docx blocks
- Block 树转 Markdown
- 分块 + Embedding + 写 Qdrant
- 写入文档元数据与权限列表到 PostgreSQL

**关键设计**:与 rag_service 解耦——同步负载(尤其是大批量首次同步)不影响在线问答性能;基于 `document_id + seq` 生成确定性 chunk ID,多次同步结果一致。

---

## 5. 核心数据流

### 5.1 文档同步流程

```
sync_service 启动
    │
    ▼
全量拉取:list_wiki_spaces → walk_wiki_tree
    │
    ▼
遍历每个节点(docx/sheet/bitable)
    │
    ▼
拉取 blocks (get_docx_blocks)
    │
    ▼
Block 树 → Markdown (blocks_to_markdown)
    │
    ▼
按标题 + token 混合分块 (split_markdown)
    │
    ▼
批量 Embedding (embed_texts)
    │
    ▼
delete_document(旧 chunks) → upsert_chunks(新 chunks) to Qdrant
    │
    ▼
upsert_document 写 PG 元数据
    │
    ▼
set_document_permissions 写权限表

--- 增量同步 ---
飞书 Webhook:drive.file.edit_v1
    │
    ▼
bot_service 转发事件到 sync_service
    │
    ▼
sync_docx(document_id)  # 复用同一 pipeline
```

### 5.2 问答的完整八步流程

1. **合规意图分类**:question 含"净值/持仓/收益率"等敏感词 → 需合格投资者
2. **权限拉取**:查 PG,拿到该用户可访问的 document_id 列表
3. **向量化**:embed_query(question) → 1024 维向量
4. **检索**:Qdrant 带权限 filter 检索(MatchAny on document_id),top_k=8
5. **精排**:(MVP 暂未启用)Reranker 取 top_k=4
6. **生成**:组装 Prompt(system + 参考资料 + 历史对话 + 问题)→ LLM
7. **合规扫描**:屏蔽违规词 + 追加风险提示 + 提取引用来源
8. **审计**:写 chat_logs(session_id / user / Q / A / chunks / citations / latency)

### 5.3 关键延迟预算(MVP 目标)

| 阶段 | 目标延迟 | 备注 |
|------|---------|------|
| bot_service 事件接收到转发 | < 50ms | |
| 合规意图分类 | < 10ms | 正则匹配 |
| PG 权限查询 | < 30ms | 加索引 |
| Embedding(单条) | < 200ms | 通义 API |
| Qdrant 检索 | < 100ms | MVP 数据量 |
| LLM 生成(首 token) | < 1.5s | Qwen-Max |
| LLM 生成(完整) | < 5s | 500 token 输出 |
| **端到端 P95** | **< 6s** | |

---

## 6. 数据模型

### 6.1 PostgreSQL 表结构

#### `documents` - 文档元数据

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL PK | 自增 ID |
| document_id | VARCHAR(64) UNIQUE | 飞书 document_id / node_token |
| space_id | VARCHAR(64) | 飞书知识空间 ID |
| obj_type | VARCHAR(32) | docx / sheet / bitable / wiki |
| title | TEXT | 文档标题 |
| path | TEXT | 在知识空间中的路径 |
| content_md | TEXT | 转换后的 Markdown 全文(截断 50KB) |
| owner_id | VARCHAR(64) | 文档所有者 open_id |
| last_edit_time | TIMESTAMP | 最后编辑时间 |
| synced_at | TIMESTAMP | 上次同步时间 |
| chunk_count | INT | 切分后的 chunk 数 |
| status | VARCHAR(16) | active / deleted |

索引:space_id、status

#### `document_permissions` - 文档权限

| 字段 | 类型 | 说明 |
|------|------|------|
| document_id | VARCHAR(64) | 关联 documents |
| principal_type | VARCHAR(16) | user / department / tenant |
| principal_id | VARCHAR(64) | 对应的 open_id / department_id |
| perm | VARCHAR(16) | read / edit |

复合唯一约束:`(document_id, principal_type, principal_id)`
索引:document_id、(principal_type, principal_id)

#### `chat_logs` - 对话审计(合规要求)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGSERIAL PK | |
| session_id | VARCHAR(64) | 会话 ID |
| user_open_id | VARCHAR(64) | 用户 |
| user_name | VARCHAR(128) | 用户名(冗余方便审计) |
| question | TEXT | 问题 |
| answer | TEXT | 完整回答 |
| retrieved_chunks | JSONB | 检索命中的 chunks(用于追溯) |
| citations | JSONB | 实际引用的文档 |
| latency_ms | INT | 响应延迟 |
| llm_model | VARCHAR(64) | 使用的模型名 |
| created_at | TIMESTAMP | |

索引:user_open_id、created_at

#### `qualified_investors` - 合格投资者白名单

| 字段 | 类型 | 说明 |
|------|------|------|
| user_open_id | VARCHAR(64) PK | 飞书 open_id |
| name | VARCHAR(128) | 姓名 |
| verified_at | TIMESTAMP | 认证时间 |
| expire_at | TIMESTAMP | 过期时间(NULL 表示永不过期) |
| level | VARCHAR(16) | standard / professional |

### 6.2 Qdrant Collection 结构

- Collection 名:`pe_kb_chunks`
- 向量维度:1024(通义 text-embedding-v3)
- 距离度量:Cosine

Payload schema(每个 chunk 的元数据):

```json
{
  "document_id": "doccnxxxxx",
  "seq": 3,
  "content": "原始文本内容...",
  "headings": ["私募产品手册", "A 基金", "申购流程"],
  "title": "A 基金产品手册",
  "space_id": "7xxxxxx",
  "path": "产品库/私募/A 基金产品手册"
}
```

Payload 索引:document_id(keyword)、allowed_users(keyword,后续启用)

---

## 7. 关键设计决策

### 7.1 权限透传:金融场景核心

**问题**:用户 A 在飞书对文档 X 无权限,Agent 不能把 X 的内容回答给 A,否则就是严重的数据泄露事故。

**方案(MVP)**

sync_service 同步文档时,调用飞书 `drive.permission.member.list` 接口拉取文档的可访问成员,写入 document_permissions 表。rag_service 问答时,先查 PG 拿到该用户可访问的 document_id 列表,在 Qdrant 检索时用 MatchAny filter 过滤,只返回有权限的 chunks。

**为什么不用 Qdrant 的 payload 存 allowed_users 数组?**

文档权限变更频繁时,Qdrant 的全量 payload 更新开销大;PG 作为权限 Source of Truth 更清晰,利于审计。

**生产环境建议**

回答前二次校验:用用户 token 调用飞书 API 确认权限(而非只信任缓存)。敏感文档增加"原文快照"留痕,避免文档删除后无法追溯。

### 7.2 合规前置 (Compliance-First)

**问题**:涉及"净值/持仓/收益率"等问题,监管要求只能回答合格投资者。如果等 LLM 生成后再判断,既浪费 token,又可能泄露信息片段。

**方案**

在检索和 LLM 调用**之前**做意图分类;未认证用户直接返回标准拒答话术,不进入 RAG 流程;所有被拦截的请求也要落审计日志。

### 7.3 输出合规扫描

**问题**:LLM 可能被 prompt 诱导或基于资料生成"保本""稳赚"等违规表述。

**方案**

关键词正则扫描(MVP);未来升级为小模型分类器(基于标注数据微调);触发后标记输出 + 告警 + 留痕,人工 review。

### 7.4 引用可追溯

**问题**:金融场景必须能追溯"这个答案是基于哪份文档的哪一段生成的"。

**方案**

每个 chunk 的 payload 带完整元数据(document_id + seq + headings + title);LLM prompt 中显式要求标注引用;审计表 retrieved_chunks 字段完整记录检索上下文(不仅是最终引用);飞书消息卡片展示引用来源,点击可跳转原文档。

### 7.5 分块策略

**问题**:飞书文档是 block 结构,不是纯文本。如果直接按固定 token 切,会破坏语义。

**方案**(见 `chunker.py`)

先按标题边界切(H1/H2/H3);单个 section 超过 chunk_size(500 tokens)时按滑窗(overlap=80)再切;每个 chunk 保留**标题面包屑**(例如:`产品库 > A 基金 > 申购流程`),在 Embedding 时作为前缀拼接;表格单独抽取为结构化数据(MVP 占位,后续完善);图片走 OCR 或 VLM 生成描述(后续)。

### 7.6 同步增量化

**问题**:全量扫描所有 Wiki 节点慢且受 API 限频。

**方案**

首次全量同步;之后订阅 `drive.file.edit_v1` 事件,文档变更实时推送;定时(每天凌晨)跑一次全量兜底,防止事件丢失。

---

## 8. 项目目录结构

```
pe-kb-mvp/
├── docker-compose.yml              # 一键启动 Qdrant / PG / Redis
├── .env.example                    # 环境变量模板
├── requirements.txt                # Python 依赖
├── ARCHITECTURE.md                 # 本文档
├── README.md                       # 快速开始
│
├── scripts/
│   └── init.sql                    # PG 建表脚本
│
├── rag_service/                    # Agent + RAG 核心服务 (Python)
│   ├── __init__.py
│   ├── config.py                   # 环境变量配置
│   │
│   ├── feishu/                     # 飞书 API 封装
│   │   ├── client.py               # tenant_access_token + wiki + docx API
│   │   ├── block_parser.py         # block 树 → Markdown 解析器
│   │   ├── auth_tool.py            # OAuth 令牌管理
│   │   ├── auth_server.py          # OAuth 授权服务
│   │   ├── oauth.py                # OAuth 封装
│   │   └── user_client.py          # 用户级 API 客户端
│   │
│   ├── rag/                        # RAG 核心
│   │   ├── chunker.py              # 标题 + token 混合分块
│   │   ├── embedder.py             # bge-m3 Embedding 封装
│   │   └── vector_store.py         # Qdrant 封装(含权限 filter)
│   │
│   ├── agent/                      # Agent 编排 (Step 7 完成)
│   │   ├── rag_agent.py            # RAG 主 Agent
│   │   ├── api.py                  # FastAPI 入口
│   │   ├── models.py               # Pydantic 数据模型
│   │   ├── llm.py                  # LLM 调用
│   │   └── compliance.py           # 合规校验
│   │
│   ├── models/
│   │   └── db.py                   # PG 操作
│   │
│   └── sync/
│       └── pipeline.py             # full_sync / sync_folder 命令
│
├── tests/                          # 测试套件
│   ├── step2_test_cases.json
│   ├── step4_smoke.py
│   ├── step5_*.py
│   ├── step6_*.py
│   ├── step7_api_contract.py       # Step 7 API 测试 (14 passed)
│   └── step7_chaos.py
│
├── sync_service/                   # (待补) 独立部署的同步服务
│
└── bot_service/                    # 飞书机器人 (TypeScript / NestJS)
    └── src/                        # (待补)
        ├── main.ts
        ├── event-handler.ts        # 飞书事件接收
        ├── card-renderer.ts        # 消息卡片渲染
        └── rag-client.ts           # 调用 rag_service
```

### 8.1 已实现模块清单

| 模块 | 文件 | 状态 | 说明 |
|------|------|------|------|
| Docker 基础设施 | docker-compose.yml、scripts/init.sql | ✅ | Qdrant + PG + Redis,含建表 SQL |
| 配置管理 | rag_service/config.py、.env.example | ✅ | 环境变量统一配置 |
| 飞书客户端 | feishu/client.py | ✅ | token 自动刷新 + wiki + docx API |
| Block 解析 | feishu/block_parser.py | ✅ | 处理标题/列表/代码/引用/表格(表格简化版) |
| 分块器 | rag/chunker.py | ✅ | 标题 + token 混合分块,带 heading 面包屑 |
| Embedding | rag/embedder.py | ✅ | 通义 text-embedding-v3 |
| 向量库 | rag/vector_store.py | ✅ | Qdrant 封装,支持权限 filter |
| 合规 | agent/compliance.py | ✅ | 关键词拦截 + 合格投资者判断 + 风险提示 |
| LLM 调用 | agent/llm.py | ✅ | 通义千问 + 金融 system prompt |
| 主工作流 | agent/workflow.py | ✅ | 完整 8 步闭环 |
| 数据访问 | models/db.py | ✅ | 文档 / 权限 / 审计 / 合格投资者 |
| 同步 Pipeline | sync/pipeline.py | ✅ | full_sync + sync_doc 命令 |
| FastAPI 接口 | agent/api.py、agent/models.py | ✅ | POST /api/v1/chat、/api/v1/search、/api/v1/health (Step 7 完成) |
| 飞书机器人 | bot_service/src/* | ✅ | 事件接收 + 卡片渲染 + 调用 RAG (Step 8 完成) |

---

## 9. 部署与启动

### 9.1 环境要求

- Docker + Docker Compose
- Python 3.11+
- Node.js 20+(后续 bot_service 需要)
- 飞书自建应用(拿到 App ID + App Secret)
- 通义千问 API Key(或其他 LLM 凭证)

### 9.2 飞书应用权限申请

**自建应用需开通的权限**

- `wiki:wiki:readonly` - 读取知识空间
- `docx:document:readonly` - 读取文档
- `drive:drive:readonly` - 读取云空间
- `drive:file:metadata:read` - 读取文件元信息
- `drive:permission:member:read` - 读取文档成员权限
- `im:message.group_at_msg` - 接收群 @
- `im:message.p2p_msg` - 接收单聊消息
- `im:message:send_as_bot` - 以机器人身份发消息

**事件订阅**

- `drive.file.edit_v1` - 文档编辑
- `drive.file.deleted_v1` - 文档删除
- `im.message.receive_v1` - 收到消息

### 9.3 启动步骤

```bash
# 1. 克隆项目
git clone <repo>
cd pe-kb-mvp

# 2. 配置环境变量
cp .env.example .env
vim .env   # 填入 FEISHU_APP_ID / SECRET / DASHSCOPE_API_KEY 等

# 3. 启动基础设施 (Qdrant / PG / Redis)
docker-compose up -d

# 4. 等待 PG 初始化完成,检查表
docker exec -it pe-kb-postgres psql -U pekb -d pekb -c "\dt"

# 5. 安装 Python 依赖
cd rag_service
pip install -r ../requirements.txt

# 6. 首次全量同步(阻塞执行,看日志)
python -m app.sync.pipeline full_sync

# 7. 启动 rag_service (待 api/main.py 补完)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 8. 启动 bot_service (待补完)
cd ../bot_service
npm install
npm run start:dev
```

### 9.4 本地测试验证

同步完成后,可以直接测试 workflow.run_chat:

```python
from app.agent.workflow import run_chat

result = run_chat(
    user_open_id="ou_test_user_001",
    user_name="测试用户",
    question="A 基金的申购流程是什么?",
)
print(result["answer"])
print(result["citations"])
```

---

## 10. MVP 范围与后续迭代

### 10.1 MVP 范围(本期)

- ✅ 飞书 Wiki / docx 文档全量 + 增量同步
- ✅ 基于标题的智能分块
- ✅ 向量检索 + 权限过滤
- ✅ 合规校验(合格投资者 + 输出扫描)
- ✅ 带引用的 LLM 问答
- ✅ 对话审计留痕
- ✅ 飞书机器人单聊 / 群 @ 问答

### 10.2 Phase 2(1-2 个月后)

- 表格 / 多维表格结构化解析(当前占位)
- 图片 OCR + VLM 描述(研报图表很关键)
- Reranker 接入(bge-reranker-v2-m3)
- BM25 + 向量混合检索
- Langfuse 接入,可观测性
- 飞书卡片交互(追问、点赞点踩、快速反馈)
- 会话多轮上下文管理(Redis)

### 10.3 Phase 3(3-6 个月后)

- 知识图谱(Neo4j)存储 基金—管理人—底层资产—关联方 关系
- 工具调用:查净值、查持仓、生成日报
- 多 Agent 协作:研究 Agent / 合规 Agent / 客服 Agent
- LangGraph 升级工作流引擎
- 定向微调(私募领域语料)
- 对外部合格投资者开放(需额外的身份认证流程)

### 10.4 技术债务 & 已知限制

- 当前 block_parser.py 表格渲染为占位符,需要完整实现
- 权限同步依赖飞书 API,大批量文档时有限频风险,需加退避和分批
- MVP 未做 Reranker,检索精度在文档量大时会下降
- 未集成可观测性,线上问题排查靠日志
- 合格投资者认证当前是白名单表,生产环境需对接 KYC 系统

---

## 11. 附录

### 附录 A:关键配置项说明

见 `.env.example`,其中关键项:

| 变量 | 示例值 | 说明 |
|------|-------|------|
| FEISHU_APP_ID | cli_xxxxx | 飞书自建应用 ID |
| FEISHU_APP_SECRET | xxxxx | 飞书应用密钥 |
| QDRANT_URL | http://localhost:6333 | 向量库地址 |
| QDRANT_COLLECTION | pe_kb_chunks | 向量库集合名 |
| POSTGRES_DSN | postgresql://... | PG 连接串 |
| DASHSCOPE_API_KEY | sk-xxxxx | 通义千问 API Key |
| EMBEDDING_MODEL | text-embedding-v3 | Embedding 模型 |
| EMBEDDING_DIM | 1024 | Embedding 维度 |
| LLM_MODEL | qwen-max | LLM 模型 |

### 附录 B:合规相关配置

**触发合格投资者校验的关键词** (`compliance.py`)

```
净值、持仓、业绩、收益率、认购、申购、起投、
年化、回撤、管理费、业绩报酬、封闭期、赎回
```

**输出屏蔽关键词**

```
保本、稳赚、保证.{0,5}收益、零风险、内幕、刚性兑付
```

**风险提示模板**

> 本回答基于内部知识库生成,仅供参考,不构成投资建议。私募基金投资具有较高风险,过往业绩不代表未来表现。投资前请仔细阅读基金合同和风险揭示书。

### 附录 C:飞书 API 主要端点速查

| 场景 | Endpoint | 说明 |
|------|---------|------|
| 获取 tenant_access_token | `POST /auth/v3/tenant_access_token/internal` | 2h 有效 |
| 列出知识空间 | `GET /wiki/v2/spaces` | 分页 |
| 遍历 wiki 节点 | `GET /wiki/v2/spaces/{space_id}/nodes` | 按 parent_node_token |
| 获取 docx blocks | `GET /docx/v1/documents/{document_id}/blocks` | 分页,page_size=500 |
| 获取 docx 纯文本 | `GET /docx/v1/documents/{document_id}/raw_content` | 兜底方案 |
| 获取文档成员权限 | `GET /drive/v1/permissions/{token}/members` | 权限透传核心 |
| 发送消息卡片 | `POST /im/v1/messages` | 支持 interactive 卡片 |

---

**文档负责人**:[待填]
**评审状态**:待内部评审