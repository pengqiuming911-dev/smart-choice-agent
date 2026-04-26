import { QueryRequest, QueryResponse, WikiListResponse, WikiContentResponse } from "@/types"

const WIKI_SERVICE_URL = process.env.NEXT_PUBLIC_WIKI_SERVICE_URL || "http://host.docker.internal:8001"

export async function queryWiki(request: QueryRequest): Promise<QueryResponse> {
  const res = await fetch(`${WIKI_SERVICE_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  })
  if (!res.ok) throw new Error(`Query failed: ${res.statusText}`)
  return res.json()
}

export async function getWikiList(): Promise<WikiListResponse> {
  const res = await fetch(`${WIKI_SERVICE_URL}/wiki/list`)
  if (!res.ok) throw new Error(`Failed to list wiki pages: ${res.statusText}`)
  return res.json()
}

export async function getWikiPage(path: string): Promise<WikiContentResponse> {
  const res = await fetch(`${WIKI_SERVICE_URL}/wiki/page?path=${encodeURIComponent(path)}`)
  if (!res.ok) throw new Error(`Failed to get wiki page: ${res.statusText}`)
  return res.json()
}

export async function healthCheck(): Promise<{ status: string; wiki_repo: string; repo_exists: boolean }> {
  const res = await fetch(`${WIKI_SERVICE_URL}/health`)
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`)
  return res.json()
}