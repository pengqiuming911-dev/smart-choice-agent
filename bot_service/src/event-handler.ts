"""Feishu Event Handler - Process incoming messages and card interactions"""
import { RAGClient, ChatRequest } from "./rag-client";
import { SessionManager } from "./session-manager";
import {
  renderAnswerCard,
  renderErrorCard,
  renderWaitingCard,
} from "./card-renderer";
import { config } from "./config";

// Feishu event types
export interface FeishuEvent {
  schema: string;
  header: {
    event_id: string;
    event_type: string;
    create_time: string;
    token: string;
    app_id: string;
    tenant_key: string;
  };
  event: {
    sender?: {
      sender_id: {
        open_id?: string;
        user_id?: string;
        union_id?: string;
      };
      sender_type: string;
      tenant_key?: string;
    };
    message?: {
      message_id: string;
      root_id?: string;
      parent_id?: string;
      create_time: string;
      chat_id: string;
      chat_type: string; // "p2p" or "group"
      message_type: string;
      content: string; // JSON string
    };
    action?: {
      action_value?: string;
    };
    user?: {
      open_id: string;
      user_id?: string;
      union_id?: string;
    };
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
    // For other message types, try to extract what we can
    return content.content || "";
  } catch {
    return messageContent;
  }
}

/**
 * Check if message is a card interaction callback
 */
function isCardCallback(event: FeishuEvent): boolean {
  return (
    event.header.event_type === "card.action.trigger" ||
    event.event.action?.action_value !== undefined
  );
}

/**
 * Check if bot was mentioned in group message
 */
function isGroupMention(event: FeishuEvent): boolean {
  if (event.event.message?.chat_type !== "group") {
    return false;
  }

  try {
    const content = JSON.parse(event.event.message?.content || "{}");
    // Check if this is a mention event with bot's ID
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
function getUserOpenId(event: FeishuEvent): string {
  // Try message sender first
  if (event.event.message?.sender_id?.open_id) {
    return event.event.message.sender_id.open_id;
  }
  // Try direct user field
  if (event.event.user?.open_id) {
    return event.event.user.open_id;
  }
  // Fallback
  return "unknown";
}

/**
 * Get user name from event (will be resolved via API if needed)
 */
function getUserName(event: FeishuEvent): string {
  if (event.event.sender?.sender_type === "user") {
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
   * Returns card payload to send back, or null to skip
   */
  async handle(event: FeishuEvent): Promise<object | null> {
    // 1. Check for event deduplication
    const eventId = event.header.event_id;
    if (await this.sessionManager.isEventDuplicate(eventId)) {
      console.log(`Duplicate event ${eventId}, skipping`);
      return null;
    }

    // 2. Handle card callback interactions
    if (isCardCallback(event)) {
      return this.handleCardCallback(event);
    }

    // 3. Handle regular messages
    if (event.event.message) {
      return this.handleMessage(event);
    }

    // Unknown event type, skip
    return null;
  }

  /**
   * Handle card button interactions
   */
  private async handleCardCallback(event: FeishuEvent): Promise<object | null> {
    try {
      const actionValue = event.event.action?.action_value;
      if (!actionValue) return null;

      const action = JSON.parse(actionValue);

      if (action.action === "followup") {
        // User clicked "追问" - get session context
        const userOpenId = getUserOpenId(event);
        const session = await this.sessionManager.getSession(userOpenId);

        return {
          type: "text",
          content: `请继续您的追问...\n\n会话ID: ${session.sessionId}\n\n已保存 ${session.turns.length} 条对话历史`,
        };
      }

      if (action.action === "feedback") {
        // User clicked feedback button - log it
        console.log(
          `Feedback: session=${action.session_id} rating=${action.rating}`
        );
        // Could store feedback in DB here
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
  private async handleMessage(event: FeishuEvent): Promise<object | null> {
    const message = event.event.message;
    if (!message) return null;

    const chatType = message.chat_type;
    const messageType = message.message_type;

    // Only handle text messages in p2p or group with mention
    if (messageType !== "text") {
      return null;
    }

    // For group chats, only respond if bot is mentioned
    if (chatType === "group" && !isGroupMention(event)) {
      return null;
    }

    // Extract question from message
    const question = extractMessageText(message.content);
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

    // Call RAG service with timeout
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
    return renderAnswerCard(ragResponse, {
      question,
      sessionId: session.sessionId,
      showFeedback: true,
      feishuDocBaseUrl: "https://.feishu.cn/docx",
    });
  }
}
