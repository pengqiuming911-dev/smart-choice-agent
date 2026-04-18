// Feishu Event Handler - Process incoming messages and card interactions

import { RAGClient, ChatRequest } from "./rag-client";
import { SessionManager } from "./session-manager";
import {
  renderAnswerCard,
  renderErrorCard,
} from "./card-renderer";
import { config } from "./config";

// Feishu event from SDK
interface FeishuMessageEvent {
  event_id?: string;
  token?: string;
  create_time?: string;
  event_type?: string;
  tenant_key?: string;
  ts?: string;
  uuid?: string;
  type?: string;
  app_id?: string;
  sender: {
    sender_id?: {
      union_id?: string;
      user_id?: string;
      open_id?: string;
    };
    sender_type: string;
    tenant_key?: string;
  };
  message: {
    message_id: string;
    root_id?: string;
    parent_id?: string;
    create_time: string;
    update_time?: string;
    chat_id: string;
    thread_id?: string;
    chat_type: string;
    message_type: string;
    content: string;
    mentions?: Array<{
      key: string;
      id: {
        type: string;
        id: string;
      };
    }>;
  };
}

export interface EventHandlerDeps {
  ragClient: RAGClient;
  sessionManager: SessionManager;
}

/**
 * Extract text content from Feishu message
 */
function extractMessageText(messageContent: string): string {
  try {
    const content = JSON.parse(messageContent);
    if (content.text) {
      return content.text;
    }
    return content.content || "";
  } catch {
    return messageContent;
  }
}

/**
 * Check if bot was mentioned in group message
 */
function isGroupMention(event: FeishuMessageEvent): boolean {
  if (event.message.chat_type !== "group") {
    return false;
  }

  try {
    const content = JSON.parse(event.message.content || "{}");
    return content.mentions?.some(
      (m: { key: string; id: { type: string; id: string } }) =>
        m.id?.type === "open_id" && m.id?.id === config.feishu.appId
    );
  } catch {
    return false;
  }
}

/**
 * Get user open_id from event
 */
function getUserOpenId(event: FeishuMessageEvent): string {
  if (event.sender?.sender_id?.open_id) {
    return event.sender.sender_id.open_id;
  }
  return "unknown";
}

/**
 * Get user name from event
 */
function getUserName(event: FeishuMessageEvent): string {
  if (event.sender?.sender_type === "user") {
    return `User_${getUserOpenId(event).slice(-8)}`;
  }
  return "Unknown User";
}

/**
 * Event Handler class
 */
export class EventHandler {
  private ragClient: RAGClient;
  private sessionManager: SessionManager;

  constructor(deps: EventHandlerDeps) {
    this.ragClient = deps.ragClient;
    this.sessionManager = deps.sessionManager;
  }

  /**
   * Process incoming Feishu event
   */
  async handle(event: FeishuMessageEvent): Promise<object | null> {
    // 1. Check for event deduplication
    const eventId = event.event_id || event.uuid || "";
    if (await this.sessionManager.isEventDuplicate(eventId)) {
      console.log(`Duplicate event ${eventId}, skipping`);
      return null;
    }

    // 2. Handle card callback interactions
    if (event.message.message_type === "interactive") {
      return this.handleCardCallback(event);
    }

    // 3. Handle regular text messages
    if (event.message.message_type === "text") {
      return this.handleMessage(event);
    }

    // Unknown event type, skip
    return null;
  }

  /**
   * Handle card button interactions
   */
  private async handleCardCallback(event: FeishuMessageEvent): Promise<object | null> {
    try {
      const content = JSON.parse(event.message.content);
      const actionValue = content.action?.value;

      if (!actionValue) return null;

      const action = JSON.parse(actionValue);

      if (action.action === "followup") {
        const userOpenId = getUserOpenId(event);
        const session = await this.sessionManager.getSession(userOpenId);

        return {
          type: "text",
          content: `请继续您的追问...\n\n会话ID: ${session.sessionId}\n\n已保存 ${session.turns.length} 条对话历史`,
        };
      }

      if (action.action === "feedback") {
        console.log(
          `Feedback: session=${action.session_id} rating=${action.rating}`
        );
        return {
          type: "text",
          content: "感谢您的反馈！",
        };
      }

      return null;
    } catch (err) {
      console.error("Error handling card callback:", err);
      return null;
    }
  }

  /**
   * Handle regular chat messages
   */
  private async handleMessage(event: FeishuMessageEvent): Promise<object | null> {
    const chatType = event.message.chat_type;

    // For group chats, only respond if bot is mentioned
    if (chatType === "group" && !isGroupMention(event)) {
      return null;
    }

    // Extract question from message
    const question = extractMessageText(event.message.content);
    if (!question.trim()) {
      return null;
    }

    const userOpenId = getUserOpenId(event);
    const userName = getUserName(event);

    // Get session for context
    const session = await this.sessionManager.getSession(userOpenId);

    // Prepare RAG request
    const ragRequest: ChatRequest = {
      user_open_id: userOpenId,
      user_name: userName,
      question: question,
      session_id: session.sessionId,
      top_k: 5,
    };

    // Call RAG service
    let ragResponse;
    try {
      ragResponse = await this.ragClient.chat(ragRequest);
    } catch (err) {
      console.error("RAG call failed:", err);
      return renderErrorCard(
        err instanceof Error ? err.message : "Unknown error"
      );
    }

    // Save to conversation history
    await this.sessionManager.addTurn(userOpenId, question, ragResponse.answer);

    // Render response card
    const card = renderAnswerCard(ragResponse, {
      question,
      sessionId: session.sessionId,
      showFeedback: true,
      feishuDocBaseUrl: "https://.feishu.cn/docx",
    });

    // Return combined response (card + raw data for text fallback)
    return {
      card,
      answer: ragResponse.answer,
      citations: ragResponse.citations,
      blocked: ragResponse.blocked,
    };
  }
}
