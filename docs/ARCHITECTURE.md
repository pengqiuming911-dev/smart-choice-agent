# 团队 LLM Wiki 知识库 — 完整设计文档

> 基于 Andrej Karpathy 提出的 LLM Wiki 模式，构建一个面向团队的、可持续维护的内部知识库系统。
>
> 适用规模：约 100 篇文档、10~30 人团队
> 文档版本：v1.2
> 最后更新：2026-04-26
>
> v1.1 更新：新增第七章"飞书文档定时同步"
> v1.2 更新：扩展第十章"技术栈推荐",增加完整前端选型与三大模块实现方案

---

## 一、为什么选 LLM Wiki 而不是 RAG

### 两种模式的核心区别

| 维度 | 传统 RAG | LLM Wiki |
|------|----------|----------|
| 知识形态 | 原始文档 + 向量索引 | LLM 编译后的结构化 markdown |
| 查询方式 | 每次重新检索原文片段 | LLM 先读索引，再读相关页面 |
| 知识积累 | 无积累，每次从零发现 | 持续沉淀，越用越完整 |
| 工程复杂度 | 需要向量数据库、embedding 管线 | 一个 Git 仓库 + LLM API |
| 适用规模 | 数千篇以上 | 中等规模（约 100~500 篇） |
| 可解释性 | 检索片段不连贯 | 每个结论可追溯到 wiki 页面和原始来源 |

### 为什么这个项目适合 LLM Wiki

- **规模匹配**：100 篇文档正好在 LLM Wiki 的甜蜜区
- **更新频率适中**：内部文档不是每分钟都在变，适合"编译"模式
- **追溯性要求高**：内部知识库需要让用户看到答案的依据
- **工程成本低**：不需要专门的 ML 团队维护向量管线

---

## 二、核心架构

### 整体三层架构

```
┌──────────────────────────────────────────────────────┐
│  Layer 3 — Schema 层(规则配置)                       │
│  CLAUDE.md / AGENTS.md                               │
│  告诉 LLM 如何摄入、查询、维护                       │
└──────────────────────┬───────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│  Layer 2 — Wiki 层(LLM 全权管理)                     │
│  ┌─────────────┐ ┌──────────┐ ┌──────────┐           │
│  │ 实体/概念页 │ │ index.md │ │ log.md   │           │
│  │ 带反向链接  │ │ 全局索引 │ │ 时间日志 │           │
│  └─────────────┘ └──────────┘ └──────────┘           │
└──────────────────────┬───────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│  Layer 1 — Raw 层(只读事实源)                        │
│  飞书文档 · Excel 表 · PDF · 会议纪要                │
└──────────────────────────────────────────────────────┘
```

### 三个核心操作

| 操作 | 触发方 | 说明 |
|------|--------|------|
| **ingest** | 管理员上传 / 定时同步 | LLM 阅读原文 → 提取实体/概念 → 创建/更新 wiki 页面 → 更新 index.md |
| **query** | 用户提问 | LLM 读 index.md 找相关页面 → 深读 → 综合回答 → 好答案归档为新页面 |
| **lint** | 定时任务 | LLM 检查矛盾、断链、孤立页面、知识空白 |

---

## 三、云端架构详解

### 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│  用户层                                                 │
│  浏览器 / 飞书机器人 / 管理员后台                       │
└────────────────────────┬────────────────────────────────┘
                         ↓ HTTPS
┌─────────────────────────────────────────────────────────┐
│  应用层(ECS)                                            │
│  Web 前端 ──→ API 服务 ──→ Wiki Agent                   │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌──────────────────────┐ ┌────────────────────────────────┐
│  数据层              │ │  外部服务                      │
│  Wiki Git 仓库       │ │  飞书 API(同步源文档)          │
│  PostgreSQL(运营)    │ │  Claude / DeepSeek API(推理)   │
└──────────────────────┘ └────────────────────────────────┘
```

### 各模块职责说明

#### 用户层

| 入口 | 适用场景 | 实现方式 |
|------|----------|----------|
| Web 浏览器 | 主要使用场景，问答 + 浏览 wiki | 前端 SPA |
| 飞书机器人 | 群聊里 @ 机器人快速提问 | 飞书开放平台 webhook |
| 管理员后台 | 上传文档、审核内容、查看统计 | 同前端,带角色路由 |

#### 应用层

| 服务 | 技术选型推荐 | 部署位置 |
|------|--------------|----------|
| Web 前端 | Next.js / Nuxt | ECS(Nginx 托管) |
| API 服务 | FastAPI(Python)或 NestJS(Node) | ECS |
| Wiki Agent | Python 脚本 + Claude SDK | ECS,常驻进程或定时任务 |

**Wiki Agent 核心职责**:
- 接收 ingest 任务,调用 LLM 处理新文档,把结果写回 Git
- 接收 query 任务,调用 LLM 综合答案,记录到问答历史
- 定时跑 lint 任务,生成健康检查报告
- 对接飞书 API,定时同步源文档到 raw/

#### 数据层

**Wiki Git 仓库**(挂载在 ECS 数据盘)

```
wiki-repo/
├── raw/                    # 原始文档(只读)
│   ├── articles/
│   ├── pdfs/
│   └── meeting-notes/
├── wiki/                   # LLM 生成的 markdown
│   ├── index.md            # 全局目录
│   ├── log.md              # 时间日志
│   ├── entities/           # 实体页(产品、客户、人员)
│   ├── concepts/           # 概念页(术语、流程、政策)
│   └── overviews/          # 综合页(月报、主题汇总)
├── CLAUDE.md               # Schema 配置
└── .git/
```

每次 LLM 修改 wiki 自动 `git commit`,完整版本历史白送。

**PostgreSQL**(运营数据)

```sql
-- 用户表
users (id, email, role, dept, created_at)

