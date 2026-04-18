# 私募基金知识库 Agent - 存储架构教程

> 本教程详细解释为什么这个项目需要三种不同的存储组件，以及它们如何协作完成一次问答。

**面向读者**：希望理解项目架构的技术人员
**前置知识**：了解什么是数据库、什么是 API 调用

---

## 目录

1. [先从一个真实问题开始](#1-先从一个真实问题开始)
2. [三种存储组件的角色划分](#2-三种存储组件的角色划分)
3. [PostgreSQL 详解](#3-postgresql-详解)
4. [Qdrant 详解](#4-qdrant-详解)
5. [Redis 详解](#5-redis-详解)
6. [一次问答的完整数据流](#6-一次问答的完整数据流)
7. [为什么不用一种数据库解决所有问题](#7-为什么不用一种数据库解决所有问题)
8. [代码示例](#8-代码示例)

---

## 1. 先从一个真实问题开始

想象用户通过飞书机器人问了这样一个问题：

> **"A基金的封闭期是多久？"**

这句话背后，AI 需要做以下事情：

```
1. 判断这个问题是否涉及敏感信息（"封闭期"本身不敏感，但如果是"净值"就需要合规）
2. 确认这个用户有没有权限看到关于 A 基金的信息
3. 在海量文档中找到所有和"封闭期"、"基金"相关的内容
4. 综合分析后给出准确回答，并注明来源
5. 把这次对话记录下来，供合规审计
```

这 5 件事由**三个不同的存储组件**分别负责。为什么会这样？让我们从头说起。

---

## 2. 三种存储组件的角色划分

### 2.1 一句话说明

| 组件 | 一句话说明 | 存储内容 |
|-----|----------|---------|
| **PostgreSQL** | 关系型数据库，存"**结构化数据**" | 文档元数据、用户权限、对话日志 |
| **Qdrant** | 向量数据库，存"**文档的语义特征**" | 文档片段的向量（Embedding） |
| **Redis** | 内存数据库，存"**临时热点数据**" | 缓存、会话、限流计数器 |

### 2.2 类比：图书馆

把私募基金知识库想象成一个**图书馆**：

```
┌─────────────────────────────────────────────────────────────┐
│                          图书馆                              │
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  目录卡片柜   │    │  智能推荐系统 │    │  临时便签区   │     │
│  │  (PG)       │    │  (Qdrant)   │    │  (Redis)    │     │
│  │             │    │             │    │             │     │
│  │ "A基金合同   │    │ "找和基金   │    │ "某用户正在   │     │
│  │  在3楼B架"   │    │  封闭期相关  │    │  问A基金"    │     │
│  │             │    │  的书"       │    │             │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│       ↓                   ↓                   ↓              │
│   精确查找            语义相似度搜索        临时状态          │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. PostgreSQL 详解

### 3.1 什么是 PostgreSQL

PostgreSQL（简称 PG）是一个**关系型数据库**。你可以把它理解成 Excel 表格的超级升级版——能存几亿行数据、支持复杂的表格关联、还能设置各种约束保证数据不出错。

### 3.2 这个项目用 PG 存什么

#### 表 1：`documents`（文档元数据表）

```
┌────────────────┬────────────────────┬────────────────────────────┐
│    字段        │      类型          │         说明                │
├────────────────┼────────────────────┼────────────────────────────┤
│ document_id   │ VARCHAR(64)        │ 飞书文档的唯一标识符        │
│ space_id      │ VARCHAR(64)        │ 属于哪个知识空间            │
│ obj_type      │ VARCHAR(32)        │ 文档类型：docx/sheet/wiki   │
│ title         │ TEXT               │ 文档标题                    │
│ path          │ TEXT               │ 在知识空间里的路径          │
│ content_md    │ TEXT               │ 转换后的 Markdown 内容      │
│ owner_id      │ VARCHAR(64)        │ 文档所有者                  │
│ last_edit_time│ TIMESTAMP          │ 最后编辑时间                │
│ synced_at     │ TIMESTAMP          │ 上次同步到系统的时间        │
│ chunk_count   │ INT                │ 这个文档被切成了多少块      │
│ status        │ VARCHAR(16)         │ active=正常 deleted=已删除  │
└────────────────┴────────────────────┴────────────────────────────┘
```

#### 表 2：`document_permissions`（权限表）

这是**权限透传**的核心。飞书里用户 A 可能没有权限访问某份文档，Agent 也不能把这份文档的内容返回给 A。

```
┌────────────────┬───────────────┬────────────────────────────┐
│    字段        │    类型       │         说明                │
├────────────────┼───────────────┼────────────────────────────┤
│ document_id   │ VARCHAR(64)   │ 关联 documents 表           │
│ principal_type│ VARCHAR(16)   │ user=个人 dept=部门 tenant=全员│
│ principal_id  │ VARCHAR(64)   │ 对应的 open_id 或 department_id │
│ perm          │ VARCHAR(16)   │ read=可读 edit=可编辑       │
└────────────────┴───────────────┴────────────────────────────┘

示例数据：
document_id      │ principal_type │ principal_id    │ perm
──────────────────────────────────────────────────────────
doccn_xxxxx_001 │ user          │ ou_zhang_san   │ read
doccn_xxxxx_001 │ dept          │ dept_investment│ read
doccn_xxxxx_002 │ user          │ ou_li_si       │ read
```

#### 表 3：`chat_logs`（对话审计表）

金融合规要求**所有对话留痕 5 年以上**，这张表就是干这个的。

```
┌────────────────┬───────────────┬────────────────────────────┐
│    字段        │    类型       │         说明                │
├────────────────┼───────────────┼────────────────────────────┤
│ id             │ BIGSERIAL     │ 主键，自增                  │
│ session_id     │ VARCHAR(64)   │ 会话 ID，同一对话多次交互    │
│ user_open_id   │ VARCHAR(64)   │ 用户身份                    │
│ user_name      │ VARCHAR(128)  │ 用户名（冗余存储方便审计）  │
│ question       │ TEXT          │ 用户问的问题                │
│ answer         │ TEXT          │ AI 给的回答                 │
│ retrieved_chunks│ JSONB        │ 检索到的文档片段（用于追溯） │
│ citations      │ JSONB         │ 最终引用的文档列表          │
│ latency_ms     │ INT           │ 响应耗时（毫秒）            │
│ llm_model      │ VARCHAR(64)   │ 用了哪个 LLM               │
│ created_at     │ TIMESTAMP     │ 对话时间                    │
└────────────────┴───────────────┴────────────────────────────┘

重点：answer 字段存的是完整回答，不是摘要。
      retrieved_chunks 存了检索上下文，方便以后复盘"为什么会这么回答"。
```

#### 表 4：`qualified_investors`（合格投资者白名单）

私募基金涉及"净值"、"持仓"等敏感信息，只有在白名单里的用户才能问。

```
┌────────────────┬───────────────┬────────────────────────────┐
│    字段        │    类型       │         说明                │
├────────────────┼───────────────┼────────────────────────────┤
│ user_open_id   │ VARCHAR(64)  │ 飞书 open_id（主键）        │
│ name           │ VARCHAR(128) │ 姓名                        │
│ verified_at    │ TIMESTAMP    │ 认证时间                    │
│ expire_at      │ TIMESTAMP    │ 过期时间，NULL=永不过期     │
│ level          │ VARCHAR(16)  │ standard=普通 professional=专业 │
└────────────────┴───────────────┴────────────────────────────┘
```

### 3.3 为什么用 PG 而不是 MySQL

| 对比项 | PostgreSQL | MySQL |
|-------|----------|-------|
| JSON 支持 | 原生 JSONB，直接存检索结果 | 5.7 后支持但功能弱 |
| 全文搜索 | 内置全文搜索 | 需要插件 |
| 数组类型 | 原生支持数组 | 不支持 |
| 许可 | BSD 开源，社区活跃 | GPL 商业使用有顾虑 |

---

## 4. Qdrant 详解

### 4.1 什么是向量数据库

传统的数据库像 PG、MySQL 找数据都是靠**精确匹配**：

```
WHERE title = 'A基金合同'
WHERE content LIKE '%封闭期%'
```

但这种方式有两个问题：

1. **同义词问题**："封闭期"和"锁定期"是同一个意思，但数据库会当成不同的词
2. **语义理解问题**：用户问"基金封闭期间能不能中途退出"，传统的 LIKE 完全无法理解语义

**向量数据库**解决的是**语义搜索**问题。核心思想是：

```
第一步：把文档的每个片段转成一串数字（向量/Embedding）
        "私募基金在封闭期内不允许赎回" → [0.123, -0.456, 0.789, ...] (1024维)

第二步：把问题也转成向量
        "封闭期可以取钱吗" → [0.234, -0.123, 0.567, ...] (1024维)

第三步：找"距离最近"的向量
        通过余弦相似度（Cosine Similarity）计算两个向量的"语义相似程度"
```

### 4.2 为什么选 Qdrant

市面上的向量数据库有：Pinecone、Weaviate、Milvus、Qdrant 等。

| 选择 Qdrant 的原因 | 说明 |
|------------------|------|
| 部署简单 | 单二进制，不需要 Kubernetes |
| 性能好 | Rust 写的，内存和 CPU 效率高 |
| 权限过滤强 | 支持按 document_id 过滤，这是这个项目的核心需求 |
| 轻量 | MVP 阶段数据量小，Qdrant 完全够用 |

### 4.3 Qdrant 存什么

```
Collection: pe_kb_chunks

每条数据（Point）包含：
├── id              : 唯一ID (自增)
├── vector          : [0.123, -0.456, ...] (1024维)
└── payload        : 元数据
    ├── document_id : 来自哪份文档
    ├── seq         : 文档内的序号
    ├── content     : 原始文本内容
    ├── headings    : ["A基金", "申购流程"] (标题面包屑)
    ├── title       : 文档标题
    ├── space_id    : 知识空间ID
    └── path        : "产品库/私募/A基金"
```

### 4.4 为什么向量数据不和 PG 存在一起

PG 有个扩展叫 `pgvector`，理论上可以把向量存在 PG 里。为什么不这么做？

| 方案 | 优点 | 缺点 |
|-----|-----|------|
| PG + pgvector | 统一存储 | 检索性能差，数据量大了很慢 |
| Qdrant 独立 | 检索性能好，专用优化 | 多一个服务 |

**关键原因**：Qdrant 的 `payload filter` 能力比 PG 强太多。这个项目需要在检索时按 `document_id` 过滤（权限控制），Qdrant 的过滤性能比 PG 好很多个数量级。

### 4.5 检索流程图

```
用户问："A基金的封闭期是多久？"

                    ┌─────────────────────┐
                    │  1. 转成向量          │
                    │  embed_query()       │
                    │  [0.234, ...]        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  2. 查询 Qdrant     │
                    │  带着 document_id    │
                    │  过滤条件（权限）    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  3. 返回 top-8      │
                    │  最相关的文档片段    │
                    └─────────────────────┘
```

---

## 5. Redis 详解

### 5.1 什么是 Redis

Redis 是一个**内存数据库**。数据存在内存（RAM）里，读写速度极快（微秒级），但断电后数据会丢失。

对比：
| 存储 | 读取速度 | 持久化 | 适合存什么 |
|-----|---------|-------|----------|
| PostgreSQL | ~10ms | 是 | 重要数据，需要持久化 |
| Qdrant | ~5ms | 是 | 向量数据，需要持久化 |
| Redis | ~0.1ms | 可选 | 临时数据、缓存 |

### 5.2 这个项目用 Redis 存什么

#### 用途 1：限流

防止用户或恶意攻击者频繁调用 API。

```python
# 伪代码：每个用户每秒最多问3次
key = f"rate_limit:{user_open_id}"
count = redis.get(key)

if count and int(count) >= 3:
    return "请稍后再试"

redis.incr(key)
redis.expire(key, 1)  # 1秒后过期
```

#### 用途 2：会话上下文（多轮对话）

第一轮用户问"A基金封闭期"，第二轮用户说"那封闭期结束后呢"——AI 需要知道"那"指的是 A 基金。

```python
# 存最近 3 轮对话
key = f"session:{session_id}"
redis.lpush(key, json.dumps({"role": "user", "content": "那封闭期结束后呢"}))
redis.ltrim(key, 0, 5)  # 只保留最近 3 条
redis.expire(key, 3600)  # 1小时过期
```

#### 用途 3：热点数据缓存

有些问题被问很多次（比如"公司地址在哪"），可以把答案缓存起来。

```python
# 缓存 5 分钟
key = f"cache:answer:{hash(question)}"
cached = redis.get(key)
if cached:
    return json.loads(cached)

answer = llm.generate(question)
redis.setex(key, 300, json.dumps(answer))  # 5分钟后过期
```

#### 用途 4：飞书事件去重

飞书平台在网络波动时会重复推送同一个事件，需要去重。

```python
event_id = event["header"]["event_id"]
key = f"event:{event_id}"
is_new = redis.set(key, "1", "EX", 600, "NX")  # 10分钟窗口，只设置一次

if not is_new:
    return  # 重复事件，跳过
```

### 5.3 为什么不用 Redis 存所有数据

Redis 是**内存数据库**，贵且不适合存所有数据：

| 数据类型 | 存储大小 | 持久化需求 | 选 Redis？ |
|---------|---------|----------|----------|
| chat_logs | 每年可能几 GB | 必须（5年合规） | ❌ 放 PG |
| 文档向量 | 几千万维 | 必须 | ❌ 放 Qdrant |
| 用户 session | KB 级 | 可选 | ✅ 放 Redis |
| 限流计数 | Byte 级 | 不需要 | ✅ 放 Redis |
| 热点缓存 | KB 级 | 不需要 | ✅ 放 Redis |

---

## 6. 一次问答的完整数据流

现在我们把三个组件串起来，看一次完整问答的数据流：

```
用户通过飞书问："A基金的封闭期是多久？"
                                                        ┌──────────────┐
                                                        │  飞书客户端   │
                                                        └──────┬───────┘
                                                               │
                                                               ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  Step 1: 事件接收（bot_service）                                            │
│  飞书服务器把消息转发给我们的机器人，解析出 user_open_id 和问题内容            │
└────────────────────────────────────────────────────────────────────────────┘
                                                               │
                                                               ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  Step 2: 合规意图分类（rag_service）                                         │
│                                                                            │
│  判断问题是否涉及敏感词（净值、持仓、收益率...）                               │
│                                                                            │
│  ┌──────────┐    ┌─────────────────────────┐                               │
│  │ Redis    │───▶│ qualified_investors 表   │  ← PostgreSQL                  │
│  │ 缓存     │    │ 查该用户是否在白名单      │                               │
│  └──────────┘    └─────────────────────────┘                               │
│                                                                            │
│  如果用户不在白名单且问题涉及敏感词 → 直接返回合规话术，流程结束               │
└────────────────────────────────────────────────────────────────────────────┘
                                                               │
                                                               ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  Step 3: 权限拉取（rag_service）                                            │
│                                                                            │
│  ┌─────────────────────────┐                                               │
│  │ document_permissions 表  │  ← PostgreSQL                                  │
│  │ 查该用户能访问的 doc_id  │                                               │
│  └─────────────────────────┘                                               │
│                                                                            │
│  例如：用户是"新人"，只能看开放给所有人的文档                                  │
│       用户是"投资经理"，能看更多内部文档                                       │
└────────────────────────────────────────────────────────────────────────────┘
                                                               │
                                                               ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  Step 4: 向量化 + 语义检索（rag_service）                                     │
│                                                                            │
│  4.1 把问题转成向量                                                         │
│      ┌──────────────┐                                                      │
│      │ embed_query() │ → [0.234, -0.123, ...]                             │
│      │ (调用通义 API) │                                                      │
│      └──────────────┘                                                      │
│                                                                            │
│  4.2 去 Qdrant 检索，带 document_id 过滤                                    │
│      ┌──────────────┐                                                      │
│      │ search()     │                                                      │
│      │ top_k=8      │                                                      │
│      │ filter:      │                                                      │
│      │ doc_id in    │                                                      │
│      │ [允许的列表]  │                                                      │
│      └──────────────┘                                                      │
│                                                                            │
│  返回：8个最相关的文档片段 + 相似度分数                                       │
└────────────────────────────────────────────────────────────────────────────┘
                                                               │
                                                               ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  Step 5: LLM 生成回答（rag_service）                                         │
│                                                                            │
│  把检索到的 8 个文档片段 + 用户问题 组装成 Prompt，调用通义千问                │
│                                                                            │
│  Prompt 里会要求：                                                          │
│  - 严格基于提供的资料回答，不要编造                                           │
│  - 每个结论标注引用来源                                                       │
│  - 涉及投资相关内容必须加风险提示                                             │
└────────────────────────────────────────────────────────────────────────────┘
                                                               │
                                                               ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  Step 6: 合规扫描（rag_service）                                             │
│                                                                            │
│  检查回答中是否有违规词（保本、稳赚、零风险...）                               │
│  如果有 → 替换成 * 号，追加合规风险提示                                       │
└────────────────────────────────────────────────────────────────────────────┘
                                                               │
                                                               ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  Step 7: 审计落库（rag_service）                                            │
│                                                                            │
│  ┌─────────────────────────┐                                               │
│  │ chat_logs 表            │  ← PostgreSQL                                  │
│  │ 写入：                   │                                               │
│  │ - user_open_id          │                                               │
│  │ - question              │                                               │
│  │ - answer                │                                               │
│  │ - retrieved_chunks (JSON)│                                              │
│  │ - citations (JSON)      │                                               │
│  │ - latency_ms            │                                               │
│  │ - llm_model             │                                               │
│  │ - created_at            │                                               │
│  └─────────────────────────┘                                               │
│                                                                            │
│  数据持久化到 PG，供日后合规审计                                             │
└────────────────────────────────────────────────────────────────────────────┘
                                                               │
                                                               ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  Step 8: 返回结果给用户（bot_service）                                        │
│                                                                            │
│  渲染飞书消息卡片：                                                          │
│  - 答案正文                                                                 │
│  - 引用来源列表（可点击跳转原文档）                                           │
│  - 👍👎 反馈按钮                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. 为什么不用一种数据库解决所有问题

这是个好问题。理论上确实可以，但代价是**性能**和**复杂度**的取舍。

### 7.1 如果只用 PostgreSQL

| 方案 | 优点 | 缺点 |
|-----|-----|------|
| PG + JSONB 存向量 | 简单，一个数据库 | 向量检索极慢（10ms vs 1ms）|
| PG + pgvector | 稍好 | 数据量大了还是慢 |

### 7.2 如果只用 Redis

| 方案 | 优点 | 缺点 |
|-----|-----|------|
| Redis 存所有数据 | 快 | Redis 内存贵；不支持复杂查询；不支持向量检索 |

### 7.3 如果只用 Qdrant

| 方案 | 优点 | 缺点 |
|-----|-----|------|
| Qdrant 存所有数据 | 向量检索快 | 不擅长精确查询（查某个用户的对话记录）；不支持复杂 JOIN |

### 7.4 实际选择的理由

```
PostgreSQL          Qdrant               Redis
     │                  │                  │
     │ 擅长：            │ 擅长：            │ 擅长：
     │ - 精确查询        │ - 向量语义检索    │ - 微秒级读写
     │ - 复杂 JOIN       │ - 按字段过滤     │ - 临时状态
     │ - 数据持久化      │ - 相似度排序     │ - 缓存
     │ - 事务支持        │                  │
     │                  │                  │
     ▼                  ▼                  ▼
  文档元数据          文档片段            限流计数
  权限关系            向量检索            会话缓存
  审计日志            (语义搜索)          事件去重
```

三者各司其职，组合起来是当前性价比最高的方案。

---

## 8. 代码示例

### 8.1 PostgreSQL 操作示例

```python
from psycopg2 import connect

# 连接数据库
conn = connect("postgresql://pekb:pekb_dev_password@localhost:5432/pekb")

# 插入一条文档记录
with conn.cursor() as cur:
    cur.execute("""
        INSERT INTO documents (document_id, space_id, obj_type, title, path, chunk_count)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (document_id) DO UPDATE SET
            title = EXCLUDED.title,
            chunk_count = EXCLUDED.chunk_count,
            synced_at = NOW()
    """, ("doccn_xxxxx", "space_001", "docx", "A基金产品手册", "产品库/私募", 10))
    conn.commit()

# 查询某用户能访问的文档
with conn.cursor() as cur:
    cur.execute("""
        SELECT d.document_id, d.title
        FROM documents d
        JOIN document_permissions p ON d.document_id = p.document_id
        WHERE p.principal_id = %s AND d.status = 'active'
    """, ("ou_zhang_san",))
    results = cur.fetchall()
    print(results)  # [('doccn_001', 'A基金'), ('doccn_002', '合规手册')]

# 写入审计日志
with conn.cursor() as cur:
    cur.execute("""
        INSERT INTO chat_logs (session_id, user_open_id, user_name, question, answer, latency_ms)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, ("sess_001", "ou_zhang_san", "张三", "封闭期多久", "封闭期12个月...", 3200))
    conn.commit()

conn.close()
```

### 8.2 Qdrant 操作示例

```python
from qdrant_client import QdrantClient
from qdrant_client.http import models

# 连接
client = QdrantClient(url="http://localhost:6333")
collection = "pe_kb_chunks"

# 插入向量数据
client.upsert(
    collection_name=collection,
    points=[
        {
            "id": 1,
            "vector": [0.123, -0.456, ...],  # 1024维
            "payload": {
                "document_id": "doccn_xxxxx",
                "content": "私募基金在封闭期内不允许赎回...",
                "headings": ["A基金", "封闭期"],
                "title": "A基金产品手册"
            }
        },
        # ... 更多 points
    ]
)

# 语义检索（带权限过滤）
results = client.search(
    collection_name=collection,
    query_vector=[0.234, -0.123, ...],  # 问题的向量
    query_filter=models.Filter(
        must=[
            models.FieldCondition(
                key="document_id",
                match=models.MatchAny(any=["doccn_001", "doccn_002"])  # 权限过滤
            )
        ]
    ),
    limit=8  # 返回 top-8
)

# 打印结果
for result in results:
    print(f"分数: {result.score:.3f}")
    print(f"内容: {result.payload['content'][:50]}...")
    print(f"来源: {result.payload['title']}")
    print("---")
```

### 8.3 Redis 操作示例

```python
import redis
import json

r = redis.from_url("redis://localhost:6379/0")

# 限流示例
def check_rate_limit(user_id: str, max_requests: int = 3, window: int = 1) -> bool:
    key = f"rate_limit:{user_id}"
    count = r.get(key)

    if count and int(count) >= max_requests:
        return False  # 被限流

    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    pipe.execute()
    return True

# 会话上下文示例
def add_to_session(session_id: str, role: str, content: str):
    key = f"session:{session_id}"
    message = json.dumps({"role": role, "content": content})

    pipe = r.pipeline()
    pipe.lpush(key, message)
    pipe.ltrim(key, 0, 5)      # 只保留最近 3 条
    pipe.expire(key, 3600)      # 1小时过期
    pipe.execute()

def get_session_history(session_id: str) -> list:
    key = f"session:{session_id}"
    messages = r.lrange(key, 0, -1)
    return [json.loads(m) for m in messages]

# 缓存示例
def get_cached_answer(question_hash: str):
    key = f"cache:answer:{question_hash}"
    cached = r.get(key)
    return json.loads(cached) if cached else None

def cache_answer(question_hash: str, answer: dict, ttl: int = 300):
    key = f"cache:answer:{question_hash}"
    r.setex(key, ttl, json.dumps(answer))

# 事件去重示例
def is_duplicate_event(event_id: str, window: int = 600) -> bool:
    key = f"event:{event_id}"
    # set 成功返回 True（第一次），失败返回 None（重复）
    result = r.set(key, "1", "EX", window, "NX")
    return result is None
```

---

## 附录：快速命令参考

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 连接 PostgreSQL
docker exec -i pe-kb-postgres psql -U pekb -d pekb

# 查看 PostgreSQL 表
psql> \dt
psql> SELECT * FROM documents LIMIT 5;

# 测试 Redis
docker exec -i pe-kb-redis redis-cli PING
docker exec -i pe-kb-redis redis-cli KEYS "*"

# 访问 Qdrant Dashboard
# 浏览器打开 http://localhost:6333/dashboard

# 运行基础设施 smoke test
python tests/step4_smoke.py
```

---

**文档版本**: v1.0
**最后更新**: 2026-04-18
**相关文档**: [ARCHITECTURE.md](./ARCHITECTURE.md) | [ROADMAP.md](./ROADMAP.md)
