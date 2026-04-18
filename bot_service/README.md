# PE Knowledge Base Bot

飞书机器人服务 - Step 8 实现

## 项目结构

```
bot_service/
├── src/
│   ├── main.ts            # 入口，启动 WebSocket 长连接
│   ├── config.ts          # 配置管理
│   ├── event-handler.ts   # 飞书事件处理
│   ├── rag-client.ts      # RAG 服务 HTTP 客户端
│   ├── card-renderer.ts   # 飞书消息卡片渲染
│   └── session-manager.ts  # Redis 会话管理
├── tests/
│   ├── step8_idempotent.test.ts
│   └── step8_event-handler.test.ts
├── docs/
│   └── step8-card-schema.md
├── package.json
├── tsconfig.json
└── config.yaml.example
```

## 快速开始

### 1. 安装依赖

```bash
cd bot_service
npm install
```

### 2. 配置

复制配置文件并填入实际值：

```bash
cp config.yaml.example config.yaml
# 编辑 config.yaml 填入 FEISHU_APP_ID, FEISHU_APP_SECRET 等
```

或设置环境变量：

```bash
export FEISHU_APP_ID=cli_xxx
export FEISHU_APP_SECRET=xxx
export RAG_SERVICE_URL=http://localhost:8080
export REDIS_URL=redis://localhost:6379/0
```

### 3. 启动

```bash
# 开发模式
npm run dev

# 生产模式
npm run build
npm start
```

### 4. 验证

```bash
# 测试 RAG 服务连通性
curl http://localhost:8080/api/v1/health

# 检查 Redis
redis-cli ping
```

## 飞书应用配置

### 1. 创建应用

在[飞书开放平台](https://open.feishu.cn/)创建自建应用。

### 2. 申请权限

需要以下权限（P1 为 Step 8 必须）：

| 权限 | 用途 | 必须 |
|------|------|------|
| `im:message.group_at_msg` | 接收群@消息 | ✅ |
| `im:message.p2p_msg` | 接收单聊消息 | ✅ |
| `im:message:send_as_bot` | 发送消息 | ✅ |
| `contact:user.base:readonly` | 读取用户信息 | 可选 |

### 3. 配置事件订阅

1. 在飞书开放平台，进入应用 > 事件订阅
2. 选择「使用长连接接收事件」模式
3. 添加事件：`im.message.receive_v1`

### 4. 机器人能力

开启机器人能力：
- 应用 > 应用能力 > 机器人 > 开启

## API 接口

### 发送消息

```typescript
// 发送文本
await client.im.message.create({
  path: { receive_id: chatId },
  params: { receive_id_type: "chat_id" },
  data: {
    msg_type: "text",
    content: JSON.stringify({ text: "Hello" }),
  },
});

// 发送卡片
await client.im.message.create({
  path: { receive_id: chatId },
  params: { receive_id_type: "chat_id" },
  data: {
    msg_type: "interactive",
    content: JSON.stringify(card),
  },
});
```

## 测试

```bash
# 运行所有测试
npm test

# 运行特定测试
npm test -- --testNamePattern="单聊"
```

## 常见问题

### Q: 机器人没有响应？

1. 检查是否开启了机器人能力
2. 检查事件订阅是否配置了长连接
3. 检查权限是否审批通过

### Q: 消息发送失败？

1. 检查 `im:message:send_as_bot` 权限
2. 检查 `receive_id_type` 是否正确（chat_id / open_id）

### Q: 长连接断开？

SDK 会自动重连。如果频繁断开，检查网络稳定性。
