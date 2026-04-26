'use client';

// API route for chat streaming would go here
// In production, this would proxy to wiki_service with auth

export async function POST(request: Request) {
  return new Response(JSON.stringify({ error: 'Not implemented' }), {
    status: 501,
    headers: { 'Content-Type': 'application/json' },
  });
}