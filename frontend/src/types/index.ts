import { DefaultSession } from "next-auth"

declare module "next-auth" {
  interface Session {
    user: {
      union_id?: string
      accessToken?: string
    } & DefaultSession["user"]
  }
}

export interface QueryRequest {
  question: string
  user_id?: string
}

export interface WikiPage {
  title: string
  path: string
}

export interface RawSource {
  title: string
  path: string
}

export interface QueryResponse {
  answer: string
  wiki_pages: WikiPage[]
  raw_sources: RawSource[]
  confidence: string
}

export interface WikiPageItem {
  title: string
  path: string
  type: string
  access: string
}

export interface WikiListResponse {
  pages: WikiPageItem[]
}

export interface WikiContentResponse {
  content: string
  title: string
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  wiki_pages?: WikiPage[]
  raw_sources?: RawSource[]
  confidence?: string
  created_at?: string
}