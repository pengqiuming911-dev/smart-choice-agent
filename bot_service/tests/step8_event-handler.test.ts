/** Step 8: Event Handler Test */
import { EventHandler, FeishuEvent } from "../src/event-handler";
import { RAGClient } from "../src/rag-client";
import { SessionManager } from "../src/session-manager";

// Mock RAG Client
const mockRAGClient: RAGClient = {
  chat: jest.fn(),
  search: jest.fn(),
  health: jest.fn().mockResolvedValue(true),
} as unknown as RAGClient;

// Mock Session Manager
const mockSessionManager: SessionManager = {
  getSession: jest.fn().mockResolvedValue({
    sessionId: "test-session-001",
    userOpenId: "ou_test_user",
    turns: [],
    lastActivity: Date.now(),
  }),
  addTurn: jest.fn(),
  isEventDuplicate: jest.fn().mockResolvedValue(false),
  ping: jest.fn().mockResolvedValue(true),
  close: jest.fn(),
} as unknown as SessionManager;

describe("EventHandler", () => {
  let handler: EventHandler;

  beforeEach(() => {
    jest.clearAllMocks();
    handler = new EventHandler({
      ragClient: mockRAGClient,
      sessionManager: mockSessionManager,
    });
  });

  describe("handle", () => {
    test("T1: 单聊正常问答", async () => {
      // Mock RAG response
      (mockRAGClient.chat as jest.Mock).mockResolvedValue({
        session_id: "test-session-001",
        answer: "私募基金的投资策略包括...",
        citations: [
          { title: "基金产品手册", document_id: "doc_001", score: 0.95 },
        ],
        blocked: false,
        latency_ms: 1234,
      });

      const event: FeishuEvent = {
        schema: "2.0",
        header: {
          event_id: "evt_001",
          event_type: "im.message.receive_v1",
          create_time: "2024-01-01T00:00:00Z",
          token: "test-token",
          app_id: "cli_test",
          tenant_key: "test_tenant",
        },
        event: {
          sender: {
            sender_id: { open_id: "ou_test_user" },
            sender_type: "user",
          },
          message: {
            message_id: "msg_001",
            create_time: "2024-01-01T00:00:00Z",
            chat_id: "chat_001",
            chat_type: "p2p",
            message_type: "text",
            content: JSON.stringify({ text: "私募基金的投资策略有哪些？" }),
          },
        },
      };

      const response = await handler.handle(event);

      expect(response).toBeDefined();
      expect(response).toHaveProperty("schema", "2.0");
      expect(mockRAGClient.chat).toHaveBeenCalledWith(
        expect.objectContaining({
          user_open_id: "ou_test_user",
          question: "私募基金的投资策略有哪些？",
        })
      );
    });

    test("T2: 群聊 @ 问答", async () => {
      (mockRAGClient.chat as jest.Mock).mockResolvedValue({
        session_id: "test-session-002",
        answer: "根据公司流程...",
        citations: [],
        blocked: false,
        latency_ms: 1000,
      });

      const event: FeishuEvent = {
        schema: "2.0",
        header: {
          event_id: "evt_002",
          event_type: "im.message.receive_v1",
          create_time: "2024-01-01T00:00:00Z",
          token: "test-token",
          app_id: "cli_test",
          tenant_key: "test_tenant",
        },
        event: {
          sender: {
            sender_id: { open_id: "ou_test_user" },
            sender_type: "user",
          },
          message: {
            message_id: "msg_002",
            create_time: "2024-01-01T00:00:00Z",
            chat_id: "chat_group",
            chat_type: "group",
            message_type: "text",
            content: JSON.stringify({
              text: "@bot 公司流程是什么？",
              mentions: [{ key: "@bot", id: { type: "open_id", id: "cli_test" } }],
            }),
          },
        },
      };

      const response = await handler.handle(event);

      expect(response).toBeDefined();
      expect(mockRAGClient.chat).toHaveBeenCalled();
    });

    test("T3: 群里普通消息不响应", async () => {
      const event: FeishuEvent = {
        schema: "2.0",
        header: {
          event_id: "evt_003",
          event_type: "im.message.receive_v1",
          create_time: "2024-01-01T00:00:00Z",
          token: "test-token",
          app_id: "cli_test",
          tenant_key: "test_tenant",
        },
        event: {
          sender: {
            sender_id: { open_id: "ou_test_user" },
            sender_type: "user",
          },
          message: {
            message_id: "msg_003",
            create_time: "2024-01-01T00:00:00Z",
            chat_id: "chat_group",
            chat_type: "group",
            message_type: "text",
            content: JSON.stringify({ text: "你好" }),
          },
        },
      };

      const response = await handler.handle(event);

      // Should return null because bot is not mentioned
      expect(response).toBeNull();
      expect(mockRAGClient.chat).not.toHaveBeenCalled();
    });

    test("T4: 合规拦截展示", async () => {
      (mockRAGClient.chat as jest.Mock).mockResolvedValue({
        session_id: "test-session-004",
        answer: "抱歉，无法提供此类信息",
        citations: [],
        blocked: true,
        latency_ms: 500,
      });

      const event: FeishuEvent = {
        schema: "2.0",
        header: {
          event_id: "evt_004",
          event_type: "im.message.receive_v1",
          create_time: "2024-01-01T00:00:00Z",
          token: "test-token",
          app_id: "cli_test",
          tenant_key: "test_tenant",
        },
        event: {
          sender: {
            sender_id: { open_id: "ou_test_user" },
            sender_type: "user",
          },
          message: {
            message_id: "msg_004",
            create_time: "2024-01-01T00:00:00Z",
            chat_id: "chat_001",
            chat_type: "p2p",
            message_type: "text",
            content: JSON.stringify({ text: "A基金净值是多少？" }),
          },
        },
      };

      const response = await handler.handle(event);

      expect(response).toBeDefined();
      // Should show compliance card
      expect(response).toHaveProperty("schema", "2.0");
    });

    test("T7: 机器人离线时返回友好提示", async () => {
      (mockRAGClient.chat as jest.Mock).mockRejectedValue(
        new Error("RAG service is not available")
      );

      const event: FeishuEvent = {
        schema: "2.0",
        header: {
          event_id: "evt_007",
          event_type: "im.message.receive_v1",
          create_time: "2024-01-01T00:00:00Z",
          token: "test-token",
          app_id: "cli_test",
          tenant_key: "test_tenant",
        },
        event: {
          sender: {
            sender_id: { open_id: "ou_test_user" },
            sender_type: "user",
          },
          message: {
            message_id: "msg_007",
            create_time: "2024-01-01T00:00:00Z",
            chat_id: "chat_001",
            chat_type: "p2p",
            message_type: "text",
            content: JSON.stringify({ text: "测试问题" }),
          },
        },
      };

      const response = await handler.handle(event);

      expect(response).toBeDefined();
      // Should return error card
      expect(response).toHaveProperty("schema", "2.0");
    });
  });
});
