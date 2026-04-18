"""Session Manager using Redis for multi-turn conversation context"""
import Redis from "ioredis";
import { config } from "./config";

interface ConversationTurn {
  question: string;
  answer: string;
  timestamp: number;
}

interface Session {
  sessionId: string;
  userOpenId: string;
  turns: ConversationTurn[];
  lastActivity: number;
}

/**
 * Session Manager for handling multi-turn conversations
 *
 * Stores conversation history in Redis with TTL
 */
export class SessionManager {
  private redis: Redis;
  private readonly MAX_TURNS = 5; // Keep last N turns

  constructor() {
    this.redis = new Redis(config.redis.url, {
      maxRetriesPerRequest: 3,
      retryDelayOnFailover: 100,
    });

    this.redis.on("error", (err) => {
      console.error("Redis connection error:", err.message);
    });

    this.redis.on("connect", () => {
      console.log("Redis connected");
    });
  }

  /**
   * Get or create a session for user
   */
  async getSession(userOpenId: string): Promise<Session> {
    const key = `session:${userOpenId}`;
    const data = await this.redis.get(key);

    if (data) {
      return JSON.parse(data) as Session;
    }

    // Create new session
    const session: Session = {
      sessionId: this.generateSessionId(),
      userOpenId,
      turns: [],
      lastActivity: Date.now(),
    };

    await this.saveSession(session);
    return session;
  }

  /**
   * Add a turn to the conversation history
   */
  async addTurn(
    userOpenId: string,
    question: string,
    answer: string
  ): Promise<Session> {
    const session = await this.getSession(userOpenId);

    session.turns.push({
      question,
      answer,
      timestamp: Date.now(),
    });

    // Keep only last N turns
    if (session.turns.length > this.MAX_TURNS) {
      session.turns = session.turns.slice(-this.MAX_TURNS);
    }

    session.lastActivity = Date.now();
    await this.saveSession(session);

    return session;
  }

  /**
   * Get conversation history formatted for RAG context
   */
  async getHistoryContext(userOpenId: string): Promise<string> {
    const session = await this.getSession(userOpenId);

    if (session.turns.length === 0) {
      return "";
    }

    const historyParts = session.turns.map(
      (turn, i) =>
        `对话 ${i + 1}:\n问: ${turn.question}\n答: ${turn.answer}`
    );

    return historyParts.join("\n\n");
  }

  /**
   * Check if event is duplicate (for deduplication)
   */
  async isEventDuplicate(eventId: string): Promise<boolean> {
    const key = `event:${eventId}`;
    const exists = await this.redis.exists(key);

    if (exists) {
      return true;
    }

    // Mark as processed with TTL
    await this.redis.setex(key, config.redis.eventDedupeTtl, "1");
    return false;
  }

  /**
   * Close session for user
   */
  async closeSession(userOpenId: string): Promise<void> {
    const key = `session:${userOpenId}`;
    await this.redis.del(key);
  }

  /**
   * Save session to Redis
   */
  private async saveSession(session: Session): Promise<void> {
    const key = `session:${session.userOpenId}`;
    await this.redis.setex(key, config.redis.sessionTtl, JSON.stringify(session));
  }

  /**
   * Generate unique session ID
   */
  private generateSessionId(): string {
    return `sess_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
  }

  /**
   * Health check
   */
  async ping(): Promise<boolean> {
    try {
      const result = await this.redis.ping();
      return result === "PONG";
    } catch {
      return false;
    }
  }

  /**
   * Close Redis connection
   */
  async close(): Promise<void> {
    await this.redis.quit();
  }
}
