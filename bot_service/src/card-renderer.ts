"""Feishu Message Card Renderer"""
import { ChatResponse } from "./rag-client";

export interface CardAction {
  type: "primary" | "default";
  text: string;
  value: string;
}

export interface CardOptions {
  question: string;
  sessionId: string;
  showFeedback: boolean;
  feishuDocBaseUrl?: string;
}

/**
 * Render RAG response as Feishu Interactive Card
 *
 * Card structure:
 * - Header: "知识助手回答"
 * - Body: Answer text
 * - Divider
 * - Citations section (if available)
 * - Footer: Feedback buttons
 */
export function renderAnswerCard(
  ragResponse: ChatResponse,
  options: CardOptions
): object {
  const { question, sessionId, showFeedback, feishuDocBaseUrl } = options;
  const { answer, citations, blocked } = ragResponse;

  // If blocked by compliance, show compliance message
  if (blocked) {
    return renderComplianceCard(question);
  }

  // Build citations section
  const citationElements = citations.length > 0
    ? {
        tag: "div",
        text: {
          tag: "lark_md",
          content: "**引用文档:**\n" + citations
            .map((c, i) => {
              const link = feishuDocBaseUrl
                ? `${feishuDocBaseUrl}/${c.document_id}`
                : null;
              const linkText = link
                ? `[${c.title}](${link})`
                : c.title;
              return `${i + 1}. ${linkText}`;
            })
            .join("\n"),
        },
      }
    : null;

  // Build elements
  const elements: object[] = [
    // Question
    {
      tag: "div",
      text: {
        tag: "lark_md",
        content: `**Q:** ${question}`,
      },
    },
    // Answer
    {
      tag: "div",
      text: {
        tag: "lark_md",
        content: `**A:** ${escapeMarkdown(answer)}`,
      },
    },
  ];

  // Add divider and citations if available
  if (citationElements) {
    elements.push({ tag: "hr" });
    elements.push(citationElements);
  }

  // Add feedback buttons
  if (showFeedback) {
    elements.push({
      tag: "action",
      actions: [
        {
          tag: "button",
          text: {
            tag: "lark_md",
            content: "👍 有用",
          },
          type: "primary",
          value: JSON.stringify({ action: "feedback", session_id: sessionId, rating: "like" }),
        },
        {
          tag: "button",
          text: {
            tag: "lark_md",
            content: "👎 没帮助",
          },
          type: "default",
          value: JSON.stringify({ action: "feedback", session_id: sessionId, rating: "dislike" }),
        },
        {
          tag: "button",
          text: {
            tag: "lark_md",
            content: "🔍 追问",
          },
          type: "default",
          value: JSON.stringify({ action: "followup", session_id: sessionId }),
        },
      ],
    });
  }

  // Card structure
  return {
    schema: "2.0",
    config: {
      WideScreenMode: true,
      ENABLE Forward: true,
    },
    header: {
      title: {
        tag: "plain_text",
        content: "📚 知识助手回答",
      },
      template: "blue",
    },
    elements,
  };
}

/**
 * Render compliance-blocked response
 */
function renderComplianceCard(question: string): object {
  return {
    schema: "2.0",
    config: {
      WideScreenMode: true,
    },
    header: {
      title: {
        tag: "plain_text",
        content: "⚠️ 抱歉，无法回答",
      },
      template: "orange",
    },
    elements: [
      {
        tag: "div",
        text: {
          tag: "lark_md",
          content: `您的问题「${escapeMarkdown(question)}」涉及私募基金的敏感信息。`,
        },
      },
      {
        tag: "div",
        text: {
          tag: "lark_md",
          content:
            "根据监管要求，这类信息仅向合格投资者披露。\n\n" +
            "如需了解更多，请联系您的客户经理或合规部门。",
        },
      },
      {
        tag: "note",
        elements: [
          {
            tag: "plain_text",
            content: "本回答基于内部知识库生成，仅供参考",
          },
        ],
      },
    ],
  };
}

/**
 * Render error card when service is unavailable
 */
export function renderErrorCard(errorMessage: string): object {
  return {
    schema: "2.0",
    config: {
      WideScreenMode: true,
    },
    header: {
      title: {
        tag: "plain_text",
        content: "❌ 服务暂时不可用",
      },
      template: "red",
    },
    elements: [
      {
        tag: "div",
        text: {
          tag: "lark_md",
          content:
            "知识库服务暂时无法响应，请稍后再试。\n\n" +
            `错误信息: ${escapeMarkdown(errorMessage)}`,
        },
      },
      {
        tag: "div",
        text: {
          tag: "lark_md",
          content: "如问题持续存在，请联系技术支持。",
        },
      },
    ],
  };
}

/**
 * Render waiting card while processing
 */
export function renderWaitingCard(): object {
  return {
    schema: "2.0",
    config: {
      WideScreenMode: true,
    },
    header: {
      title: {
        tag: "plain_text",
        content: "🤔 正在思考...",
      },
      template: "blue",
    },
    elements: [
      {
        tag: "div",
        text: {
          tag: "lark_md",
          content: "正在检索知识库，请稍候...",
        },
      },
    ],
  };
}

/**
 * Escape special Markdown characters
 */
function escapeMarkdown(text: string): string {
  // Truncate if too long (Feishu card limit)
  if (text.length > 4000) {
    text = text.substring(0, 4000) + "...\n\n(内容过长已截断)";
  }
  // Escape special characters
  return text
    .replace(/\\/g, "\\\\")
    .replace(/\*/g, "\\*")
    .replace(/_/g, "\\_")
    .replace(/~/g, "\\~")
    .replace(/`/g, "\\`");
}
