"""飞书消息发送模块"""
import json
import time
import httpx
from rag_service.config import settings


class FeishuSender:
    """飞书消息发送器"""

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self):
        self._token = None
        self._token_expires_at = 0

    def _get_token(self) -> str:
        """获取 tenant_access_token，自动刷新"""
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        resp = httpx.post(
            f"{self.BASE_URL}/auth/v3/tenant_access_token/internal",
            json={
                "app_id": settings.feishu_app_id,
                "app_secret": settings.feishu_app_secret,
            },
            timeout=30,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Failed to get token: {data}")

        self._token = data["tenant_access_token"]
        self._token_expires_at = time.time() + 7200
        return self._token

    def send_message(self, open_id: str, content: str, msg_type: str = "text") -> bool:
        """
        发送消息给指定用户

        Args:
            open_id: 用户的 open_id
            content: 消息内容
            msg_type: 消息类型，text 或 interactive

        Returns:
            是否发送成功
        """
        token = self._get_token()

        payload = {
            "receive_id": open_id,
            "msg_type": msg_type,
            "content": json.dumps({"text": content}) if msg_type == "text" else content,
        }

        resp = httpx.post(
            f"{self.BASE_URL}/im/v1/messages",
            headers={"Authorization": f"Bearer {token}"},
            params={"receive_id_type": "open_id"},
            json=payload,
            timeout=30,
        )

        data = resp.json()
        if data.get("code") != 0:
            print(f"[ERROR] Failed to send message: {data}")
            return False

        return True

    def send_card(self, open_id: str, card_content: dict) -> bool:
        """
        发送卡片消息

        Args:
            open_id: 用户的 open_id
            card_content: 卡片内容 dict

        Returns:
            是否发送成功
        """
        return self.send_message(open_id, card_content, msg_type="interactive")


# Singleton
_sender = None


def get_sender() -> FeishuSender:
    """获取发送器单例"""
    global _sender
    if _sender is None:
        _sender = FeishuSender()
    return _sender