-- 问答历史
queries (id, user_id, question, answer, sources, feedback, created_at)

-- 文档同步状态
documents (id, source_url, last_synced, ingested_at, version)

-- 权限规则
access_rules (page_path, required_role, dept_restriction)
```

---

## 四、关键设计决策

### 1. 权限分级

**为什么需要**:内部知识库通常涉及敏感内容(薪酬、客户、战略)。

**建议三级模型**:

| 级别 | 可见范围 | 典型内容 |
|------|----------|----------|
| public | 全员 | 产品文档、规章制度、常识问答 |
| dept-* | 部门内 | 销售话术、技术方案、内部 SOP |
| admin | 少数人 | 财务数据、薪酬结构、战略规划 |

**实现方式**:每篇 wiki 页面 frontmatter 标注访问级别:

```yaml
---
title: Q3 销售目标
access: dept-sales
created: 2026-04-01
sources: [飞书文档/2026Q3规划.docx]
---
```

API 查询时按用户角色过滤,LLM 阅读时也只能访问授权页面。

### 2. 摄入策略

**100 篇文档建议先手动**:管理员后台上传 → 触发 ingest 任务。

**为什么不一开始就自动**:
- 自动同步会把噪音文档(草稿、临时记录)吸进来,污染知识库
- 人工策展是 LLM Wiki 的核心理念 — 人决定什么进知识库,LLM 负责整理
- 流程跑顺后再加自动化

**第二阶段加自动同步**:
- 飞书文档:用 Open API 定时拉取(每天凌晨)
- 文档变更:对比 hash,变了就触发增量 ingest
- 新建文档:管理员审核通过后才入库

### 3. 查询返回结构

**不要只返回一段话答案**。学 NotebookLM 的设计:

```json
{
  "answer": "Q3 华东区销售目标是 2400 万,比 Q2 增长 15%...",
  "wiki_pages": [
    {"title": "Q3 销售目标", "url": "/wiki/entities/q3-sales-goal"},
    {"title": "华东区运营", "url": "/wiki/entities/east-china"}
  ],
  "raw_sources": [
    {"title": "2026Q3规划.docx", "url": "feishu://docs/xxx"}
  ],
  "confidence": "high"
}
```

**好处**:
- 用户能追溯到原文,信任度高
- 答案不对时一键查原文
- 引用的 wiki 页面可以直接展开看

### 4. 是否需要向量检索兜底

**100 篇规模**:不需要。LLM 直接读 index.md(几千 token)就能找到相关页面。

**500 篇以上**:建议加一层向量检索作为**召回层**,给 LLM 缩小阅读范围。这是 LLM Wiki 和 RAG 的混合,工程上叫 "agentic RAG"。

---

## 五、阿里云资源配置

### 资源清单(按量付费)

| 资源 | 规格 | 月费用 | 备注 |
|------|------|--------|------|
| ECS | 2核4G, Ubuntu 24 | ¥80~120 | 应用 + Agent 共用 |
| 数据盘 ESSD | 40G | ¥20 | Git 仓库 + 日志 |
| RDS PostgreSQL | 1核1G(最低配) | ¥60 | 可选,自建可省 |
| EIP | 5Mbps 按流量 | ¥30~50 | 视访问量 |
| 域名 | .com | ¥60/年 | 摊到月约 5 元 |
| HTTPS 证书 | Let's Encrypt | 免费 | |
| **基础设施小计** | | **约 ¥200/月** | |

### LLM API 费用估算

| 用量 | 单次成本 | 月度估算 |
|------|----------|----------|
| 100 篇文档初次摄入 | 约 ¥30~50 | 一次性 |
| 单次 query(含读 index + 深读) | 约 ¥0.3~0.8 | - |
| 每天 100 次查询(30 人团队) | - | 约 ¥100~200 |
| 每周 lint 健康检查 | 约 ¥20 | 约 ¥80 |
| **LLM 调用小计** | | **约 ¥200~300/月** |

**成本优化方案**:
- 用 DeepSeek 替代 Claude:成本降到 1/5
- 简单问题用便宜模型(Haiku),复杂问题用 Opus
- 缓存常见问题答案,避免重复调用
- 优化 prompt 长度,index.md 控制在 3000 字以内

### 总月度成本

| 团队规模 | 基础设施 | LLM API | 总计 |
|----------|----------|---------|------|
| 10 人轻度使用 | ¥200 | ¥100 | **¥300/月** |
| 30 人中度使用 | ¥200 | ¥300 | **¥500/月** |
| 50+ 人重度使用 | ¥400 | ¥600 | **¥1000/月** |

---

## 六、上线路径

### Phase 1(2 周)— 内部 MVP

**目标**:验证 LLM Wiki 生成的内容质量是否达标

**任务**:
- [ ] 本地把 LLM Wiki 跑通(Claude Code + Obsidian)
- [ ] 选 10 篇代表性文档手动 ingest,检查输出
- [ ] 部署到 ECS,域名解析,HTTPS
- [ ] 实现最简单的登录 + 问答页面
- [ ] 邀请 3~5 个种子用户试用,收集反馈

**关键指标**:种子用户提的 10 个问题里,LLM Wiki 能答对几个?

### Phase 2(1 个月)— 内部产品化

**目标**:让 30 人团队都能自助使用

**任务**:
- [ ] 实现三级权限分级
- [ ] 管理员后台:上传文档、审核、查统计
- [ ] 问答历史 + 反馈按钮(👍/👎)
- [ ] 飞书机器人接入(群里 @ 机器人提问)
- [ ] **飞书 Cron 同步(每天凌晨拉高频空间,详见第七章)**
- [ ] 100 篇文档全部 ingest 完成
- [ ] 编写运维文档和 Schema 规范

### Phase 3(持续)— 精细化运营

**任务**:
- [ ] 每周自动 lint,生成健康报告给管理员
- [ ] 高频问题答案自动归档为 wiki 新页面(知识复利)
- [ ] 文档热度监控:哪些被引用多、哪些没人看
- [ ] **升级到 Celery + Webhook 实时同步(详见第七章)**
- [ ] 定期 schema 调优(根据使用反馈)

---

## 七、飞书文档定时同步

定时同步是 LLM Wiki 长期运转的关键。本章描述如何把飞书团队空间的文档自动同步到知识库,保持内容时新。

### 同步流程总览

```
飞书团队空间
    ↓ (定时拉取 / 实时推送)
