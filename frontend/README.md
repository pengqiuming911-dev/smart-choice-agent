# LLM Wiki — 智能知识库前端

基于 Next.js 15 + React 19 + Ant Design 的企业级知识库问答前端,完全还原字节系产品风格。

## 技术栈

- **框架**: Next.js 15 (App Router)
- **UI 组件**: Ant Design 5.x
- **AI 组件**: Ant Design X
- **语言**: TypeScript 5
- **样式**: 内联 + 全局 CSS

## 目录结构

```
src/
├── app/                    # Next.js App Router 入口
│   ├── layout.tsx         # 全局 Layout + ConfigProvider
│   ├── page.tsx           # 首页路由
│   └── globals.css        # 全局样式
├── components/             # UI 组件
│   ├── Sidebar.tsx        # 左侧会话栏
│   ├── ChatHeader.tsx     # 顶部 Header
│   ├── Welcome.tsx        # 欢迎区
│   ├── Suggestions.tsx    # 推荐问题
│   ├── Capabilities.tsx   # 能力卡片
│   └── ChatInput.tsx      # 底部输入框
├── pages/
│   └── ChatPage.tsx       # 主聊天页面
└── types/
    └── index.ts           # TypeScript 类型定义
```

## 安装与运行

```bash
# 1. 安装依赖
pnpm install
# 或 npm install / yarn install

# 2. 启动开发服务器
pnpm dev

# 3. 打开浏览器访问
http://localhost:3000
```

## 设计风格说明

参考字节系产品(飞书、扣子、豆包)的设计语言:

- **主色**: `#3B6AF8` (字节蓝)
- **背景**: 主区 `#fff`, 侧栏 `#F7F8FA`
- **边框**: `#EBEDF0` (淡灰)
- **文字层级**: 主 `#1F2329`, 次 `#4E5969`, 弱 `#8F959E`
- **圆角**: 统一 8~12px

## 后续接入点

### 1. 接入 LLM 流式响应

修改 `ChatPage.tsx` 的 `handleSend`:

```typescript
const handleSend = async () => {
  // 用 Vercel AI SDK 的 useChat
  const response = await fetch('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ message: inputValue }),
  });
  // 处理流式返回...
};
```

### 2. 接入飞书登录

参考设计文档第十章 2.1 节:使用 NextAuth.js v5 + 自定义 Feishu Provider。

### 3. 添加消息流展示

新增 `MessageList.tsx` 组件,使用 Ant Design X 的 `Bubble` 组件展示对话气泡。

## 颜色对照表

| 用途 | 颜色值 |
|------|--------|
| 品牌主色 | `#3B6AF8` |
| 主色浅版(高亮背景) | `#E6EFFE` |
| 文字主色 | `#1F2329` |
| 文字次色 | `#4E5969` |
| 文字弱色 | `#8F959E` |
| 边框色 | `#EBEDF0` |
| 侧栏背景 | `#F7F8FA` |
