// Core types for LLM Wiki frontend

// ─── User & Auth ────────────────────────────────────────────────────────────

export interface UserInfo {
  id: string;
  name: string;
  email: string;
  department: string;
  avatar?: string;
  role: 'admin' | 'dept-sales' | 'dept-tech' | 'public';
}

// ─── Conversation ────────────────────────────────────────────────────────────

export interface Conversation {
  id: string;
  title: string;
  group: '今天' | '昨天' | '更早';
  updatedAt: string;
}

// ─── Messages ───────────────────────────────────────────────────────────────

export interface MessageSource {
  title: string;
  url: string;
  type: 'wiki' | 'feishu';
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: MessageSource[];
  createdAt: string;
  confidence?: 'high' | 'medium' | 'low';
}

// ─── Wiki ───────────────────────────────────────────────────────────────────

export interface WikiPage {
  title: string;
  path: string;
  type: 'entity' | 'concept' | 'overview';
  access: 'public' | 'dept-sales' | 'dept-tech' | 'admin';
  lastUpdated?: string;
  sources?: string[];
}

export interface WikiListResponse {
  pages: WikiPage[];
}

// ─── Query ──────────────────────────────────────────────────────────────────

export interface QueryRequest {
  question: string;
  user_id?: string;
}

export interface QueryResponse {
  answer: string;
  wiki_pages: Array<{ title: string; path: string }>;
  raw_sources: Array<{ title: string; path: string }>;
  confidence: 'high' | 'medium' | 'low';
}

// ─── Ingest ─────────────────────────────────────────────────────────────────

export interface IngestRequest {
  doc_token?: string;
  file_path?: string;
}

export interface IngestResponse {
  success: boolean;
  message: string;
  pages_created: number;
  pages_updated: number;
}

// ─── Suggestions ────────────────────────────────────────────────────────────

export interface SuggestionItem {
  key: string;
  title: string;
  category: string;
}

// ─── Capabilities ────────────────────────────────────────────────────────────

export interface CapabilityItem {
  key: string;
  icon: React.ReactNode;
  title: string;
  description: string;
}

// ─── Lint ───────────────────────────────────────────────────────────────────

export interface LintReport {
  orphaned_pages: string[];
  broken_links: string[];
  contradictions: string[];
  stale_pages: string[];
  suggestions: string[];
}