飞书 Open API
    ↓ (对比版本 hash)
变更检测器
    ↓ (有变化才触发)
Ingest 任务队列
    ↓ (LLM 处理)
Wiki 仓库更新
    ↓ (自动 commit)
Git 历史 + 通知管理员
```

### 1. 飞书开放平台权限申请

去飞书开放平台 `open.feishu.cn` 创建**企业自建应用**(不是机器人)。

需要申请的权限范围:

| 权限 | 用途 |
|------|------|
| `wiki:wiki:readonly` | 读知识空间列表和节点树 |
| `docx:document:readonly` | 读新版文档(docx)内容 |
| `drive:drive:readonly` | 读云空间文件列表 |
| `sheets:spreadsheet:readonly` | 读 Excel 表格(可选) |

申请通过后会拿到 `App ID` 和 `App Secret`,务必存到 ECS 环境变量,**禁止提交到 Git**。

### 2. 同步频率分级策略

不同类型文档变化频率差异很大,建议按重要性和变化频率分级:

| 类型 | 典型内容 | 同步频率 | 触发方式 |
|------|----------|----------|----------|
| 高频变化 | 产品文档、SOP、技术方案 | 每天凌晨 1 次 | Cron 定时 |
| 低频变化 | 规章制度、组织架构、归档资料 | 每周 1 次 | Cron 定时 |
| 关键文档 | 公告、紧急通知、重大变更 | 实时 | 飞书 Webhook 推送 |

**为什么不全部用实时同步?**
- Webhook 需要公网可达 + HTTPS,部署成本更高
- 大部分文档不需要分钟级更新
- 实时同步会触发频繁的 LLM 调用,成本上升

**为什么不全部用每日 Cron?**
- 公告类文档可能上午发,下午就要全员知道
- 每日批量处理时容易触发飞书 API 限流

### 3. Cron 定时任务实现

最简单的方案就是 ECS 上写 Python 脚本 + crontab。

#### 3.1 同步脚本骨架

```python
# /opt/wiki/sync/sync_main.py
import os
import sys
from datetime import datetime
from feishu_client import FeishuClient
from db import documents_db
from agent import trigger_ingest

def sync_feishu_space(space_id, space_type='high-freq'):
    client = FeishuClient(
        app_id=os.getenv('FEISHU_APP_ID'),
        app_secret=os.getenv('FEISHU_APP_SECRET')
    )

    # 1. 拉取知识空间所有节点(递归)
    remote_docs = client.list_wiki_nodes(space_id)

    stats = {'new': 0, 'updated': 0, 'archived': 0, 'failed': 0}

    # 2. 对比本地状态
    for doc in remote_docs:
        local = documents_db.get(doc.token)

        try:
            if not local:
                # 新文档 → 拉取 + 入库 + 触发 ingest
                content = client.get_document_content(doc.token)
                save_to_raw(doc, content)
                trigger_ingest(doc.token, action='create')
                stats['new'] += 1

            elif local.last_modified < doc.last_modified:
                # 时间戳变了 → 拉内容对比 hash,避免无意义 ingest
                content = client.get_document_content(doc.token)
                new_hash = md5(content)
                if new_hash != local.content_hash:
                    save_to_raw(doc, content)
                    trigger_ingest(doc.token, action='update')
                    stats['updated'] += 1
        except Exception as e:
            stats['failed'] += 1
            log_error(doc.token, e)

    # 3. 检测删除(飞书已删的标记为 archived,不真删 wiki 页面)
    remote_tokens = {d.token for d in remote_docs}
    for local in documents_db.list_all(space_id=space_id):
        if local.token not in remote_tokens:
            trigger_ingest(local.token, action='archive')
            stats['archived'] += 1

    # 4. 写同步报告
    write_sync_report(space_id, space_type, stats)

if __name__ == '__main__':
    space_type = sys.argv[1] if len(sys.argv) > 1 else 'high-freq'
    spaces = config.get_spaces(space_type)
    for space in spaces:
        sync_feishu_space(space.id, space_type)
```

#### 3.2 Crontab 配置

```bash
# 在 ECS 上编辑当前用户的定时任务
crontab -e

# 高频空间:每天凌晨 2 点同步
0 2 * * * /usr/bin/python3 /opt/wiki/sync/sync_main.py high-freq >> /var/log/wiki-sync-high.log 2>&1

