"""PE Knowledge Base Bot - Main Entry Point"""
import "dotenv/config";
import { config } from "./config";
import { RAGClient } from "./rag-client";
import { SessionManager } from "./session-manager";
import { EventHandler, FeishuEvent } from "./event-handler";
import { Client, Constants } from "@larksuiteoapi/node-sdk";

// Initialize clients
const ragClient = new RAGClient();
const sessionManager = new SessionManager();
const eventHandler = new EventHandler({ ragClient, sessionManager });

// Initialize Feishu client with WebSocket mode (WsClient)
// This avoids needing a public IP for webhook callbacks
const client = new Client({
  appId: config.feishu.appId,
  appSecret: config.feishu.appSecret,
  loggerLevel: Constants.LoggerLevel.info,
});

// Event types to subscribe
const subscribedEvents = [
  "im.message.receive_v1", // Receive messages
];

// Create message event handler
const messageHandler = async (data: FeishuEvent) => {
  console.log(
    `Received event: ${data.header.event_type} from ${data.event.message?.sender_id?.open_id || "unknown"
    }`
  );

  try {
    const response = await eventHandler.handle(data);

    if (response === null) {
      console.log("Event handled, no response needed");
      return;
    }

    // If it's a card, send it back as an update
    if (data.event.message && data.event.message.message_id) {
      const message = data.event.message;

      if ("content" in response && typeof response === "object" && "type" in response) {
        // It's a card
        await sendCardMessage(message.chat_id, response as object, message.message_id);
      } else if (typeof response === "object" && "type" in response && (response as any).type === "text") {
        // It's a text response
        await sendTextMessage(message.chat_id, (response as any).content, message.message_id);
      }
    }
  } catch (err) {
    console.error("Error processing event:", err);
  }
};

/**
 * Send text message reply
 */
async function sendTextMessage(
  chatId: string,
  content: string,
  replyMessageId?: string
): Promise<void> {
  try {
    await client.im.message.create({
      path: { receive_id: chatId },
      params: {
        receive_id_type: "chat_id",
      },
      data: {
        msg_type: "text",
        content: JSON.stringify({ text: content }),
        reply_in_thread_id: replyMessageId || undefined,
      },
    });
  } catch (err) {
    console.error("Failed to send text message:", err);
  }
}

/**
 * Send interactive card message
 */
async function sendCardMessage(
  chatId: string,
  card: object,
  replyMessageId?: string
): Promise<void> {
  try {
    await client.im.message.create({
      path: { receive_id: chatId },
      params: {
        receive_id_type: "chat_id",
      },
      data: {
        msg_type: "interactive",
        content: JSON.stringify(card),
        reply_in_thread_id: replyMessageId || undefined,
      },
    });
  } catch (err) {
    console.error("Failed to send card message:", err);
  }
}

/**
 * Start the bot service
 */
async function main() {
  console.log("Starting PE Knowledge Base Bot...");
  console.log(`App ID: ${config.feishu.appId}`);
  console.log(`RAG Service: ${config.ragService.baseUrl}`);

  // Check RAG service health
  const ragHealthy = await ragClient.health();
  console.log(`RAG Service health: ${ragHealthy ? "OK" : "UNAVAILABLE"}`);

  // Check Redis health
  const redisHealthy = await sessionManager.ping();
  console.log(`Redis health: ${redisHealthy ? "OK" : "UNAVAILABLE"}`);

  // Subscribe to events using persistent WebSocket connection
  // This keeps the bot running and automatically reconnects
  client.event.subscribe("im.message.receive_v1", messageHandler);

  console.log("Bot is running. Press Ctrl+C to stop.");

  // Keep process alive
  process.on("SIGINT", async () => {
    console.log("\nShutting down...");
    await sessionManager.close();
    process.exit(0);
  });
}

// Run
main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
