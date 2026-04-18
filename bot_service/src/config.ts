// Configuration for PE Knowledge Base Bot
import * as fs from "fs";
import * as path from "path";
import * as yaml from "yaml";

interface BotConfig {
  feishu: {
    appId: string;
    appSecret: string;
    botName: string;
  };
  ragService: {
    baseUrl: string;
    timeout: number;
  };
  redis: {
    url: string;
    sessionTtl: number;
    eventDedupeTtl: number;
  };
}

function loadConfig(): BotConfig {
  // Try to load from env first
  if (process.env.FEISHU_APP_ID && process.env.FEISHU_APP_SECRET) {
    return {
      feishu: {
        appId: process.env.FEISHU_APP_ID,
        appSecret: process.env.FEISHU_APP_SECRET,
        botName: process.env.FEISHU_BOT_NAME || "pe-kb-bot",
      },
      ragService: {
        baseUrl: process.env.RAG_SERVICE_URL || "http://localhost:8080",
        timeout: parseInt(process.env.RAG_TIMEOUT || "60000", 10),
      },
      redis: {
        url: process.env.REDIS_URL || "redis://localhost:6379/0",
        sessionTtl: parseInt(process.env.SESSION_TTL || "3600", 10),
        eventDedupeTtl: parseInt(process.env.EVENT_DEDUPE_TTL || "600", 10),
      },
    };
  }

  // Fallback to config.yaml
  const configPath = path.join(__dirname, "..", "config.yaml");
  if (fs.existsSync(configPath)) {
    const content = fs.readFileSync(configPath, "utf-8");
    return yaml.parse(content) as BotConfig;
  }

  throw new Error("No configuration found. Set env vars or create config.yaml");
}

export const config = loadConfig();