# 低频空间:每周一凌晨 3 点同步
0 3 * * 1 /usr/bin/python3 /opt/wiki/sync/sync_main.py low-freq >> /var/log/wiki-sync-low.log 2>&1

# 每月 1 号凌晨 4 点跑 lint 健康检查
0 4 1 * * /usr/bin/python3 /opt/wiki/sync/lint.py >> /var/log/wiki-lint.log 2>&1
```

**几个细节**:
- 选凌晨执行,避开飞书 API 限流和 LLM 调用高峰
- 高频和低频分开时间,避免互相阻塞
- 日志单独输出,方便排查
- 时间错开 1 小时,防止任务重叠

#### 3.3 用 Celery 替代 Cron(团队成熟后)

任务量上来后,Cron 缺乏重试、监控、并发控制等能力。建议升级到 Celery + Redis:

```python
# tasks.py
from celery import Celery
from celery.schedules import crontab

app = Celery('wiki', broker='redis://localhost:6379')

@app.task(bind=True, max_retries=3)
def sync_feishu_doc(self, doc_token):
    try:
        client = FeishuClient(...)
        content = client.get_document_content(doc_token)
        save_to_raw(doc_token, content)
        trigger_ingest.delay(doc_token)
    except Exception as e:
        # 指数退避重试: 1min → 2min → 4min
        raise self.retry(exc=e, countdown=2 ** self.request.retries * 60)

# 定时配置
app.conf.beat_schedule = {
    'sync-high-freq-daily': {
        'task': 'tasks.sync_all_spaces',
        'schedule': crontab(hour=2, minute=0),
        'kwargs': {'space_type': 'high-freq'}
    },
    'sync-low-freq-weekly': {
        'task': 'tasks.sync_all_spaces',
        'schedule': crontab(hour=3, minute=0, day_of_week=1),
        'kwargs': {'space_type': 'low-freq'}
    },
}
```

启动方式:

```bash
# 启动 worker
celery -A tasks worker --loglevel=info

# 启动定时调度器
celery -A tasks beat --loglevel=info
```

**Celery 比 Cron 的好处**:失败自动重试、任务并行、Web 界面看任务状态(Flower)、支持优先级队列。

### 4. 增量同步策略

#### 文档状态表设计

PostgreSQL 中维护每个文档的同步状态:

```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    feishu_token VARCHAR(64) UNIQUE NOT NULL,
    space_id VARCHAR(64) NOT NULL,
    title VARCHAR(255),
    last_modified TIMESTAMP,           -- 飞书侧最后修改时间
    content_hash VARCHAR(32),          -- 内容 MD5
    last_ingested_at TIMESTAMP,        -- 最后一次 ingest
    status VARCHAR(20) DEFAULT 'synced', -- synced/pending/failed/archived
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_space ON documents(space_id);
CREATE INDEX idx_status ON documents(status);
```

#### 三种变更场景

| 场景 | 检测方式 | 处理动作 |
|------|----------|----------|
| 新文档 | 飞书有,本地无 | 拉内容 → 入 raw/ → 触发 ingest |
| 已更新 | last_modified 变了且 hash 不同 | 拉内容 → 覆盖 raw/ → 触发 ingest |
| 已删除 | 飞书 API 找不到了 | 标记 archived,不删 wiki 页面 |

**为什么删除要用软标记?**
飞书侧的删除可能是误操作,直接删 wiki 页面会丢失历史。标记 archived 后:
- wiki 页面仍可访问,但加"原文已归档"提示
- 30 天后管理员审核确认,再决定是否真删
- Git 历史永久保留,任何时候可恢复

### 5. 飞书 API 调用要点

#### 5.1 Token 缓存

`tenant_access_token` 默认有效期 2 小时,频繁请求会被限流:

```python
def get_access_token():
    token = redis.get('feishu:tenant_token')
    if not token:
        token = fetch_new_token()
        # 留 200 秒余量,避免临界过期
        redis.setex('feishu:tenant_token', 7000, token)
    return token
```

#### 5.2 知识空间是树结构

需要递归拉取所有节点:

```python
def list_wiki_nodes(space_id, parent_token=None):
    nodes = []
    page_token = None
    while True:
        resp = api.get(
            f'/wiki/v2/spaces/{space_id}/nodes',
            params={'parent_node_token': parent_token,
                    'page_token': page_token}
        )
        nodes.extend(resp['items'])

        # 递归子节点
        for item in resp['items']:
            if item['has_child']:
                nodes.extend(list_wiki_nodes(space_id, item['node_token']))

        page_token = resp.get('page_token')
        if not page_token:
            break
    return nodes
```

#### 5.3 docx 转 markdown

飞书新版文档(docx)是 block 结构,不是 markdown。建议用现成的开源库:

- `feishu2md` (`github.com/Wsine/feishu2md`)
- `lark-doc-parser` (官方 SDK)

自己写转换器很容易踩各种格式坑(嵌套列表、表格、图片、代码块)。

#### 5.4 频率限制

飞书 API 默认 QPS 限制(一般 50/秒),批量同步要加节流:

```python
import time

for doc in docs:
    process(doc)
    time.sleep(0.05)  # 20 QPS,留余量
