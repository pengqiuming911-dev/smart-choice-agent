"""Feishu message sender with token auto-refresh"""
import json
import time
import httpx
from src.config import settings


class FeishuClient:
    """Shared Feishu API client with token management"""

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token = None
        self._token_expires_at = 0

    def _get_token(self) -> str:
        """Get or refresh tenant access token"""
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        resp = httpx.post(
            f"{self.BASE_URL}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Failed to get Feishu token: code={data.get('code')}, msg={data.get('msg')}")

        self._token = data["tenant_access_token"]
        self._token_expires_at = time.time() + 7200
        return self._token

    def _post(self, path: str, data: dict, params: dict = None) -> dict:
        """POST to Feishu API with auto token"""
        token = self._get_token()
        resp = httpx.post(
            f"{self.BASE_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            json=data,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") != 0:
            raise RuntimeError(f"Feishu API error: code={result.get('code')}, msg={result.get('msg')}")
        return result

    def send_message(self, open_id: str, content: str, msg_type: str = "text") -> bool:
        """Send message to user"""
        try:
            payload = {
                "receive_id": open_id,
                "msg_type": msg_type,
                "content": json.dumps({"text": content}) if msg_type == "text" else content,
            }
            self._post(
                "/im/v1/messages",
                payload,
                params={"receive_id_type": "open_id"},
            )
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send message: {e}")
            return False

    def send_text(self, open_id: str, text: str) -> bool:
        """Send plain text message"""
        return self.send_message(open_id, text, msg_type="text")

    def send_card(self, open_id: str, card: dict) -> bool:
        """Send interactive card"""
        return self.send_message(open_id, card, msg_type="interactive")


# Singleton
_client = None


def get_feishu_client() -> FeishuClient:
    global _client
    if _client is None:
        _client = FeishuClient(
            app_id=settings.feishu_app_id,
            app_secret=settings.feishu_app_secret,
        )
    return _client


# Backward compatibility
def get_sender():
    return get_feishu_client()
