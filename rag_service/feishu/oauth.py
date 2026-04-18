"""Feishu OAuth 2.0 user authorization flow"""
import os
import webbrowser
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Feishu OAuth config
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_REDIRECT_URI = os.getenv("FEISHU_REDIRECT_URI", "http://localhost:8080/callback")
FEISHU_OAUTH_URL = "https://open.feishu.cn/open-apis/authen/v1/authorize"
FEISHU_TOKEN_URL = "https://open.feishu.cn/open-apis/authen/v1/oidc/access_token"


class FeishuOAuth:
    """Feishu OAuth 2.0 authorization handler"""

    def __init__(self, app_id: str = None, redirect_uri: str = None):
        self.app_id = app_id or FEISHU_APP_ID
        self.redirect_uri = redirect_uri or FEISHU_REDIRECT_URI

    def get_authorization_url(self, state: str = None) -> str:
        """
        Generate the OAuth authorization URL for user to scan.

        Returns:
            URL string for user to visit and scan QR code
        """
        import urllib.parse

        # Request necessary scopes for wiki and drive access
        # wiki:wiki - read wiki spaces and folders
        # drive:drive - read drive files and folders
        scopes = ["wiki:wiki", "drive:drive"]

        params = {
            "app_id": self.app_id,
            "redirect_uri": self.redirect_uri,
            "state": state or "random_state_string",
            "scope": " ".join(scopes),
        }
        query = urllib.parse.urlencode(params)
        return f"{FEISHU_OAUTH_URL}?{query}"

    def exchange_code_for_token(self, code: str) -> dict:
        """
        Exchange authorization code for user access token.

        Args:
            code: The authorization code from callback

        Returns:
            Token response with access_token, refresh_token, etc.
        """
        import httpx

        resp = httpx.post(
            FEISHU_TOKEN_URL,
            json={
                "grant_type": "authorization_code",
                "code": code,
            },
            headers={
                "Authorization": f"Bearer {self._get_app_token()}",
                "Content-Type": "application/json",
            },
            timeout=30,
        ).json()

        if resp.get("code") != 0:
            raise RuntimeError(f"Token exchange failed: {resp}")

        return resp.get("data", {})

    def refresh_user_token(self, refresh_token: str) -> dict:
        """
        Refresh user access token using refresh token.

        Args:
            refresh_token: The refresh token from previous authorization

        Returns:
            New token response
        """
        import httpx

        resp = httpx.post(
            FEISHU_TOKEN_URL,
            json={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            headers={
                "Authorization": f"Bearer {self._get_app_token()}",
                "Content-Type": "application/json",
            },
            timeout=30,
        ).json()

        if resp.get("code") != 0:
            raise RuntimeError(f"Token refresh failed: {resp}")

        return resp.get("data", {})

    def _get_app_token(self) -> str:
        """Get app access token for API calls"""
        import httpx

        resp = httpx.post(
            "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal",
            json={
                "app_id": self.app_id,
                "app_secret": os.getenv("FEISHU_APP_SECRET"),
            },
            timeout=30,
        ).json()

        if resp.get("code") != 0:
            raise RuntimeError(f"App token failed: {resp}")

        return resp.get("tenant_access_token")


# Singleton instance
_oauth = None


def get_oauth() -> FeishuOAuth:
    global _oauth
    if _oauth is None:
        _oauth = FeishuOAuth()
    return _oauth


if __name__ == "__main__":
    oauth = get_oauth()
    url = oauth.get_authorization_url()
    print(f"Please visit this URL to authorize:")
    print(url)
    print("\nAfter authorization, you'll be redirected to localhost with a 'code' parameter.")
    print("Then call exchange_code_for_token(code) to get the user token.")