```

### 6. 实时同步(可选,Phase 3)

对公告、紧急通知等高时效内容,用 Webhook 实时推送:

```python
# FastAPI endpoint
@app.post('/webhook/feishu')
async def feishu_webhook(request):
    # 1. 验证签名
    if not verify_signature(request):
        return {'error': 'invalid signature'}

    event = await request.json()

    # 2. 异步触发同步任务
    if event['type'] == 'docx.document.updated_v1':
        doc_token = event['data']['document_id']
        sync_feishu_doc.delay(doc_token)

    return {'code': 0}
```

**前置条件**:
- ECS 必须有公网可达的 HTTPS 地址
- 飞书开放平台后台配置事件订阅 URL
- 验证签名防止伪造请求

订阅的事件类型:

| 事件 | 用途 |
|------|------|
| `docx.document.updated_v1` | 文档内容更新 |
| `wiki.space.node_changed_v1` | 知识空间节点变化(新增/删除/移动) |

### 7. 同步质量保障

#### 7.1 同步报告

每次同步后生成结构化报告:

```python
sync_report = {
    'timestamp': '2026-04-26T02:00:00',
    'space_id': 'wiki_xxx',
    'space_type': 'high-freq',
    'total_docs': 120,
    'new': 3,
    'updated': 8,
    'archived': 1,
    'failed': 0,
    'duration_sec': 145,
    'llm_tokens_used': 35000,
    'cost_estimate_yuan': 12.5
}
```

存入 PostgreSQL,**每周给管理员发邮件汇总**。

#### 7.2 失败分类与处理

| 失败类型 | 处理方式 |
|----------|----------|
| 网络超时 | 自动重试 3 次,指数退避 |
| 权限不足 | 跳过文档,记录日志,通知管理员 |
| 内容解析失败 | 保留原始 raw 内容,标记 parse_failed,人工介入 |
| LLM 调用失败 | 进入死信队列,下次同步优先处理 |
| 飞书 API 限流 | 降速,等待后重试 |

#### 7.3 防止"同步风暴"

如果飞书一次更新了 50 篇文档,不要同时丢 50 个 ingest 任务给 LLM——会触发 API 限流而且费钱:

```python
# 错误做法:同时触发
for doc in updated_docs:
    ingest.delay(doc)  # 50 个任务并发

