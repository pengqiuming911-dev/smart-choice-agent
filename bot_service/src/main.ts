// PE Knowledge Base Bot - Main Entry Point

import "dotenv/config";
import * as lark from "@larksuiteoapi/node-sdk";
import { config } from "./config";
import { RAGClient } from "./rag-client";
import { SessionManager } from "./session-manager";
import { EventHandler } from "./event-handler";

// Initialize clients
const ragClient = new RAGClient();
const sessionManager = new SessionManager();
const eventHandler = new EventHandler({ ragClient, sessionManager });

// Create Feishu client
const client = new lark.Client({
  appId: config.feishu.appId,
  appSecret: config.feishu.appSecret,
  loggerLevel: lark.LoggerLevel.info,
});

// Event dispatcher - register handlers using SDK's event type
const eventDispatcher = new lark.EventDispatcher({}).register({
  "im.message.receive_v1": async (data: any) => {
    console.log(
      `Received event: ${data.event_type} from ${data.sender?.sender_id?.open_id || "unknown"}`
    );

    try {
      const response = await eventHandler.handle(data);

      if (response === null) {
        console.log("Event handled, no response needed");
        return;
      }

      // Send response as text for now (debugging card format)
      if (data.message && data.message.message_id) {
        const chatId = data.message.chat_id;

        // Always send as text to verify RAG flow works
        if ("answer" in (response as any)) {
          const answer = (response as any).answer || "无回答";
          const citations = (response as any).citations || [];
          let text = `${answer}`;
          if (citations.length > 0) {
            text += `\n\n引用文档:\n${citations.map((c: any, i: number) => `${i+1}. ${c.title}`).join("\n")}`;
          }
          await sendTextMessage(chatId, text);
        } else {
          await sendTextMessage(chatId, JSON.stringify(response));
        }
      }
    } catch (err) {
      console.error("Error processing event:", err);
    }
  },
});

// WebSocket client for long connection
const wsClient = new lark.WSClient({
  appId: config.feishu.appId,
  appSecret: config.feishu.appSecret,
});

/**
 * Send text message reply
 */
async function sendTextMessage(chatId: string, content: string): Promise<void> {
  try {
    await client.im.message.create({
      params: {
        receive_id_type: "chat_id",
      },
      data: {
        receive_id: chatId,
        msg_type: "text",
        content: JSON.stringify({ text: content }),
      },
    });
  } catch (err) {
    console.error("Failed to send text message:", err);
  }
}

/**
 * Send interactive card message
 */
async function sendCardMessage(chatId: string, card: object): Promise<void> {
  try {
    await client.im.message.create({
      params: {
        receive_id_type: "chat_id",
      },
      data: {
        receive_id: chatId,
        msg_type: "interactive",
        content: JSON.stringify(card),
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

  // Start WebSocket client with event dispatcher
  await wsClient.start({
    eventDispatcher: eventDispatcher,
  });

  console.log("Bot is running. Press Ctrl+C to stop.");

  // Keep process alive
  process.on("SIGINT", async () => {
    console.log("\nShutting down...");
    await sessionManager.close();
    wsClient.close({ force: true });
    process.exit(0);
  });
}

// Run
main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
