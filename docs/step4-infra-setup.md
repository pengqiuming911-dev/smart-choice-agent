# Step 4 基础设施搭建记录

> 私募基金知识库 Agent - 基础设施搭建

**搭建日期**: 2026-04-18
**状态**: ✅ 完成

---

## 一、交付物清单

| 文件 | 状态 | 说明 |
|-----|------|-----|
| `docker-compose.yml` | ✅ | Qdrant + PostgreSQL + Redis |
| `scripts/init.sql` | ✅ | 4 张表 + 索引 |
| `.env.example` | ✅ | 环境变量模板 |
| `.env` | ✅ | 实际配置（已加入 .gitignore）|
| `.gitignore` | ✅ | 包含 .env |
| `rag_service/rag/vector_store.py` | ✅ | Qdrant 初始化脚本 |
| `rag_service/rag/embedder.py` | ✅ | Embedding 封装 |
| `rag_service/rag/chunker.py` | ✅ | Markdown 分块器 |
| `tests/step4_smoke.py` | ✅ | 连通性测试 |

---

## 二、服务状态

| 服务 | 端口 | 状态 | 验证 |
|-----|------|------|-----|
| Qdrant | 6333/6334 | ✅ Running | Dashboard 可访问 |
| PostgreSQL | 5432 | ✅ Running | 4 张表已创建 |
| Redis | 6379 | ✅ Running | PING 返回 PONG |

---

## 三、PostgreSQL 表结构

### 3.1 表清单

| 表名 | 说明 |
|-----|------|
| `documents` | 文档元数据 |
| `document_permissions` | 文档权限 |
| `chat_logs` | 对话审计 |
| `qualified_investors` | 合格投资者白名单 |

### 3.2 索引

- `documents`: `idx_documents_space`, `idx_documents_status`
- `document_permissions`: `idx_perm_doc`, `idx_perm_principal`
- `chat_logs`: `idx_chat_user`, `idx_chat_time`

---

## 四、Qdrant Collection

- **Collection 名称**: `pe_kb_chunks`
- **向量维度**: 1024
- **距离度量**: Cosine
- **Payload 索引**: `document_id` (keyword), `space_id` (keyword)

---

## 五、Smoke Test 结果

```
[PASS] PostgreSQL: connectivity OK, 4 tables exist, indexes OK
[PASS] Redis: connectivity OK, read/write OK
[PASS] Qdrant: connectivity OK, collection 'pe_kb_chunks' exists, 0 vectors
[PASS] Security: .env is in .gitignore

Results: 4 passed, 0 failed
```

---

## 六、环境变量

### 6.1 已配置项

```
FEISHU_APP_ID=cli_a9257755deb99cc1
FEISHU_APP_SECRET=**** (已隐藏)
DASHSCOPE_API_KEY=**** (已隐藏)
POSTGRES_DSN=postgresql://pekb:pekb_dev_password@localhost:5432/pekb
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=pe_kb_chunks
REDIS_URL=redis://localhost:6379/0
EMBEDDING_MODEL=text-embedding-v3
EMBEDDING_DIM=1024
LLM_MODEL=qwen-max
```

### 6.2 安全说明

- `.env` 已加入 `.gitignore`，不会被提交到 git
- 生产环境需修改默认密码

---

## 七、已知限制

1. **PostgreSQL 密码**: 当前使用弱密码 `pekb_dev_password`，生产环境必须修改
2. **Qdrant API Key**: MVP 阶段未启用认证，生产环境需开启
3. **SSL**: PostgreSQL 未开启 SSL，生产环境建议开启

---

## 八、下一步

进入 [Step 5: 文档同步 Pipeline](../ROADMAP.md#step-5-文档同步-pipeline)

---

**记录人**: Claude Code
**日期**: 2026-04-18