# 正确做法:串行 + 限速
from celery import group
chord = group(
    ingest.s(doc).set(countdown=i * 30)  # 每 30 秒一个
    for i, doc in enumerate(updated_docs)
)
chord.apply_async()
```

### 8. 同步目录结构建议

```
/opt/wiki/
├── sync/
│   ├── feishu_client.py       # 飞书 API 封装
│   ├── differ.py              # 变更检测
│   ├── parser.py              # docx → markdown 转换
│   └── sync_main.py           # 主同步脚本
├── tasks/
│   ├── celery_app.py
│   ├── ingest.py              # ingest 任务
│   └── lint.py                # lint 任务
├── webhook/
│   └── feishu_webhook.py      # 飞书事件接收(Phase 3)
├── wiki-repo/                 # Git 仓库(挂数据盘)
│   ├── raw/
│   ├── wiki/
│   └── CLAUDE.md
├── logs/
└── .env                       # 凭证(不提交 Git)
```

### 9. 迭代节奏建议

不要一上来就搞 Celery + Webhook + 实时推送的完整方案,先用最土的 Cron 跑通验证价值:

| 时间 | 任务 |
|------|------|
| Week 1 | Cron + Python 脚本跑通最简同步,1 个核心知识空间,每天凌晨拉一次 |
| Week 2 | 加变更检测(hash 对比),避免重复 ingest 浪费钱 |
| Week 3-4 | 扩展到所有空间,加监控和报警邮件 |
| Month 2 | 升级到 Celery,加重试和并发控制 |
| Month 3+ | 如有实时性需求,加 Webhook 实时同步关键文档 |

**第一步动作**:把"飞书 API 调通拿到一篇文档的 markdown"这个最小动作做完。这步打通了,后面的同步逻辑都是水到渠成的事。

---

## 八、运维与监控

### 必备监控指标

| 指标 | 阈值 | 行动 |
|------|------|------|
| 查询响应时间 | P95 < 5s | 超过排查 LLM 调用 |
| 查询成功率 | > 95% | 低于检查 API 配额 |
| 用户反馈准确率 | 👍 > 70% | 低于审视 schema 和 ingest 质量 |
| LLM API 月度消耗 | < 预算 120% | 超过排查异常调用 |
| 知识库矛盾数(lint) | 月增 < 10 | 超过人工介入 |

### 备份策略

- **Git 仓库**:每日 push 到内部 GitLab 或私有 GitHub 备份
- **PostgreSQL**:阿里云 RDS 自动每日快照,保留 7 天
- **原始文档**:OSS 冷备份,长期保存

### 安全要点

- ECS 关闭非必要端口,只开 80/443/22
- SSH 强制密钥登录,禁用密码
- API 接口全部经过登录鉴权
- 飞书 webhook 校验签名
- 敏感日志脱敏(用户 query 不记录手机号、邮箱等)

---

## 九、常见误区警示

### 1. "先做完美 UI 再上线"

很多团队上来就想做漂亮的产品页,搞精美的图表。结果三个月后发现:**用户不在乎 UI,在乎答案准不准**。

正确做法:Phase 1 用最简陋的 UI,先把"问题 → 准答案"闭环跑通。

### 2. "把所有文档都塞进去"

把过期的、草稿、临时记录全部 ingest,结果 LLM 回答时引用错误信息。

正确做法:**人工策展**。管理员审核每一篇是否值得入库。Karpathy 强调:**人决定来源,LLM 负责记账**。

### 3. "等 LLM 生成完美的页面"

LLM 写的 wiki 页面不会一步到位完美。如果你纠结于"必须每个字都对",会陷入无穷调优。

正确做法:接受 80% 准确度起步,通过用户反馈和 lint 持续改进。

### 4. "只重 ingest 不重 query"

很多人花大力气把文档塞进去,但忽视了查询体验。结果用户问完一次就不来了。

正确做法:**查询是入口**。投入精力优化:答案展示、源文档跳转、反馈机制、追问能力。

### 5. "想用一套系统满足所有人"

技术部门想要技术细节,销售要客户案例,HR 要规章制度。一套通用 wiki 难以满足。

正确做法:**用 schema 区分领域**。可以一个仓库多个子目录,或多个独立 wiki 共享底层架构。

---

## 十、技术栈推荐

### 整体技术栈分层

```
┌─────────────────────────────────────────────────┐
│  业务层 — 三大核心模块                          │
│  飞书登录 · 智能体问答 · 日历模块               │
├─────────────────────────────────────────────────┤
│  UI 组件层                                      │
│  Ant Design Pro 5.x + Ant Design X(AI 组件)     │
├─────────────────────────────────────────────────┤
│  框架与状态管理                                 │
│  Next.js 15 + TanStack Query + Zustand          │
├─────────────────────────────────────────────────┤
│  基础设施层                                     │
│  TypeScript 5 + pnpm + Tailwind CSS             │
└─────────────────────────────────────────────────┘
```

### 1. 前端技术栈

#### 1.1 框架层:Next.js 15(App Router)

**为什么不是 Vite + React SPA?**

企业内部系统常被忽略的需求:首屏速度、服务端渲染敏感数据、Streaming UI。Next.js 15 的 App Router + React Server Components 已经成熟,是目前最适合企业级应用的 React 框架。

特别是**智能体问答页**需要流式输出(LLM 一边生成一边显示),Next.js 的 Streaming SSR 和 Server Actions 配合 Vercel AI SDK 能让流式实现非常优雅。

**为什么不是 Vue/Nuxt?**

如果团队是 Vue 背景,Nuxt 3 也没问题。但 React 生态在 AI 应用方向(Vercel AI SDK、LangChain.js、各种 LLM UI 库)领先 Vue 至少一年。新项目用 React 选择更多。

#### 1.2 UI 组件库:Ant Design Pro 5.x + Ant Design X

**为什么不是 shadcn/ui?**

shadcn/ui 在创业项目和 To C 应用上是首选(美观、可定制、社区活跃)。但对企业内部系统:

- **稳定和功能完整优先**:复杂表单、数据表格、权限菜单、国际化这些 shadcn 都得自己拼
- **Ant Design Pro 自带完整脚手架**:登录页、布局、菜单、面包屑、主题切换、国际化、权限路由全都现成
- **团队上手快**:国内 90% 的前端工程师都熟悉 Ant Design

**Ant Design X 强烈推荐**(蚂蚁刚出的 AI 应用组件库),专为智能体页面设计:

| 组件 | 用途 |
|------|------|
| `Bubble` | 对话气泡(用户消息 + AI 回复) |
| `Sender` | 输入框(支持快捷键、附件) |
| `ThoughtChain` | 思考链展示(显示 LLM 推理过程) |
| `Suggestion` | 推荐问题(引导用户提问) |
| `Conversations` | 历史会话列表 |

**关于 Tailwind CSS**:和 Ant Design 不冲突,Ant Design 管业务组件,Tailwind 处理 layout 和细节调整。

#### 1.3 状态管理:TanStack Query + Zustand

**核心理念**:服务端状态和客户端状态分开管理。

| 状态类型 | 工具 | 例子 |
|----------|------|------|
| 服务端数据(API 返回) | TanStack Query | 用户信息、wiki 页面、问答历史、日历事件 |
| 客户端 UI 状态 | Zustand | 侧边栏开关、主题、当前选中项 |

**为什么不用 Redux?**

Redux 太重了,企业级也没必要。Redux Toolkit 可以接受,但 Zustand 的代码量是 Redux 的 1/3,学习成本是 1/5。

**为什么 TanStack Query 是必选?**

它解决了所有前端都头疼的问题:API 数据的缓存、失效、重试、轮询。比如用户切换页面又切回来是否要重新请求、多个组件请求同一个接口如何去重——这些 TanStack Query 自动处理。

### 2. 三大核心模块的实现方案

#### 2.1 飞书登录认证

**推荐:飞书 OAuth 2.0 网页授权 + NextAuth.js (Auth.js v5)**

**流程**:

```
用户点击"飞书登录"
  ↓ 跳转到飞书授权页(https://open.feishu.cn/open-apis/authen/v1/index)
用户同意授权
  ↓ 飞书回调到你的 callback URL 带 code
后端用 code 换 access_token,再换用户信息
  ↓ 生成 JWT 存到 httpOnly cookie
跳转回应用
```

**自定义 Feishu Provider 示例**:

```typescript
// providers/feishu.ts
import type { OAuthConfig } from "next-auth/providers"

export default function FeishuProvider(config): OAuthConfig {
  return {
    id: "feishu",
    name: "Feishu",
    type: "oauth",
    authorization: {
      url: "https://open.feishu.cn/open-apis/authen/v1/index",
      params: { app_id: config.appId, redirect_uri: config.redirectUri }
    },
    token: "https://open.feishu.cn/open-apis/authen/v1/access_token",
    userinfo: "https://open.feishu.cn/open-apis/authen/v1/user_info",
    profile(profile) {
      return {
        id: profile.union_id,
        name: profile.name,
        email: profile.email,
        image: profile.avatar_url,
        deptId: profile.dept_id,
      }
    },
    clientId: config.appId,
    clientSecret: config.appSecret,
  }
}
```

**关键安全设计**:

| 设计点 | 做法 | 原因 |
|--------|------|------|
| Token 存储 | httpOnly cookie | 防 XSS 偷 token |
| 前端存储 | 不直接存 token | 避免 localStorage 被注入读取 |
| 权限缓存 | 写进 JWT payload | 避免每次请求都查数据库 |
| 自动刷新 | access_token 快过期时静默刷新 | 用户无感 |

#### 2.2 智能体问答页

**推荐:Ant Design X + Vercel AI SDK**

要实现的核心能力:
- 流式输出(一个字一个字蹦出来)
- 引用 wiki 页面和原始飞书文档(点击可跳转)
- 多轮对话历史
- Markdown 渲染(含代码高亮、表格、图片)
- 反馈按钮(👍/👎 + 文字反馈)

**核心代码示例**(简化版):

```typescript
'use client'
import { useChat } from 'ai/react'
import { Bubble, Sender, ThoughtChain } from '@ant-design/x'

export default function ChatPage() {
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: '/api/chat',  // 后端流式接口
    onFinish: (message) => {
      // 自动归档高质量回答到 wiki(后端逻辑)
    }
  })

  return (
    <div className="flex flex-col h-screen">
      <div className="flex-1 overflow-y-auto p-4">
        {messages.map(m => (
          <Bubble
            key={m.id}
            content={<MarkdownRenderer content={m.content} />}
            placement={m.role === 'user' ? 'end' : 'start'}
            footer={m.role === 'assistant' && (
              <CitationList sources={m.sources} />
            )}
          />
        ))}
        {isLoading && <ThoughtChain items={[{title: '正在检索知识库...'}]} />}
      </div>
      <Sender
        value={input}
        onChange={handleInputChange}
        onSubmit={handleSubmit}
        loading={isLoading}
      />
    </div>
  )
}
```

**Markdown 渲染推荐**:
- `react-markdown` + `remark-gfm`(基础表格、任务列表)
- `rehype-highlight`(代码高亮)
- `rehype-katex`(数学公式,如果需要)

**引用展示设计**:答案下方折叠面板,展开后显示:
- 引用的 wiki 页面(带跳转链接)
- 引用的原始飞书文档(点击跳转飞书)
- 置信度标识(高/中/低)

#### 2.3 日历模块

**推荐:FullCalendar React**

```bash
pnpm add @fullcalendar/react @fullcalendar/daygrid @fullcalendar/timegrid @fullcalendar/interaction
```

**为什么不用 Ant Design Calendar?**

Ant Design 自带的 Calendar 太基础,只能做"日期选择器"级别的展示。FullCalendar 是日历领域的工业标准:

- **多视图**:月视图、周视图、日视图、议程视图
- **拖拽**:直接拖动事件改时间
- **资源管理**:多人/多会议室的时间线视图
- **国际化**:开箱即用的中文支持
- **打印**:支持打印日历

**和飞书日历集成**:

```typescript
// 同步飞书日历事件
async function syncFeishuCalendar(userId: string) {
  const events = await feishuClient.calendar.events.list({
    calendar_id: 'primary',
    start_time: startOfMonth(),
    end_time: endOfMonth(),
  })

  return events.map(e => ({
    id: e.event_id,
    title: e.summary,
    start: e.start_time,
    end: e.end_time,
    extendedProps: {
      attendees: e.attendees,
      location: e.location,
    }
  }))
}
```

**业务集成点**:
- 知识库里某些 wiki 页面绑定到日历(如"周会纪要"自动出现在每周一日历上)
- 智能体可以基于日历回答"明天的会议有哪些资料?"

### 3. 前端项目结构

```
wiki-frontend/
├── app/                        # Next.js 15 App Router
│   ├── (auth)/
│   │   ├── login/             # 飞书登录页
│   │   └── callback/          # OAuth 回调
│   ├── (main)/                # 登录后的主区域
│   │   ├── chat/              # 智能体问答
│   │   ├── wiki/              # Wiki 浏览
│   │   ├── calendar/          # 日历
│   │   └── admin/             # 管理后台
│   ├── api/
│   │   ├── auth/[...nextauth] # NextAuth 路由
│   │   ├── chat/              # 流式聊天接口
│   │   └── webhook/feishu/    # 飞书 webhook
│   └── layout.tsx
├── components/
│   ├── chat/                  # 问答相关组件
│   ├── wiki/                  # Wiki 渲染组件
│   ├── calendar/              # 日历组件
│   └── common/                # 通用组件
├── lib/
│   ├── feishu/                # 飞书 SDK 封装
│   ├── api/                   # API 客户端
│   └── utils/
├── stores/                    # Zustand stores
├── hooks/                     # 自定义 hooks
└── types/                     # TypeScript 类型
```

### 4. 完整依赖清单

```json
{
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "antd": "^5.21.0",
    "@ant-design/x": "^1.0.0",
    "@ant-design/pro-components": "^2.7.0",
    "next-auth": "^5.0.0-beta",
    "@tanstack/react-query": "^5.59.0",
    "zustand": "^5.0.0",
    "ai": "^4.0.0",
    "@fullcalendar/react": "^6.1.0",
    "@fullcalendar/daygrid": "^6.1.0",
    "@fullcalendar/timegrid": "^6.1.0",
    "react-markdown": "^9.0.0",
    "remark-gfm": "^4.0.0",
    "rehype-highlight": "^7.0.0",
    "axios": "^1.7.0",
    "dayjs": "^1.11.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.6.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "eslint": "^9.0.0",
    "eslint-config-next": "^15.0.0",
    "prettier": "^3.3.0",
    "husky": "^9.1.0",
    "lint-staged": "^15.2.0"
  }
}
```

### 5. 后端技术栈

#### MVP 版本

```
后端框架: FastAPI(Python 3.11+)
ORM:      SQLAlchemy 2.0
异步任务: 内置 BackgroundTasks
LLM:      Anthropic Claude API(claude-sonnet-4-6)
存储:     Git 仓库 + PostgreSQL
部署:     阿里云 ECS + Nginx + Docker Compose
监控:     Uptime Robot(免费)
```

#### 进阶版本(团队成熟后)

```
后端框架: FastAPI + Celery(异步任务队列)
缓存:     Redis(会话 + Token + 任务队列)
LLM:      Claude(主)+ DeepSeek(降本)+ 本地嵌入模型
存储:     Git + PostgreSQL + Redis + OSS(原始文档)
部署:     阿里云 ECS + 容器服务 ACK(可选)
监控:     Prometheus + Grafana + Sentry
日志:     ELK 或阿里云 SLS
```

### 6. 企业级要点清单

不要漏掉这些细节,否则后期返工成本很高:

| 要点 | 推荐方案 | 说明 |
|------|----------|------|
| 错误监控 | Sentry / 阿里云 ARMS | 前端报错自动上报 |
| 埋点统计 | 阿里云 Quick BI / Mixpanel | 哪些功能没人用,决定迭代方向 |
| 性能监控 | Web Vitals 接入 | LCP、FID、CLS 指标 |
| 国际化 | next-intl | 即使只做中文,基础架构要有 |
| CI/CD | GitHub Actions / GitLab CI | 自动 lint、type check、build、部署 |
| 灰度发布 | Nginx 路由 / Vercel Preview | 内部分批放量 |
| 代码规范 | ESLint + Prettier + Husky | Pre-commit 自动检查 |
| 类型检查 | TypeScript strict mode | 别图省事用 any |

### 7. 替代方案对比

如果不想用上述主推方案,这些组合也可以考虑:

| 场景 | 推荐组合 | 适用情况 |
|------|----------|----------|
| 极简快速上线 | Vite + React + Ant Design + React Router | 团队小、不需要 SSR |
| 团队是 Vue 背景 | Nuxt 3 + Vue + Element Plus | 已有 Vue 经验 |
| 想要极致美观 | Next.js + shadcn/ui + Radix UI | 需要高度定制设计 |
| 多端覆盖 | Next.js + Capacitor 封装 | 需要 PWA 或移动 App |

但综合考虑**企业级稳定性、团队协作、AI 应用生态**,**Next.js 15 + Ant Design Pro + Ant Design X** 是当前最稳妥的选择。

---

## 十一、参考资源

- Andrej Karpathy 原始 gist:`https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f`
- LLM Wiki 桌面应用实现:`https://github.com/nashsu/llm_wiki`
- WikiLLM(中文实践):`https://github.com/wang-junjian/wikillm`
- Claude Code 官方文档:`https://docs.claude.com/en/docs/claude-code`
- 飞书开放平台:`https://open.feishu.cn`

