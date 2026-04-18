# RAG 问答 Agent 实现

## 概述

为私募基金知识库实现了基于 RAG（Retrieval-Augmented Generation）的问答功能，支持从已同步的飞书文档中检索相关内容并生成答案。

## 新增文件

### 1. `rag_service/agent/rag_agent.py`

核心 RAG Agent 实现，主要功能：

- **检索（Retrieve）**：从 Qdrant 向量数据库中检索与用户问题最相关的文档片段
- **构建上下文（Build Context）**：将检索到的片段组织成 LLM 可理解的上下文
- **生成答案（Answer）**：调用 MiniMax LLM，基于上下文生成回答
- **权限过滤**：支持按用户权限过滤可检索的文档
- **日志记录**：将问答记录存入 PostgreSQL 供审计

关键类：
- `RAGAgent` - 主 Agent 类
- `RetrievedChunk` - 检索结果数据结构
- `Citation` - 引用来源数据结构

### 2. `rag_service/agent/api.py`

FastAPI 问答接口服务：

- `POST /api/question` - 问答接口
- `GET /api/health` - 健康检查
- `GET /api/stats` - 知识库统计

## 使用方式

### 命令行测试

```bash
python -m rag_service.agent.rag_agent "私募基金的投资策略有哪些？"
```

参数：
- `--top-k N` - 检索的片段数量（默认 5）
- `--session-id UUID` - 会话 ID
- `--user-id OPEN_ID` - 用户 ID（用于权限过滤）
- `--doc-ids ID1,ID2` - 指定要检索的文档 ID

### API 服务

```bash
python -m rag_service.agent.api
```

服务启动后访问 http://localhost:8080/docs 查看 API 文档。

```bash
# 测试示例
curl -X POST http://localhost:8080/api/question \
  -H "Content-Type: application/json" \
  -d '{"question": "私募基金的投资策略有哪些？"}'
```

### Python 代码调用

```python
from rag_service.agent.rag_agent import RAGAgent

agent = RAGAgent()
result = agent.answer(
    question="私募基金的投资策略有哪些？",
    user_open_id="user_open_id",  # 可选，用于权限过滤
)

print(result["answer"])       # 答案文本
print(result["citations"])     # 引用来源
print(result["latency_ms"])   # 响应耗时
```

## 依赖更新

### `requirements.txt`

新增依赖：
- `sentence-transformers==3.0.1` - bge-m3 嵌入模型

## 注意事项

1. 使用前需确保：
   - Qdrant 向量数据库已启动并运行
   - PostgreSQL 已启动并运行
   - 文档已通过 `sync_folder` 或 `full_sync` 命令同步到向量数据库

2. RAG Agent 会自动将问答日志记录到 `chat_logs` 表中

3. 检索时会根据用户权限自动过滤可访问的文档（通过 `get_accessible_doc_ids` 函数）
