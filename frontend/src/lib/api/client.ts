// Wiki service API client

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8080';

export interface WikiListResponse {
  pages: Array<{
    title: string;
    path: string;
    type: string;
    access: string;
  }>;
}

export interface QueryResponse {
  answer: string;
  wiki_pages: Array<{ title: string; path: string }>;
  raw_sources: Array<{ title: string; path: string }>;
  confidence: 'high' | 'medium' | 'low';
}

export async function queryWiki(question: string, userId?: string): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, user_id: userId }),
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }

  return res.json();
}

export async function getWikiList(): Promise<WikiListResponse> {
  const res = await fetch(`${API_BASE}/wiki/list`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getWikiPage(path: string): Promise<{ content: string; title: string }> {
  const res = await fetch(`${API_BASE}/wiki/page?path=${encodeURIComponent(path)}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function healthCheck(): Promise<{ status: string; wiki_repo: string; repo_exists: boolean }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}