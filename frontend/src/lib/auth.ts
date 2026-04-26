import NextAuth, { NextAuthOptions } from "next-auth"

async function refreshFeishuToken(refreshToken: string) {
  const resp = await fetch(
    "https://open.feishu.cn/open-apis/authen/v1/oidc/refresh_access_token",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        grant_type: "refresh_token",
        refresh_token: refreshToken,
        app_id: process.env.FEISHU_APP_ID,
        app_secret: process.env.FEISHU_APP_SECRET,
      }),
    }
  )
  if (!resp.ok) {
    throw new Error(`Feishu token refresh failed: ${resp.status}`)
  }
  return resp.json()
}

const feishuProvider = {
  id: "feishu",
  name: "Feishu",
  type: "oauth" as const,
  authorization: {
    url: "https://open.feishu.cn/open-apis/authen/v1/index",
    params: {
      app_id: process.env.FEISHU_APP_ID!,
      redirect_uri: `${process.env.NEXTAUTH_URL}/api/auth/callback/feishu`,
      response_type: "code",
    },
  },
  token: "https://open.feishu.cn/open-apis/authen/v1/oidc/access_token",
  userinfo: "https://open.feishu.cn/open-apis/authen/v1/user_info",
  profile(profile: any) {
    return {
      id: profile.union_id || profile.user_id,
      name: profile.name,
      email: profile.email,
      image: profile.avatar_url,
      dept_id: profile.dept_id,
    }
  },
  clientId: process.env.FEISHU_APP_ID!,
  clientSecret: process.env.FEISHU_APP_SECRET!,
}

export const authOptions: NextAuthOptions = {
  providers: [feishuProvider],
  session: {
    strategy: "jwt",
    maxAge: 24 * 60 * 60, // 24 hours
  },
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async jwt({ token, user, account, trigger }) {
      if (account) {
        token.accessToken = account.access_token
        token.feishuRefreshToken = account.refresh_token
        token.expiresAt = account.expires_at
      }
      if (user) {
        token.union_id = user.id
      }

      // 如果 access_token 快过期了（5分钟内），刷新它
      const now = Math.floor(Date.now() / 1000)
      if (
        token.expiresAt &&
        token.feishuRefreshToken &&
        token.expiresAt - now < 300 &&
        trigger !== "refresh"
      ) {
        try {
          const refreshed = await refreshFeishuToken(token.feishuRefreshToken as string)
          token.accessToken = refreshed.access_token
          token.feishuRefreshToken = refreshed.refresh_token
          token.expiresAt = refreshed.expires_at
        } catch (err) {
          console.error("Feishu token refresh failed:", err)
          // refresh 失败时清除 token，用户需要重新登录
          token.error = "RefreshError"
        }
      }

      return token
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as any).union_id = token.union_id
        ;(session.user as any).accessToken = token.accessToken
        ;(session.user as any).error = token.error
      }
      return session
    },
  },
}