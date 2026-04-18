# Step 8: 飞书消息卡片 Schema

## 概述

本文档记录 PE 知识库机器人的飞书消息卡片 JSON Schema。

## 答案卡片

用户正常问答时返回的卡片。

```json
{
  "schema": "2.0",
  "config": {
    "WideScreenMode": true,
    "enable_forward": true
  },
  "header": {
    "title": {
      "tag": "plain_text",
      "content": "📚 知识助手回答"
    },
    "template": "blue"
  },
  "elements": [
    {
      "tag": "div",
      "text": {
        "tag": "lark_md",
        "content": "**Q:** 私募基金的投资策略有哪些？"
      }
    },
    {
      "tag": "div",
      "text": {
        "tag": "lark_md",
        "content": "**A:** 根据文档内容，私募基金的主要投资策略包括...\n\n（答案正文）"
      }
    },
    {
      "tag": "hr"
    },
    {
      "tag": "div",
      "text": {
        "tag": "lark_md",
        "content": "**引用文档:**\n1. [基金产品手册](https://.feishu.cn/docx/doc_id_1)\n2. [投资策略说明](https://feishu.cn/docx/doc_id_2)"
      }
    },
    {
      "tag": "action",
      "actions": [
        {
          "tag": "button",
          "text": {
            "tag": "lark_md",
            "content": "👍 有用"
          },
          "type": "primary",
          "value": "{\"action\":\"feedback\",\"session_id\":\"sess_xxx\",\"rating\":\"like\"}"
        },
        {
          "tag": "button",
          "text": {
            "tag": "lark_md",
            "content": "👎 没帮助"
          },
          "type": "default",
          "value": "{\"action\":\"feedback\",\"session_id\":\"sess_xxx\",\"rating\":\"dislike\"}"
        },
        {
          "tag": "button",
          "text": {
            "tag": "lark_md",
            "content": "🔍 追问"
          },
          "type": "default",
          "value": "{\"action\":\"followup\",\"session_id\":\"sess_xxx\"}"
        }
      ]
    }
  ]
}
```

### 卡片元素说明

| 元素 | 说明 | 限制 |
|------|------|------|
| header | 卡片标题栏 | 必须 |
| elements | 内容区 | 必须 |
| actions | 按钮区 | MVP 可选 |

## 合规拦截卡片

用户问及敏感信息但未认证时返回。

```json
{
  "schema": "2.0",
  "config": {
    "WideScreenMode": true
  },
  "header": {
    "title": {
      "tag": "plain_text",
      "content": "⚠️ 抱歉，无法回答"
    },
    "template": "orange"
  },
  "elements": [
    {
      "tag": "div",
      "text": {
        "tag": "lark_md",
        "content": "您的问题「A基金净值是多少」涉及私募基金的敏感信息。"
      }
    },
    {
      "tag": "div",
      "text": {
        "tag": "lark_md",
        "content": "根据监管要求，这类信息仅向合格投资者披露。\n\n如需了解更多，请联系您的客户经理或合规部门。"
      }
    },
    {
      "tag": "note",
      "elements": [
        {
          "tag": "plain_text",
          "content": "本回答基于内部知识库生成，仅供参考"
        }
      ]
    }
  ]
}
```

## 错误卡片

RAG 服务不可用时返回。

```json
{
  "schema": "2.0",
  "config": {
    "WideScreenMode": true
  },
  "header": {
    "title": {
      "tag": "plain_text",
      "content": "❌ 服务暂时不可用"
    },
    "template": "red"
  },
  "elements": [
    {
      "tag": "div",
      "text": {
        "tag": "lark_md",
        "content": "知识库服务暂时无法响应，请稍后再试。\n\n错误信息: Connection refused"
      }
    },
    {
      "tag": "div",
      "text": {
        "tag": "lark_md",
        "content": "如问题持续存在，请联系技术支持。"
      }
    }
  ]
}
```

## 按钮交互

卡片按钮点击后，`event.action.action_value` 包含 JSON:

```json
// 反馈按钮
{"action": "feedback", "session_id": "sess_xxx", "rating": "like"}

// 追问按钮
{"action": "followup", "session_id": "sess_xxx"}
```

## 模板颜色

| 模板 | 用途 |
|------|------|
| blue | 正常回答 |
| orange | 警告/合规拦截 |
| red | 错误 |
| green | 成功 |
| grey | 普通提示 |

## 注意事项

1. **内容长度**: 答案正文超过 4000 字符时自动截断
2. **Markdown**: 使用 `lark_md` 标签支持 Markdown 格式
3. **链接**: 引用文档使用标准 Markdown 链接格式
4. **按钮值**: 必须为合法 JSON 字符串
