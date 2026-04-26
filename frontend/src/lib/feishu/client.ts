// Feishu SDK wrapper

const FEISHU_APP_ID = process.env.NEXT_PUBLIC_FEISHU_APP_ID || '';
const FEISHU_OAUTH_URL = 'https://open.feishu.cn/open-apis/authen/v1';
const FEISHU_API_BASE = 'https://open.feishu.cn/open-apis';

export interface FeishuUser {
  union_id: string;
  name: string;
  email: string;
  avatar_url?: string;
  dept_id?: string;
}

export function getFeishuOAuthUrl(redirectUri: string): string {
  const params = new URLSearchParams({
    app_id: FEISHU_APP_ID,
    redirect_uri: redirectUri,
  });
  return `${FEISHU_OAUTH_URL}/authorize?${params.toString()}`;
}

export async function exchangeCodeForToken(code: string): Promise<{
  access_token: string;
  refresh_token: string;
  expires_in: number;
}> {
  const res = await fetch(`${FEISHU_API_BASE}/authen/v1/oidc/access_token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ grant_type: 'authorization_code', code }),
  });
  if (!res.ok) throw new Error('Failed to exchange code');
  return res.json();
}

export async function getFeishuUserInfo(accessToken: string): Promise<FeishuUser> {
  const res = await fetch(`${FEISHU_API_BASE}/authen/v1/user_info`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) throw new Error('Failed to get user info');
  return res.json();
}