---

## 附录 A — Schema 模板示例(CLAUDE.md)

```markdown
# 知识库维护规则

## 目录结构
- raw/ : 原始文档,只读
- wiki/ : LLM 生成内容
  - entities/ : 实体页(产品、客户、人员)
  - concepts/ : 概念页(术语、流程)
  - overviews/ : 综合页

## Ingest 流程
1. 阅读 raw/ 下的新文档
2. 提取实体和关键概念
3. 在 wiki/ 创建或更新对应页面
4. 维护反向链接 [[...]]
5. 更新 index.md
6. 在 log.md 追加一行

## 页面格式约定
每个 wiki 页面以 frontmatter 开头:

---
title: 页面标题
type: entity / concept / overview
access: public / dept-xxx / admin
sources: [原始文档路径列表]
last_updated: YYYY-MM-DD
---

正文用 markdown,内部引用用 [[页面名]]。

## Query 流程
1. 读 index.md 找相关页面(最多 5 篇)
2. 深读这些页面
3. 综合答案,标注引用
4. 如答案有价值,归档为新 overview 页面

## Lint 检查项
- 孤立页面(没被任何页面引用)
- 断链([[xxx]] 找不到目标)
- 矛盾陈述(两个页面说法冲突)
- 长期未更新页面(超过 3 个月)
```

---

## 附录 B — 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| LLM 幻觉 | 用户得到错误答案 | 强制返回引用,用户可追溯原文 |
| 敏感信息泄露 | 越权访问 | 三级权限 + API 鉴权 + 审计日志 |
| 知识库陈旧 | 答案过时 | 自动同步 + 月度 lint + 用户反馈 |
| LLM API 涨价 | 成本失控 | 多模型混用 + 缓存 + 用量预警 |
| 单点故障 | 服务不可用 | 数据每日备份 + 关键路径降级方案 |
| 用户流失 | 没人用变成废物 | 入口集成飞书 + 高频问题归档为 FAQ |

---

*本文档由 Claude 协助生成,可根据实际项目情况持续迭代。*