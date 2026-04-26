'use client';

// Feishu webhook handler would go here

export async function POST(request: Request) {
  return new Response(JSON.stringify({ error: 'Not implemented' }), {
    status: 501,
    headers: { 'Content-Type': 'application/json' },
  });
}