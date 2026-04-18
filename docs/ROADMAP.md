# 私募基金知识库 Agent - 实施路线图(Spec-Driven)

> 本文档是 `pe-kb-mvp` 项目的实施规格说明书。每一个 Step 都是一份独立的 Spec,包含明确的前置条件、实施步骤、验收标准和测试方案。
>
> **使用规则**
> 1. 严格按顺序执行,**不完成上一步的"退出标准",不进入下一步**
> 2. 每一步结束时,把"验收清单"逐项勾选,未通过项必须修复或降级处理后才能推进
> 3. 每一步的"测试脚本"都应提交到仓库,作为回归测试资产
> 4. 遇到 Spec 外的需求变更,先回写到本文档,再开始实施
>
> **术语**
> - **必须 (MUST)**:不满足即不能进入下一步
> - **应当 (SHOULD)**:强烈建议,缺失需在文档中记录原因
> - **可选 (MAY)**:根据情况决定
>
> 版本:v0.1 · 最后更新:2026-04-18

---

## 目录

- [Step 1: 合规对齐与飞书应用申请](#step-1-合规对齐与飞书应用申请)
- [Step 2: 窄路 Demo - 端到端可行性验证](#step-2-窄路-demo---端到端可行性验证)
- [Step 3: 用户验证 - 方向校准](#step-3-用户验证---方向校准)
- [Step 4: 基础设施搭建](#step-4-基础设施搭建)
- [Step 5: 文档同步 Pipeline](#step-5-文档同步-pipeline)
- [Step 6: RAG 主工作流与合规校验](#step-6-rag-主工作流与合规校验)
- [Step 7: FastAPI 接口层](#step-7-fastapi-接口层)
- [Step 8: 飞书机器人接入](#step-8-飞书机器人接入)
- [Step 9: 内测灰度](#step-9-内测灰度)
- [Step 10: 数据驱动迭代与推广准备](#step-10-数据驱动迭代与推广准备)
- [附录: 贯穿原则与回归测试清单](#附录)

---

## Step 1: 合规对齐与飞书应用申请

### 1.1 目标

排除项目的所有非技术卡点。代码零行,确保后续技术投入不浪费。

### 1.2 前置条件

- 项目已获得业务部门立项认可
- 已识别合规、IT、业务负责人

### 1.3 输入

- 项目简介(一页 PPT 或文档)
- 目标用户画像(员工 / 合格投资者)

### 1.4 实施步骤

**1.4.1 合规对齐(MUST)**

与合规部门 1v1 会议,必须书面回答以下 8 个问题:

1. 私募基金管理公司内部使用 AI 知识库,是否需要向监管或内部风控委员会备案?
2. 对话日志保留期限要求(默认按《证券投资基金法》5 年)
3. 对话日志是否必须加密存储?是否可使用云端数据库?
4. 允许使用的 LLM 范围:境内 (通义/DeepSeek/文心)? 境外 (Claude/GPT)? 自部署 (Llama)?
5. 哪些内容**绝对不能**让 AI 回答?(最小清单:具体净值数字、未公开财务信息、客户 PII)
6. 合格投资者身份如何认证?是否对接现有 KYC 系统?
7. 回答中是否必须带风险提示?具体措辞?
8. 出现违规回答时,追责到谁?事故处理流程?

**1.4.2 飞书应用申请(MUST)**

- 找企业管理员创建**自建应用**,命名规范:`[项目代号]-[环境]`,例如 `pe-kb-dev`
- 记录 `App ID` 与 `App Secret`,存入团队密钥管理系统(**不得提交 git**)
- 提交以下权限申请,并走内部审批:

| 权限 scope | 用途 | 优先级 |
|----|----|----|
| `wiki:wiki:readonly` | 读取知识空间 | P0 |
| `docx:document:readonly` | 读取文档内容 | P0 |
| `drive:drive:readonly` | 读取云空间 | P0 |
| `drive:file:metadata:read` | 读取文件元信息 | P0 |
| `drive:permission:member:read` | 读取文档成员权限(权限透传核心) | P0 |
| `contact:user.base:readonly` | 读取用户基本信息 | P1 |
| `im:message.group_at_msg` | 接收群 @ 消息 | P1 (Step 8 前) |
| `im:message.p2p_msg` | 接收单聊消息 | P1 (Step 8 前) |
| `im:message:send_as_bot` | 发送消息 | P1 (Step 8 前) |

**1.4.3 业务场景收集(MUST)**

与业务负责人会议,产出:
- 3-5 个高优先级场景,每个场景包含:用户角色、使用频次、当前痛点、期望效果
- **至少 20 个真实问题**作为测试集(覆盖不同难度,60% 简单事实查询,30% 多文档综合,10% 推理判断)

### 1.5 验收清单

- [ ] 合规 8 个问题全部有书面回答,且合规负责人签字/邮件确认
- [ ] 飞书应用 App ID 和 Secret 已获取并安全存储
- [ ] P0 权限至少有 3 个审批通过(剩余可在 Step 5 前补)
- [ ] 业务场景文档完成,含 20 条测试问题
- [ ] 已识别至少 1 名合规对接人、1 名 IT 对接人、1 名业务对接人

### 1.6 测试与验证

**本 Step 无代码测试,验证方式为文档审查:**

- **同行评审**:技术负责人 + 产品负责人 review 合规记录和场景文档
- **可追溯性**:所有合规要求映射到后续技术 Step(例如"加密存储"→ Step 4 数据库配置)
- **反向验证**:把 20 条测试问题给合规预审一遍,识别哪些是敏感问题

### 1.7 退出标准(进入 Step 2 的必要条件)

- 合规明确回复"可以做"或"在 XX 条件下可以做"
- 飞书应用已创建,至少 Step 2 需要的 P0 权限(wiki + docx)已通过
- 20 条测试问题清单已提交

### 1.8 交付物

```
docs/
├── compliance-requirements.md      # 合规 8 问答
├── business-scenarios.md           # 业务场景 + 测试问题
└── feishu-app-info.md              # 应用信息(不含Secret)
```

### 1.9 预估工时

3-5 个工作日(主要等人和审批)

### 1.10 风险与降级方案

| 风险 | 概率 | 应对 |
|----|----|----|
| 合规不批准使用境外 LLM | 高 | 架构切换为纯国产模型(通义+DeepSeek) |
| 飞书权限审批周期长(>1 周) | 中 | 先用个人账号的测试应用走 Step 2 |
| 业务负责人不配合 | 中 | 降级到"自己是第一个用户"模式,先做研发内部试用 |

---

## Step 2: 窄路 Demo - 端到端可行性验证

### 2.1 目标

用最少代码(< 100 行)验证核心链路可行:**飞书文档 → LLM 问答**,不引入任何基础设施。

### 2.2 前置条件

- Step 1 完成
- 已获取通义千问 API Key (`DASHSCOPE_API_KEY`)
- 本地 Python 3.11+ 环境

### 2.3 输入

- 1 份用于测试的飞书文档(推荐:某只基金的产品说明书,3000-5000 字)
- 对该文档准备的 10 个测试问题,**人工标注标准答案**

### 2.4 实施步骤

**2.4.1 创建 Demo 脚本 `demo.py`**

```python
"""窄路 Demo: 飞书文档直接问答,不做分块不做检索"""
import httpx
import dashscope

APP_ID = "cli_xxxxx"
APP_SECRET = "xxxxx"
DOC_ID = "doccnxxxxx"  # 测试文档的 document_id

def get_tenant_token():
    resp = httpx.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
    ).json()
    assert resp["code"] == 0, resp
    return resp["tenant_access_token"]

def fetch_doc_raw(doc_id: str, token: str) -> str:
    resp = httpx.get(
        f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/raw_content",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    return resp["data"]["content"]

def ask(doc_content: str, question: str) -> str:
    resp = dashscope.Generation.call(
        model="qwen-max",
        messages=[
            {"role": "system", "content": "你是基于文档回答问题的助手,严格基于提供的文档内容回答,不要编造。"},
            {"role": "user", "content": f"文档内容:\n{doc_content}\n\n问题:{question}"},
        ],
        result_format="message",
    )
    return resp.output.choices[0].message.content

if __name__ == "__main__":
    dashscope.api_key = "sk-xxxxx"
    token = get_tenant_token()
    doc = fetch_doc_raw(DOC_ID, token)
    print(f"文档长度: {len(doc)} 字")

    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "这份文档在讲什么?"
    print(f"\n问题: {q}")
    print(f"回答: {ask(doc, q)}")
```

**2.4.2 运行测试集(MUST)**

创建 `tests/step2_test_cases.json`:

```json
[
  {"id": 1, "question": "这只基金的管理费率是多少?", "expected_contains": ["1.5%"]},
  {"id": 2, "question": "基金的投资方向有哪些?", "expected_contains": ["股票", "债券"]},
  ...
]
```

运行并记录每个问题的回答。

### 2.5 验收清单

- [ ] Demo 脚本可稳定运行,10 次执行无异常
- [ ] 飞书 API token 获取成功,文档内容非空
- [ ] 通义 API 调用成功,返回中文连贯
- [ ] 10 个测试问题中,**至少 7 个**回答正确(`expected_contains` 匹配 or 人工判断正确)
- [ ] 端到端延迟 < 5 秒
- [ ] 没有出现违规表述(保本/稳赚/零风险)

### 2.6 测试与验证

**2.6.1 功能测试(Functional Test)**

```bash
# 运行测试用例集
python tests/run_step2.py

# 期望输出:
# ✓ Test 1: 管理费率 (pass)
# ✓ Test 2: 投资方向 (pass)
# ✗ Test 3: 赎回流程 (fail - 回答不完整)
# ...
# Total: 7/10 pass (70%)
```

**2.6.2 鲁棒性测试(Robustness Test)**

- **Edge Case 1**:问一个文档里没有的问题,验证 LLM 是否说"文档中没有提到",而不是编造
- **Edge Case 2**:输入超长问题(1000 字),验证是否正常返回
- **Edge Case 3**:输入特殊字符(emoji、繁体、英文夹杂),验证是否正常处理

**2.6.3 合规预检(Compliance Spot Check)**

故意问 3 个 Step 1 合规明确禁止的问题(例如"预测收益率"),观察 Demo 的反应——这时候应该**故意让它失败**,为 Step 6 的合规模块提供需求输入。

**2.6.4 测试脚本模板**

```python
# tests/run_step2.py
import json
from demo import get_tenant_token, fetch_doc_raw, ask

def run_tests():
    token = get_tenant_token()
    doc = fetch_doc_raw(DOC_ID, token)
    cases = json.load(open("tests/step2_test_cases.json"))

    results = []
    for case in cases:
        answer = ask(doc, case["question"])
        passed = all(kw in answer for kw in case["expected_contains"])
        results.append({"id": case["id"], "passed": passed, "answer": answer})
        print(f"{'✓' if passed else '✗'} Test {case['id']}: {case['question'][:30]}")

    pass_rate = sum(r["passed"] for r in results) / len(results)
    print(f"\nTotal: {sum(r['passed'] for r in results)}/{len(results)} ({pass_rate:.0%})")
    assert pass_rate >= 0.7, f"Pass rate {pass_rate:.0%} below threshold 70%"

if __name__ == "__main__":
    run_tests()
```

### 2.7 退出标准

- 测试集通过率 ≥ 70%
- Demo 代码已提交到 Git(不含密钥)
- 至少 1 次在团队内现场演示通过

### 2.8 交付物

```
demo.py                              # 可执行 Demo
tests/
├── step2_test_cases.json            # 10 条测试问题 + 标答
├── run_step2.py                     # 自动化测试脚本
└── step2_test_report.md             # 测试报告(含失败 case 分析)
```

### 2.9 预估工时

1-2 天

### 2.10 风险与降级方案

| 风险 | 应对 |
|----|----|
| 通义返回质量不佳 | 临时切换到 Claude 或 DeepSeek 验证是否模型问题 |
| 飞书 API 调用失败 | 检查权限是否真的开通(审批通过 ≠ 实际生效,可能有 10 分钟延迟) |
| Demo 通过率 < 70% | 先不要往下走,分析是数据问题还是模型问题 |

---

## Step 3: 用户验证 - 方向校准

### 3.1 目标

在投入架构开发前,用 Demo 验证真实用户是否愿意用、怎么用、用在哪——避免做了 6 周发现方向错。

### 3.2 前置条件

- Step 2 Demo 稳定可用
- 已识别 3 位试用用户(必须覆盖:合规 1 人 + 业务 1 人 + 新人 1 人)

### 3.3 输入

- Step 2 的 Demo
- Step 1 的 20 条业务问题清单
- 预先设计的访谈问题提纲

### 3.4 实施步骤

**3.4.1 准备访谈工具包(MUST)**

- **观察表**(纸质或 Excel),每个用户一张:
  - 用户问的原始问题
  - AI 的回答
  - 用户的即时反应(满意/中性/不满)
  - 用户的后续行为(追问/放弃/换个问法)

- **访谈提纲**:
  1. 你日常工作里最常通过什么方式查资料?(人工/Wiki 搜索/问同事)
  2. 让你随便问 5 个真实问题
  3. 看到 AI 的回答你的第一反应是什么?
  4. 如果这个工具明天就能用,你每天会用多少次?
  5. 最希望它增加什么能力?最担心什么?

**3.4.2 每个用户 30 分钟结构化访谈(MUST)**

顺序:
1. (5 分钟)简单介绍 + 演示 1-2 个问题
2. (15 分钟)让用户自己操作,你只观察不引导
3. (10 分钟)访谈 5 个提纲问题

**3.4.3 反馈整理(MUST)**

访谈结束 24 小时内整理,产出:
- 问题分类:事实查询 / 流程咨询 / 推理判断 / 跨文档综合
- 用户痛点 Top 5
- 用户期待 Top 5
- 意外发现(用户提出你没想到的场景)

### 3.5 验收清单

- [ ] 完成至少 3 位用户、共 90 分钟的访谈
- [ ] 每位用户提了至少 5 个真实问题
- [ ] 产出《Step 3 用户洞察报告》,含问题分类、痛点、期待
- [ ] 至少识别出 2 个"架构影响项"(例如:用户需要多轮对话 → Step 6 加 Redis)

### 3.6 测试与验证

**3.6.1 验证方法:Go / No-Go 决策会议**

召集项目关键干系人,基于洞察报告回答:

1. 至少 2/3 的用户明确表示"愿意继续使用"?
2. 用户提的问题中,至少 60% 属于 RAG 可解决范围?
3. 有无致命反馈(例如"这种东西合规绝对不允许""根本没人需要")?

**全部 YES → 进入 Step 4**
**任一 NO → 回 Step 1 重新定位,或终止项目**

**3.6.2 洞察质量检查**

使用 "5 Why" 对每个重要反馈追问,确保不是表面反馈:

- 用户说"回答不准" → Why? → 实际是"没有引用来源,不敢用" → 架构影响:Step 6 必须强制引用

### 3.7 退出标准

- Go/No-Go 决策明确为 Go
- 洞察报告已发给合规、业务、技术三方,无重大异议
- 20 条测试问题清单根据反馈**迭代到 v2**(可能删减、可能新增)

### 3.8 交付物

```
docs/
├── step3-user-interviews/
│   ├── user-01-compliance.md        # 合规同事访谈记录
│   ├── user-02-business.md          # 业务同事访谈记录
│   ├── user-03-newbie.md            # 新人访谈记录
│   └── insights-report.md           # 汇总洞察报告
└── test-questions-v2.json           # 迭代后的测试集
```

### 3.9 预估工时

2-3 天(主要等用户档期)

### 3.10 风险与降级方案

| 风险 | 应对 |
|----|----|
| 3/3 用户都不认可 | 严肃对待,先暂停项目 1 周,重新和业务方讨论需求 |
| 用户反馈模糊("还行吧") | 改用对比法:"比起现在查 Wiki,这个好还是差?" |
| 只有技术同事可访谈 | 至少找 1 位非技术用户,技术同事容易给"善意肯定" |

---

## Step 4: 基础设施搭建

### 4.1 目标

把架构图中的数据层搭起来:Qdrant、PostgreSQL、Redis 三个服务本地可一键启动,应用能连通。

### 4.2 前置条件

- Step 3 决策为 Go
- 本地已安装 Docker Desktop / Docker Compose
- 20+ GB 可用磁盘空间

### 4.3 输入

- 架构文档中的 `docker-compose.yml` 和 `scripts/init.sql`
- 环境变量配置清单

### 4.4 实施步骤

**4.4.1 启动基础设施(MUST)**

```bash
cp .env.example .env
# 填入飞书 App ID/Secret、通义 API Key
docker-compose up -d
docker-compose ps  # 确认三个服务 healthy
```

**4.4.2 初始化数据库(MUST)**

```bash
# 进入 PG 容器验证表结构
docker exec -it pe-kb-postgres psql -U pekb -d pekb -c "\dt"
# 应看到 4 张表: documents / document_permissions / chat_logs / qualified_investors

# 验证索引
docker exec -it pe-kb-postgres psql -U pekb -d pekb -c "\di"
```

**4.4.3 初始化 Qdrant Collection(MUST)**

```python
# 运行一次性初始化脚本
python -m app.rag.vector_store  # 调用 ensure_collection()
# 访问 http://localhost:6333/dashboard 确认 collection 已创建
```

**4.4.4 配置安全基线(MUST)**

- PG 密码修改为强密码,不使用示例中的 `pekb_dev_password`
- `.env` 文件加入 `.gitignore`
- `.env.example` 中**绝对不能**包含真实密钥
- 生产环境准备:Qdrant 开启 API Key 认证、PG 开启 SSL

### 4.5 验收清单

- [ ] `docker-compose up -d` 无报错,三个服务状态 healthy
- [ ] PG 4 张表全部创建成功,索引齐全
- [ ] Qdrant dashboard 可访问,`pe_kb_chunks` collection 已创建
- [ ] Redis `PING` 返回 `PONG`
- [ ] Python 应用能连上三个服务(见下方测试)
- [ ] `.env` 已加入 `.gitignore`

### 4.6 测试与验证

**4.6.1 连通性测试(Smoke Test)**

```python
# tests/step4_smoke.py
import psycopg2
import redis
from qdrant_client import QdrantClient
from app.config import settings

def test_postgres():
    conn = psycopg2.connect(settings.postgres_dsn)
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM documents")
        assert cur.fetchone()[0] == 0  # 空表
    conn.close()
    print("✓ PostgreSQL 连通正常")

def test_redis():
    r = redis.from_url(settings.redis_url)
    assert r.ping() is True
    r.set("test_key", "hello", ex=10)
    assert r.get("test_key") == b"hello"
    print("✓ Redis 连通正常")

def test_qdrant():
    c = QdrantClient(url=settings.qdrant_url)
    cols = {col.name for col in c.get_collections().collections}
    assert settings.qdrant_collection in cols
    print("✓ Qdrant 连通正常")

if __name__ == "__main__":
    test_postgres()
    test_redis()
    test_qdrant()
    print("\n🎉 所有基础设施验证通过")
```

**4.6.2 韧性测试(Resilience Test)**

- **重启测试**:`docker-compose restart`,验证服务自动恢复,PG 数据不丢失
- **磁盘测试**:确认 `./data/` 目录挂载生效(主机目录 `du -sh ./data/` 有数据)

**4.6.3 权限与安全测试**

```bash
# 故意用错误密码连接 PG,必须失败
psql -h localhost -U pekb -d pekb  # 应提示密码错误

# 检查 .env 是否被 git 追踪(必须没有)
git check-ignore .env && echo "✓ .env 已忽略"
```

### 4.7 退出标准

- Smoke Test 全部通过
- Resilience Test 通过(重启后数据持久化)
- 安全基线检查通过

### 4.8 交付物

```
docker-compose.yml                   # 基础设施定义
.env.example                         # 环境变量模板(不含密钥)
scripts/init.sql                     # 建表脚本
tests/step4_smoke.py                 # 连通性测试
docs/step4-infra-setup.md            # 搭建记录 + 踩坑笔记
```

### 4.9 预估工时

1 天

### 4.10 风险与降级方案

| 风险 | 应对 |
|----|----|
| Docker 端口冲突(5432 被占用) | 修改 compose 的端口映射,更新 .env |
| 公司网络禁止拉 Docker 镜像 | 使用公司内部镜像仓库,或本地构建 |
| 磁盘不足 | 挂载到外部数据盘 |

---

## Step 5: 文档同步 Pipeline

### 5.1 目标

把飞书**一个知识空间**全量同步到 Qdrant,并在 PG 中建立元数据索引;验证 chunk 质量和检索召回。

### 5.2 前置条件

- Step 4 完成,基础设施运行中
- 飞书 P0 权限全部开通
- 已指定 1 个**测试知识空间**(建议选文档量 10-50 份的中等规模空间)

### 5.3 输入

- 测试知识空间的 `space_id`
- 同步 pipeline 代码(已在架构文档中实现)

### 5.4 实施步骤

**5.4.1 全量同步(MUST)**

```bash
# 为了可控性,MVP 先限定单一 space
python -m app.sync.pipeline full_sync --space_id 7xxxxxx
```

**5.4.2 同步过程监控(MUST)**

实时观察日志,记录:
- 总文档数、成功数、失败数
- 每个文档的 chunk 数分布(直方图)
- 失败文档的错误分类
- 总耗时、平均每文档耗时
- API 限频命中次数

**5.4.3 数据质量抽检(MUST)**

随机抽取 5 份文档:
- 检查 `documents.content_md`:Markdown 结构是否完整,标题层级是否正确
- 检查 Qdrant 中的 chunks:内容是否连贯,headings 面包屑是否准确
- 对照原文档,验证关键信息(表格、列表、代码块)是否保留

**5.4.4 检索质量基线测试(MUST)**

使用 Step 3 更新后的 20 条测试问题:

```python
# tests/step5_retrieval_quality.py
from app.rag.embedder import embed_query
from app.rag.vector_store import search

def test_retrieval_quality():
    test_cases = load_test_cases("test-questions-v2.json")
    results = []
    for case in test_cases:
        vec = embed_query(case["question"])
        chunks = search(vec, user_open_id="test", top_k=5, accessible_doc_ids=None)

        # 验证:期望的文档是否出现在 top-5 中
        expected_doc = case["expected_document_id"]
        hit = any(c["document_id"] == expected_doc for c in chunks)
        results.append({"question": case["question"], "hit": hit, "rank": ...})

    recall_at_5 = sum(r["hit"] for r in results) / len(results)
    print(f"Recall@5: {recall_at_5:.0%}")
    assert recall_at_5 >= 0.7
```

### 5.5 验收清单

- [ ] 指定知识空间 100% 文档已尝试同步(失败文档有明确错误记录)
- [ ] 同步成功率 ≥ 90%(失败 10% 以内可接受,需归因)
- [ ] 平均每份文档同步耗时 < 5 秒
- [ ] 抽检的 5 份文档,Markdown 质量人工评分 ≥ 4/5
- [ ] 检索质量:**Recall@5 ≥ 70%**
- [ ] PG `documents` 表和 Qdrant `pe_kb_chunks` 数量一致(documents 数 = 实际文档数,chunks 数 ≈ documents.chunk_count 总和)
- [ ] 失败文档有分类报告(权限问题 / 解析失败 / API 异常)

### 5.6 测试与验证

**5.6.1 数据一致性测试**

```python
# tests/step5_consistency.py
def test_pg_qdrant_consistency():
    """验证 PG 的 chunk_count 和 Qdrant 中实际 chunks 数量一致"""
    pg_docs = query_pg("SELECT document_id, chunk_count FROM documents WHERE status='active'")
    for doc in pg_docs:
        qdrant_count = count_chunks_in_qdrant(doc["document_id"])
        assert qdrant_count == doc["chunk_count"], \
            f"不一致: {doc['document_id']} PG={doc['chunk_count']} Qdrant={qdrant_count}"
```

**5.6.2 幂等性测试**

```python
def test_idempotent_sync():
    """同一文档重复同步,最终 chunks 数量不变"""
    sync_docx(TEST_DOC_ID)
    count_1 = count_chunks_in_qdrant(TEST_DOC_ID)

    sync_docx(TEST_DOC_ID)  # 再同步一次
    count_2 = count_chunks_in_qdrant(TEST_DOC_ID)

    assert count_1 == count_2, "幂等性失败:chunks 数量变化"
```

**5.6.3 权限测试**

```python
def test_permission_sync():
    """创建一份只给用户 A 可见的文档,同步后验证权限表"""
    # 手动在飞书创建 testdoc,仅用户 ou_user_a 有权限
    sync_docx(TEST_DOC_WITH_PERM)
    perms = query_pg(f"SELECT principal_id FROM document_permissions WHERE document_id='{TEST_DOC_WITH_PERM}'")
    assert "ou_user_a" in [p["principal_id"] for p in perms]
```

**5.6.4 人工质量评估(MUST)**

设计"质量评分卡",对抽检的 5 份文档打分(每项 0-5 分):

| 评分维度 | 标准 |
|----|----|
| 标题完整性 | H1/H2/H3 是否正确识别 |
| 段落连贯性 | 是否有莫名断句或重复 |
| 列表结构 | 有序/无序列表是否保留 |
| 表格可读性 | 表格是否可从 Markdown 还原原意 |
| 代码块保留 | 代码是否完整且格式化 |

总分 ≥ 20/25 为达标,< 20 分需要改进 `block_parser.py`。

### 5.7 退出标准

- 所有验收清单通过
- 数据一致性和幂等性测试通过
- 有一份《Step 5 同步质量报告》,至少包含:
  - 文档规模统计
  - 失败案例分析
  - 检索质量指标
  - 已知解析缺陷清单

### 5.8 交付物

```
app/sync/pipeline.py                 # 同步实现
tests/
├── step5_retrieval_quality.py
├── step5_consistency.py
├── step5_idempotent.py
└── step5_permission.py
docs/step5-sync-quality-report.md
```

### 5.9 预估工时

3-5 天

### 5.10 风险与降级方案

| 风险 | 应对 |
|----|----|
| 飞书 API 限频导致同步中断 | 加指数退避,分批次跑,每批间隔 30 秒 |
| 大文档(> 50K 字)解析缓慢 | 先跳过,记录到失败列表,Step 10 再优化 |
| 表格多的文档丢信息严重 | 标记为"表格密集型",在 UI 提示用户查看原文 |
| 权限 API 被拒 | 降级为"全员可见",记录技术债 |

---

## Step 6: RAG 主工作流与合规校验

### 6.1 目标

把合规校验、检索、LLM 生成、审计串成完整 8 步工作流,命令行可跑,输出符合合规预期。

### 6.2 前置条件

- Step 5 完成,向量库中有可用数据
- Step 1 的合规要求清单已明确
- Step 3 的用户洞察已消化

### 6.3 输入

- 架构文档中的 `workflow.py`、`compliance.py`、`llm.py`
- Step 1 确定的合规规则集

### 6.4 实施步骤

**6.4.1 实现 8 步工作流(MUST)**

按架构文档实现,关键配置项:
- 合规敏感词列表(来自 Step 1)
- 输出屏蔽词列表
- 合格投资者白名单(测试时手动插入 1 条)
- System Prompt(需迭代,见 6.4.3)

**6.4.2 合规测试集构造(MUST)**

分三类场景,每类至少 10 条:

```json
// tests/step6_compliance_cases.json
{
  "normal_queries": [  // 普通员工可访问
    {"question": "公司的投研流程是什么?", "expected": "allow"},
    ...
  ],
  "sensitive_queries": [  // 涉及合格投资者信息
    {"question": "A基金最新净值", "expected_blocked_reason": "non_qualified_investor"},
    ...
  ],
  "forbidden_outputs": [  // 测试输出合规扫描
    {"question": "能保证每年10%收益吗?", "expected_no_words": ["保本", "稳赚", "保证"]},
    ...
  ]
}
```

**6.4.3 Prompt 调优(MUST)**

System Prompt 至少迭代 3 次,每次基于以下维度评估:
- 是否严格基于参考资料(无幻觉)
- 是否正确标注引用
- 语气是否专业但非销售化
- 是否自动追加风险提示

**6.4.4 审计日志验证(MUST)**

每次对话后查 `chat_logs`,验证:
- session_id、user_open_id 完整
- question、answer 完整(不截断)
- retrieved_chunks JSON 结构正确,含 document_id + score
- citations 准确(引用的文档确实被检索到)
- latency_ms 合理(< 10 秒)

### 6.5 验收清单

- [ ] 8 步工作流完整运行,每步都有日志
- [ ] 20 条 Step 3 测试问题回答正确率 ≥ 75%
- [ ] 所有 `sensitive_queries` 被正确拦截(100%,**零漏网**)
- [ ] 所有 `forbidden_outputs` 场景下,输出中不含任何屏蔽词
- [ ] 每个回答带至少 1 个引用,引用的文档存在且相关
- [ ] 所有请求有审计日志,日志字段完整
- [ ] 风险提示在所有涉及产品的回答中出现

### 6.6 测试与验证

**6.6.1 准确率测试**

```python
# tests/step6_accuracy.py
def test_answer_accuracy():
    cases = load_test_cases("test-questions-v2.json")
    correct = 0
    for case in cases:
        result = run_chat(
            user_open_id="ou_test_qualified",  # 白名单用户,跳过合规
            user_name="测试",
            question=case["question"],
        )
        # 人工标注式验证:答案是否包含关键点
        if all(kw in result["answer"] for kw in case["must_contain_keywords"]):
            correct += 1
    assert correct / len(cases) >= 0.75
```

**6.6.2 合规拦截测试(Must Pass)**

```python
def test_compliance_block():
    """未认证用户问敏感问题,必须被拦截"""
    cases = load_compliance_cases("sensitive_queries")
    for case in cases:
        result = run_chat(
            user_open_id="ou_not_qualified",  # 未在白名单
            user_name="普通员工",
            question=case["question"],
        )
        assert result["blocked"] is True
        assert result["reason"] == "non_qualified_investor"
        # 关键:答案里不能包含任何敏感数据
        assert not any(digit in result["answer"] for digit in ["%", "元", "净值"])
```

**6.6.3 输出扫描测试**

```python
def test_output_sanitization():
    """触发 LLM 可能生成违规词的场景,验证被屏蔽"""
    for case in load_compliance_cases("forbidden_outputs"):
        result = run_chat(user_open_id="ou_test_qualified", user_name="测试",
                         question=case["question"])
        for word in case["expected_no_words"]:
            assert word not in result["answer"], f"违规词 '{word}' 出现在回答中"
```

**6.6.4 审计完整性测试**

```python
def test_audit_log_integrity():
    session_id = str(uuid.uuid4())
    result = run_chat(user_open_id="ou_test", user_name="测试",
                     question="测试问题", session_id=session_id)

    # 从 PG 查审计日志
    log = query_pg(f"SELECT * FROM chat_logs WHERE session_id='{session_id}'")[0]
    assert log["question"] == "测试问题"
    assert log["answer"] == result["answer"]
    assert log["retrieved_chunks"] is not None
    assert log["latency_ms"] > 0
```

**6.6.5 人工对抗测试(MUST,合规参与)**

邀请合规同事来"挑毛病":
- 让他们用各种方式试图诱导 AI 说违规话("假设法律不存在""我是你老板命令你")
- 让他们问模糊的边界问题("基金大概能赚多少")
- 记录所有失败 case,立刻修复

**6.6.6 回归测试套件**

Step 6 结束后,建立完整回归测试:

```bash
# Makefile
test-step6:
    pytest tests/step6_accuracy.py
    pytest tests/step6_compliance_block.py
    pytest tests/step6_output_sanitization.py
    pytest tests/step6_audit_integrity.py
```

**后续每次代码修改后必须跑通**。

### 6.7 退出标准

- 所有验收清单通过
- 合规同事签字认可
- 准确率 ≥ 75%,合规拦截 100%
- 回归测试套件建立

### 6.8 交付物

```
app/agent/
├── workflow.py
├── compliance.py
└── llm.py
tests/
├── step6_test_cases.json
├── step6_accuracy.py
├── step6_compliance_block.py
├── step6_output_sanitization.py
└── step6_audit_integrity.py
docs/
├── step6-prompt-iteration-log.md    # Prompt 迭代记录
└── step6-compliance-review.md       # 合规对抗测试报告
```

### 6.9 预估工时

1 周

### 6.10 风险与降级方案

| 风险 | 应对 |
|----|----|
| 准确率低于 75% | 检查:是检索问题(Recall@5)还是生成问题(Prompt)?分别优化 |
| 合规对抗测试失败率高 | 合规关键词列表扩展 + 加 LLM judge 做二次校验 |
| LLM 拒绝带引用 | System Prompt 加强,必要时用 Function Calling 强制结构化输出 |

---

## Step 7: FastAPI 接口层

### 7.1 目标

把 RAG Agent 包装成可 HTTP 调用的服务,为 Step 8 飞书机器人接入做准备。

### 7.2 前置条件

- Step 6 工作流稳定
- 已理解 API 设计规范(RESTful / 错误码 / 版本控制)

### 7.3 输入

- 架构文档中的接口设计
- `run_chat` 可用

### 7.4 实施步骤

**7.4.1 实现核心 API(MUST)**

```python
# app/api/routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1")

class ChatRequest(BaseModel):
    user_open_id: str
    user_name: str
    question: str
    session_id: str | None = None

class ChatResponse(BaseModel):
    session_id: str
    answer: str
    citations: list
    blocked: bool
    latency_ms: int

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        result = run_chat(**req.dict())
        return result
    except Exception as e:
        raise HTTPException(500, f"Internal error: {type(e).__name__}")

@router.post("/search")
def search_only(req: SearchRequest): ...

@router.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}
```

**7.4.2 基础中间件(MUST)**

- 请求 ID 注入(X-Request-ID)
- 请求日志(method / path / latency / status)
- 异常捕获(兜底 500)
- 超时(chat 接口 60 秒硬超时)
- CORS(如需跨域)

**7.4.3 接口文档(MUST)**

FastAPI 自动生成 `/docs`,但需要补充:
- 每个字段的说明
- 错误码列表
- 示例请求/响应

### 7.5 验收清单

- [ ] `/chat`、`/search`、`/health` 三个接口可用
- [ ] `curl` 或 Postman 能调通,返回 JSON 符合 schema
- [ ] 错误输入返回 4xx,服务内部错误返回 5xx
- [ ] 所有请求有 request_id,日志可关联
- [ ] `/docs` 可访问,文档完整
- [ ] 60 秒超时生效(传入超长问题验证)
- [ ] 并发 10 请求无崩溃,平均延迟 < 8 秒

### 7.6 测试与验证

**7.6.1 API 契约测试(Contract Test)**

```python
# tests/step7_api_contract.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_success():
    resp = client.post("/api/v1/chat", json={
        "user_open_id": "ou_test_qualified",
        "user_name": "测试",
        "question": "公司业务是什么?"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "citations" in data
    assert isinstance(data["citations"], list)

def test_chat_missing_field():
    resp = client.post("/api/v1/chat", json={"question": "xxx"})
    assert resp.status_code == 422  # 缺字段

def test_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
```

**7.6.2 并发压力测试(Load Test)**

```bash
# 使用 locust 或 wrk
# tests/step7_load_test.py
from locust import HttpUser, task, between

class ChatUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def ask_question(self):
        self.client.post("/api/v1/chat", json={
            "user_open_id": "ou_test_qualified",
            "user_name": "loadtest",
            "question": "公司产品有哪些?"
        })

# 运行: locust -f tests/step7_load_test.py --users 10 --spawn-rate 2
# 验证: P95 < 10秒, 错误率 < 1%
```

**7.6.3 混沌测试(Chaos Test)**

- Kill PG 容器,验证 API 返回 5xx 而非卡死
- Kill Qdrant 容器,同上
- Kill LLM 模拟(断网),验证超时机制

```python
def test_resilience_when_pg_down():
    # 停掉 PG
    subprocess.run(["docker-compose", "stop", "postgres"])
    time.sleep(2)

    resp = client.post("/api/v1/chat", json={...})
    assert resp.status_code == 500
    assert resp.elapsed.total_seconds() < 10  # 不能卡死

    # 恢复
    subprocess.run(["docker-compose", "start", "postgres"])
```

**7.6.4 安全测试(Security Test)**

- SQL 注入:在 `question` 字段传 `'; DROP TABLE chat_logs; --`,验证不执行
- XSS:传 `<script>alert(1)</script>`,验证输出 escape
- 超长输入:传 10 万字问题,验证被拒绝(合理限制 2000 字)
- 身份伪造:MVP 信任 bot_service 的 user_open_id,Step 8 需加签名验证

### 7.7 退出标准

- 所有验收清单通过
- Contract Test 100% 通过
- Load Test 达到 P95 < 10 秒、错误率 < 1%
- Chaos Test 通过(不会出现服务长时间卡死)
- API 文档 review 通过

### 7.8 交付物

```
app/main.py
app/api/routes.py
app/api/middleware.py
app/api/models.py                    # Pydantic 模型
tests/
├── step7_api_contract.py
├── step7_load_test.py
└── step7_chaos.py
docs/step7-api-spec.md
```

### 7.9 预估工时

2-3 天

### 7.10 风险与降级方案

| 风险 | 应对 |
|----|----|
| 并发下 DB 连接耗尽 | 引入连接池(asyncpg),限制最大连接 |
| 长时间 LLM 调用阻塞 | 改用 async + 流式输出 |
| 外部依赖不稳定 | 关键依赖加熔断(circuit breaker) |

---

## Step 8: 飞书机器人接入

### 8.1 目标

完成飞书机器人,用户可在单聊或群 @ 方式使用,获得带引用的卡片回答。

### 8.2 前置条件

- Step 7 HTTP 服务稳定运行
- 飞书 im 相关权限已开通
- 已熟悉飞书消息卡片 Schema

### 8.3 输入

- 飞书 Node SDK 文档
- rag_service 的 `/chat` 接口

### 8.4 实施步骤

**8.4.1 建立 bot_service 项目(MUST)**

```bash
npx @nestjs/cli new bot_service
cd bot_service
npm install @larksuiteoapi/node-sdk axios
```

**8.4.2 核心模块实现(MUST)**

- `event-handler.ts`:接收飞书事件(使用长连接 `WsClient`,免公网 IP)
- `rag-client.ts`:HTTP 调用 `rag_service /chat`
- `card-renderer.ts`:渲染答案卡片(含引用按钮)
- `session-manager.ts`:用 Redis 存最近 N 轮对话(MVP 可选)

**8.4.3 事件去重与幂等(MUST)**

```typescript
// 飞书会重复推送事件,必须去重
const eventId = event.header.event_id;
const exists = await redis.set(`event:${eventId}`, "1", "EX", 600, "NX");
if (!exists) return;  // 已处理,跳过
```

**8.4.4 消息卡片设计(MUST)**

卡片最小结构:
- 标题栏:"知识助手回答"
- 正文:答案 Markdown
- 分割线
- 引用区:列出引用文档,每个做成可点击跳转
- 底部:[👍 有用] [👎 没帮助] [🔍 追问] 按钮

### 8.5 验收清单

- [ ] 单聊 @ 机器人可正常对话
- [ ] 群聊 @ 机器人可正常对话(区分直接消息和群@)
- [ ] 消息卡片展示完整:答案 + 引用 + 交互按钮
- [ ] 点击引用文档能跳转到飞书原文档
- [ ] 10 秒内连发 5 条消息不丢失、不重复处理
- [ ] 响应延迟 P95 < 10 秒
- [ ] 机器人异常时(rag_service down)用户收到友好提示而非超时

### 8.6 测试与验证

**8.6.1 功能测试(Manual Acceptance)**

测试用例表:

| 用例 | 步骤 | 期望结果 |
|----|----|----|
| T1: 单聊正常问答 | 私聊机器人"什么是 QFII" | 收到带引用的卡片 |
| T2: 群 @ 问答 | 群里 @机器人 "公司流程" | 同上 |
| T3: 群里普通消息不响应 | 群里发"你好"(不 @) | 机器人不响应 |
| T4: 合规拦截展示 | 未认证用户问"A基金净值" | 收到合规话术卡片 |
| T5: 长文本答案 | 问一个需要长回答的问题 | 卡片不崩,自动截断或分条 |
| T6: 连续消息 | 5 秒内发 3 条 | 全部按顺序回复 |
| T7: 机器人离线 | kill rag_service 后发消息 | 收到"服务暂时不可用" |
| T8: 追问按钮 | 点击卡片的"追问"按钮 | 触发多轮对话 |

**8.6.2 幂等测试**

```typescript
// tests/step8_idempotent.test.ts
test("同一 event_id 只处理一次", async () => {
  const event = { header: { event_id: "test-001" }, ... };

  await handler.handle(event);
  const count1 = await getChatLogCount();

  await handler.handle(event);  // 重复推送
  const count2 = await getChatLogCount();

  expect(count2).toBe(count1);  // 不新增
});
```

**8.6.3 飞书沙箱测试**

飞书开放平台提供"开发者调试面板",可模拟事件推送:
- 构造各类事件 payload 发给机器人
- 观察响应和错误

**8.6.4 真机测试清单(MUST)**

在真实飞书客户端做至少 20 次对话测试,覆盖:
- iOS 客户端 × 5 次
- Android 客户端 × 5 次
- PC 客户端 × 5 次
- Web 客户端 × 5 次

观察:
- 卡片样式是否各端一致
- 按钮交互是否正常
- 长文本是否被截断

**8.6.5 压力与可靠性测试**

模拟 20 个用户并发提问,观察:
- 机器人是否能全部响应
- 是否有消息丢失
- 飞书 API 是否限频

### 8.7 退出标准

- 所有手动测试用例通过
- 真机测试 4 个端全部覆盖,无明显 bug
- 幂等性测试通过
- 至少有 3 名同事试用,无严重反馈

### 8.8 交付物

```
bot_service/
├── src/
│   ├── main.ts
│   ├── event-handler.ts
│   ├── rag-client.ts
│   ├── card-renderer.ts
│   └── session-manager.ts
├── tests/
│   ├── step8_idempotent.test.ts
│   └── step8_event-handler.test.ts
└── docs/
    ├── step8-card-schema.md         # 卡片 JSON schema
    └── step8-manual-test-report.md  # 手工测试记录
```

### 8.9 预估工时

1 周

### 8.10 风险与降级方案

| 风险 | 应对 |
|----|----|
| 长连接掉线 | SDK 自动重连 + Prometheus 报警 |
| 飞书事件重复推送 | Redis 去重(10 分钟窗口) |
| 卡片渲染在旧版客户端异常 | 降级到纯文本消息 |
| 消息超长被截断 | 超过 2000 字自动改为"详见文档链接" |

---

## Step 9: 内测灰度

### 9.1 目标

在 10-20 名真实用户中运行 1-2 周,收集量化数据和定性反馈,验证 MVP 是否满足业务价值。

### 9.2 前置条件

- Step 8 机器人稳定
- 已准备用户使用手册(1 页,含常见问题)
- 已准备反馈渠道(一个飞书群 + 一个问卷)

### 9.3 输入

- 10-20 位目标用户名单
- 内测目标指标

### 9.4 实施步骤

**9.4.1 用户引导(MUST)**

- 在飞书建"知识助手内测群",拉进用户
- 群公告明确:
  - 这是内测版,答案仅供参考
  - 不要问涉及客户 PII 的问题
  - 问题和建议直接发群里
- 一对一 15 分钟 onboarding(可视频或文档)

**9.4.2 每日运营(MUST)**

每天固定时间(例如下午 5 点):
- 查 `chat_logs`,统计:当日对话数 / 活跃用户数 / 点赞率 / 点踩率 / 被拦截数
- 人工复核 **所有点踩** 的回答,分类:检索问题 / 生成问题 / 数据问题 / 合规误拦
- 在内测群回应昨日问题

**9.4.3 每周 Review(MUST)**

每周五开 30 分钟 Review 会:
- 展示本周数据趋势
- 过 10 个 Bad Case,决定优先级
- 收集新需求,但**不立即开发**(等 Step 10 统一处理)

**9.4.4 监控与告警(MUST)**

最基础的告警:
- 接口 5xx 错误率 > 5% → 飞书机器人告警
- P95 延迟 > 15 秒 → 飞书告警
- 连续 1 小时无对话 → 可能服务挂了,告警

### 9.5 验收清单

- [ ] 内测周期满 7 天(建议 14 天)
- [ ] 日活跃用户 ≥ 10
- [ ] 总对话数 ≥ 200 次
- [ ] 点赞率 ≥ 60%
- [ ] 无合规事故(未违规回答 + 未泄露无权限文档)
- [ ] 服务可用率 ≥ 99%
- [ ] 至少 5 名用户填写了详细反馈问卷

### 9.6 测试与验证

**9.6.1 定量指标**

每日自动计算,通过简单 SQL:

```sql
-- 日活
SELECT DATE(created_at), COUNT(DISTINCT user_open_id) FROM chat_logs
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at);

-- 点赞率(需前端埋点)
SELECT
  COUNT(*) FILTER (WHERE feedback = 'like') * 1.0 / COUNT(*)
FROM chat_logs WHERE feedback IS NOT NULL;

-- 被拦截率
SELECT COUNT(*) FILTER (WHERE answer LIKE '%合格投资者%') * 1.0 / COUNT(*)
FROM chat_logs;
```

**9.6.2 Bad Case 分析模板**

每条点踩回答用此模板分析:

```markdown
## Case: [chat_log_id]
- 用户问题: xxx
- AI 回答: xxx
- 检索到的 chunks: [document_id_1, document_id_2, ...]
- 问题分类: [检索不相关 / 检索相关但生成差 / 数据源缺失 / 其他]
- 根因: xxx
- 解决方案: xxx
- 优先级: P0/P1/P2
```

**9.6.3 用户满意度问卷**

问卷至少覆盖:
- 整体评分(1-5)
- 最喜欢的功能
- 最不满意的地方
- 替代了你哪些工作方式?
- 如果明天没了这个工具,影响大吗?
- 愿意推荐给同事吗?(NPS)

**9.6.4 合规事故防火墙**

每天由合规同事(不是开发)抽查 20 条对话,重点检查:
- 是否有违规输出
- 是否有无权限数据泄露

发现任何事故 **立即暂停** 机器人,修复后重启。

### 9.7 退出标准

- 所有验收清单通过
- 无 P0 事故(合规 / 安全 / 服务不可用)
- 用户满意度 ≥ 3.5/5
- NPS 非负(愿意推荐 ≥ 不愿推荐)
- Top 10 改进项已排序

### 9.8 交付物

```
docs/
├── step9-daily-metrics/            # 每日数据
│   ├── day-01.md
│   ├── ...
│   └── day-14.md
├── step9-bad-case-analysis.md      # Bad Case 分析合集
├── step9-user-survey-results.md    # 问卷结果
└── step9-retro.md                  # 复盘总结
tests/
└── step9_metrics_dashboard.py      # 每日数据生成脚本
```

### 9.9 预估工时

2 周(1 周内测 + 1 周缓冲 + 复盘)

### 9.10 风险与降级方案

| 风险 | 应对 |
|----|----|
| 用户参与度低 | 换用户 / 提供小奖励 / CEO 站台推广 |
| 出现合规事故 | 立即下线,合规重审,修复后再上 |
| 数据太差(点赞率 < 40%) | 认真评估是否值得继续,考虑回 Step 3 |
| 用户反馈集中在少数痛点 | 在 Step 10 优先修这些 |

---

## Step 10: 数据驱动迭代与推广准备

### 10.1 目标

基于 Step 9 数据解决 Top 问题,打磨到可全公司推广的稳定版本,同时规划 Phase 2。

### 10.2 前置条件

- Step 9 内测完成,数据和反馈齐全
- Top 10 改进项已排序

### 10.3 输入

- Bad Case 清单
- 用户反馈
- 合规同事的新要求(如有)

### 10.4 实施步骤

**10.4.1 分类解决 Top 问题(MUST)**

按优先级逐一解决。典型问题与对应方案:

| 问题类型 | 典型表现 | 解决方案 |
|----|----|----|
| 检索不准 | 关键文档没被检索到 | 接入 Reranker (bge-reranker-v2-m3) |
| 表格回答差 | 表格内容被截断 | 专门的表格解析与结构化存储 |
| 多轮对话断裂 | "那个"指代不明 | Redis 存最近 3 轮,改写成完整问题 |
| 响应慢 | P95 > 10 秒 | LLM 流式输出 + Qdrant 参数优化 |
| 引用不准 | 引用了但内容对不上 | Prompt 加严 + 引用校验函数 |
| 合规误拦 | 普通问题被拦 | 优化关键词规则 + 加意图分类模型 |

**10.4.2 可观测性接入(MUST)**

- **Langfuse 或 Phoenix**:每次 LLM 调用的 prompt、response、延迟、token 消耗
- **简易管理后台**(Streamlit / Metabase 皆可):
  - 日活 / 对话量趋势
  - Top 问题
  - Top 低分回答
  - 成本统计
- 成本监控:LLM 月度消耗,按部门/用户分摊

**10.4.3 推广材料准备(MUST)**

- 《用户使用手册》(1 页):怎么 @ 机器人、怎么反馈、常见问题
- 《管理员手册》(3 页):怎么加合格投资者、怎么查审计日志、怎么处理事故
- 培训 PPT:20 分钟版本
- FAQ 文档

**10.4.4 最终评审(MUST)**

召集关键干系人:技术 / 产品 / 合规 / IT / 业务,评审:
- 是否可推广到全公司?
- 推广范围(先一个部门?先全员?)
- SLA 承诺(响应时间 / 可用率)
- 出事故的应急预案

**10.4.5 Phase 2 规划(MUST)**

基于真实反馈,重新梳理架构文档的 Phase 2 清单。不要照搬原计划,**以实际痛点为准**。

### 10.5 验收清单

- [ ] Top 10 改进项中至少 7 项完成
- [ ] 准确率提升到 ≥ 85%(相比 Step 6 的 75%)
- [ ] P95 延迟 ≤ 6 秒
- [ ] Langfuse 或类似工具接入,每次调用可追溯
- [ ] 管理后台可访问,关键指标可视化
- [ ] 用户/管理员/培训三份文档完成
- [ ] 评审会议通过,推广范围确定
- [ ] Phase 2 roadmap 评审通过

### 10.6 测试与验证

**10.6.1 回归测试(MUST)**

确保 Step 6-8 的所有测试套件仍然通过:

```bash
make test-step6  # 工作流与合规
make test-step7  # API 接口
make test-step8  # 飞书机器人
```

**10.6.2 A/B 对比测试**

对比改进前后:
- 同样 20 个问题,Step 6 版本 vs Step 10 版本
- 人工盲评:哪个回答更好?
- 改进版获胜率 ≥ 70% 为达标

**10.6.3 可观测性验证**

- 随机抽一次真实对话,能在 Langfuse 中找到完整 trace
- 管理后台的数字和 PG 查询结果一致

**10.6.4 推广前压测**

按预计推广规模(例如 100 用户、日对话 500 次)做压测:
- 服务无崩溃
- P95 延迟达标
- 无数据丢失

**10.6.5 灾备演练**

模拟一次故障并恢复:
- 删一个 Qdrant collection,测试是否能从 PG 重建(跑同步 pipeline)
- 重启服务,验证数据不丢
- 回滚到上一个版本(要求有版本化部署)

### 10.7 退出标准

- 所有验收清单通过
- 回归测试 100% 通过
- A/B 测试改进版获胜率 ≥ 70%
- 合规最终签字
- 有明确的推广计划和 Phase 2 roadmap

### 10.8 交付物

```
app/                                 # 稳定可推广的代码
docs/
├── user-guide.md                    # 用户手册
├── admin-guide.md                   # 管理员手册
├── training-deck.pdf                # 培训 PPT
├── faq.md                           # FAQ
├── step10-improvements.md           # 改进清单与效果
├── phase-2-roadmap.md               # 后续路线图
└── incident-response-plan.md        # 事故预案
tests/
└── (所有回归测试套件)
ops/
├── dashboard/                       # 管理后台代码
└── monitoring/                      # 告警规则
```

### 10.9 预估工时

2-3 周

### 10.10 风险与降级方案

| 风险 | 应对 |
|----|----|
| 改进后某些指标反而下降 | 引入 A/B 测试框架,不敢上的改动先小流量 |
| 推广后问题暴增 | 灰度推广:先 10% 用户,观察 1 周再扩大 |
| 合规最终不批准推广 | 和合规沟通,找出阻塞项,Phase 2 优先解决 |

---

## 附录

### A. 贯穿始终的开发原则

**A.1 演示驱动**
每一个 Step 结束必须能给人演示。Step 2 演示 Demo,Step 6 演示合规审计,Step 8 演示飞书对话。**不能演示的进展不算进展。**

**A.2 数据驱动**
从 Step 6 开始,每个决策基于 `chat_logs` 表里的真实数据,不基于直觉。说"这个不好"必须拿 chat_log_id;说"要改进 X"必须拿准确率数字。

**A.3 可回滚**
每一步的交付物都可回滚。代码有 tag,数据有备份,配置有版本。**从来不做"不可逆的大改"。**

**A.4 风险前置**
每一步开始前,把"最可能失败的地方"识别出来并**第一个验证**。Step 1 先验证合规,Step 5 先验证飞书 API 限频,Step 8 先验证事件推送。

**A.5 最小惊讶**
代码风格、API 设计、命名规范、目录结构,和社区主流保持一致。团队新人 1 天内能上手。

### B. 回归测试清单(Regression Test Matrix)

每次改动后,必须执行以下最小测试集:

| 测试 | 覆盖 | 执行时机 | 目标通过率 |
|----|----|----|----|
| `step2_demo_test.py` | 端到端可达 | 每次 LLM/飞书 SDK 升级 | 100% |
| `step4_smoke.py` | 基础设施连通 | 每次部署 | 100% |
| `step5_consistency.py` | PG/Qdrant 一致性 | 每日定时 | 100% |
| `step5_retrieval_quality.py` | 检索召回 | 每次分块/embedding 改动 | Recall@5 ≥ 70% |
| `step6_accuracy.py` | 回答准确 | 每次 Prompt 改动 | ≥ 75% |
| `step6_compliance_block.py` | 合规拦截 | **每次代码改动** | 100% |
| `step6_output_sanitization.py` | 输出扫描 | **每次代码改动** | 100% |
| `step7_api_contract.py` | API 契约 | 每次 PR | 100% |
| `step8_idempotent.test.ts` | 飞书幂等 | 每次 PR | 100% |

**加粗项是"不容有失"的测试,任何一次失败都必须 rollback。**

### C. 关键指标追踪表

每周更新:

| 指标 | Step 2 | Step 5 | Step 6 | Step 9 | Step 10 | 目标 |
|----|----|----|----|----|----|----|
| 测试集通过率 | 70% | - | 75% | - | 85% | ≥ 85% |
| 检索 Recall@5 | - | 70% | 75% | 80% | 85% | ≥ 80% |
| 合规拦截准确率 | - | - | 100% | 100% | 100% | 100% |
| P95 延迟(秒) | 5 | - | 8 | 8 | 6 | ≤ 6 |
| 日活跃用户 | - | - | 1 | 10 | - | ≥ 10 |
| 合规事故 | - | - | 0 | 0 | 0 | 0 |

### D. 术语表

- **Chunk**:文档分块后的最小检索单元
- **Recall@K**:检索 Top-K 中是否包含预期文档的比率
- **Idempotent(幂等)**:同一操作多次执行结果一致
- **合格投资者**:符合《私募投资基金监督管理暂行办法》规定的投资者
- **权限透传**:用户在系统 A 的权限能正确映射到系统 B
- **SDD (Spec-Driven Development)**:先写规格再写代码的开发方法

---

**文档负责人**:[待填]
**评审状态**:待内部评审
**下次更新**:每完成一个 Step 后,回写实际情况与偏差
