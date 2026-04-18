# Step 7: FastAPI 接口层 - API 规格文档

## 概述

RAG Agent 的 HTTP API 接口层，为 Step 8 飞书机器人接入提供标准 RESTful 接口。

## 服务器信息

- **基础 URL**: `http://localhost:8080`
- **API 版本**: v1
- **前缀**: `/api/v1`

## 通用 Headers

| Header | 说明 |
|--------|------|
| `X-Request-ID` | 请求追踪 ID（可选，不提供则自动生成） |

## 通用响应格式

### 成功响应

```json
{
  "session_id": "uuid-string",
  "answer": "生成的答案",
  "citations": [...],
  "blocked": false,
  "latency_ms": 1234
}
```

### 错误响应

```json
{
  "error": "错误类型",
  "detail": "详细错误信息",
  "request_id": "请求追踪ID"
}
```

---

## 接口详情

### 1. POST `/api/v1/chat`

问答接口 - 使用 RAG 生成答案。

**请求体:**

```json
{
  "user_open_id": "ou_xxx",       // 必须，用户飞书 open_id
  "user_name": "张三",              // 必须，用户名
  "question": "私募基金的投资策略？", // 必须，问题（最大 2000 字符）
  "session_id": "uuid",            // 可选，会话 ID
  "doc_ids": ["doc1", "doc2"],     // 可选，指定文档 ID 范围
  "top_k": 5                        // 可选，检索片段数（默认5，最大20）
}
```

**响应:**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "answer": "根据文档内容，私募基金的主要投资策略包括...",
  "citations": [
    {
      "title": "基金产品说明书",
      "document_id": "doccnxxx",
      "score": 0.95
    }
  ],
  "blocked": false,
  "latency_ms": 2341
}
```

**状态码:**

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 422 | 请求参数验证失败 |
| 500 | 服务器内部错误 |

---

### 2. POST `/api/v1/search`

检索接口 - 仅返回相关文档片段，不生成答案。

**请求体:**

```json
{
  "query": "投资策略",               // 必须，检索 query
  "user_open_id": "ou_xxx",         // 可选，用户 ID
  "doc_ids": ["doc1"],              // 可选，指定文档范围
  "top_k": 5                         // 可选，检索数量（默认5）
}
```

**响应:**

```json
{
  "chunks": [
    {
      "content": "私募基金的投资策略包括...",
      "title": "基金产品说明书",
      "document_id": "doccnxxx",
      "score": 0.95,
      "path": "测试文档"
    }
  ],
  "total": 5
}
```

---

### 3. GET `/api/v1/health`

健康检查接口。

**响应:**

```json
{
  "status": "ok",
  "timestamp": 1713432000.123,
  "version": "1.0.0"
}
```

---

### 4. GET `/api/v1/stats`

知识库统计信息。

**响应:**

```json
{
  "active_documents": 150,
  "total_chunks": 3420,
  "daily_chats": 89
}
```

---

## 错误码列表

| HTTP 状态码 | error | 说明 |
|------------|-------|------|
| 400 | Bad Request | 请求格式错误 |
| 404 | Not Found | 端点不存在 |
| 405 | Method Not Allowed | HTTP 方法错误 |
| 422 | Validation Error | 请求参数验证失败 |
| 500 | Internal Server Error | 服务器内部错误 |

---

## 超时配置

- **chat 接口**: 60 秒硬超时
- **search 接口**: 30 秒超时
- **health/stats 接口**: 10 秒超时

---

## 使用示例

### cURL

```bash
# 问答
curl -X POST http://localhost:8080/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_open_id": "ou_test",
    "user_name": "测试用户",
    "question": "私募基金的投资策略有哪些？"
  }'

# 健康检查
curl http://localhost:8080/api/v1/health

# 检索
curl -X POST http://localhost:8080/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "投资策略"}'
```

### Python

```python
import requests

# 问答
resp = requests.post("http://localhost:8080/api/v1/chat", json={
    "user_open_id": "ou_test",
    "user_name": "测试用户",
    "question": "私募基金的投资策略有哪些？",
})
print(resp.json())
```

---

## 启动服务

```bash
python -m rag_service.agent.api
# 或指定端口
RAG_API_PORT=9000 python -m rag_service.agent.api
```

访问 http://localhost:8080/docs 查看自动生成的 Swagger 文档。
