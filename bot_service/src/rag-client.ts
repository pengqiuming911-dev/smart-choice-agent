"""RAG Service HTTP Client"""
import axios, { AxiosInstance } from "axios";
import { config } from "./config";

export interface ChatRequest {
  user_open_id: string;
  user_name: string;
  question: string;
  session_id?: string;
  doc_ids?: string[];
  top_k?: number;
}

export interface ChatResponse {
  session_id: string;
  answer: string;
  citations: Array<{
    title: string;
    document_id: string;
    score: number;
  }>;
  blocked: boolean;
  latency_ms: number;
}

export interface SearchResponse {
  chunks: Array<{
    content: string;
    title: string;
    document_id: string;
    score: number;
  }>;
  total: number;
}

export class RAGClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: config.ragService.baseUrl,
      timeout: config.ragService.timeout,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }

  async chat(req: ChatRequest): Promise<ChatResponse> {
    try {
      const response = await this.client.post<ChatResponse>("/api/v1/chat", req);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        if (error.code === "ECONNREFUSED") {
          throw new Error("RAG service is not available");
        }
        if (error.code === "ETIMEDOUT") {
          throw new Error("RAG service timeout");
        }
        throw new Error(`RAG service error: ${error.message}`);
      }
      throw error;
    }
  }

  async search(query: string, top_k: number = 5): Promise<SearchResponse> {
    const response = await this.client.post<SearchResponse>("/api/v1/search", {
      query,
      top_k,
    });
    return response.data;
  }

  async health(): Promise<boolean> {
    try {
      const response = await this.client.get("/api/v1/health");
      return response.data.status === "ok";
    } catch {
      return false;
    }
  }
}
