"""Feishu Bitable (多维表格) client for querying product data"""
import os
import json
import httpx
from typing import List, Dict, Optional
from src.config import settings


class FeishuBitableClient:
    """Query Feishu Bitable records via Feishu Open API"""

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token = None
        self._token_expires_at = 0

    def _get_token(self) -> str:
        """Get tenant access token"""
        import time

        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        resp = httpx.post(
            f"{self.BASE_URL}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=30,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Failed to get Feishu token: {data}")

        self._token = data["tenant_access_token"]
        self._token_expires_at = time.time() + 7200
        return self._token

    def list_records(
        self,
        app_token: str,
        table_id: str,
        filter_str: str = None,
        sort_str: str = None,
        page_size: int = 100,
    ) -> List[Dict]:
        """
        获取多维表格中的记录

        Args:
            app_token: 多维表格的 app token（如 bascnxxxxxx）
            table_id: 数据表 ID（如 tblxxxxxx）
            filter_str: 过滤条件
            sort_str: 排序条件
            page_size: 每页大小，最大 500

        Returns:
            记录列表，每条记录是一个 dict
        """
        token = self._get_token()
        headers = {"Authorization": f"Bearer {token}"}

        all_records = []
        page_token = None

        while True:
            params = {"page_size": page_size}
            if filter_str:
                params["filter"] = filter_str
            if sort_str:
                params["sort"] = sort_str
            if page_token:
                params["page_token"] = page_token

            resp = httpx.get(
                f"{self.BASE_URL}/bitable/v1/apps/{app_token}/tables/{table_id}/records",
                headers=headers,
                params=params,
                timeout=30,
            )
            data = resp.json()

            if data.get("code") != 0:
                print(f"[ERROR] Failed to query bitable: {data}")
                break

            items = data.get("data", {}).get("items", [])
            all_records.extend(items)

            has_more = data.get("data", {}).get("has_more", False)
            if not has_more:
                break

            page_token = data.get("data", {}).get("page_token")
            if not page_token:
                break

        return all_records

    def get_table_fields(self, app_token: str, table_id: str) -> List[Dict]:
        """获取数据表的字段列表"""
        token = self._get_token()
        headers = {"Authorization": f"Bearer {token}"}

        resp = httpx.get(
            f"{self.BASE_URL}/bitable/v1/apps/{app_token}/tables/{table_id}/fields",
            headers=headers,
            timeout=30,
        )
        data = resp.json()

        if data.get("code") != 0:
            print(f"[ERROR] Failed to get fields: {data}")
            return []

        return data.get("data", {}).get("items", [])


# Singleton
_client = None


def get_bitable_client() -> FeishuBitableClient:
    global _client
    if _client is None:
        _client = FeishuBitableClient(
            app_id=settings.feishu_app_id,
            app_secret=settings.feishu_app_secret,
        )
    return _client


def query_product_table() -> List[Dict]:
    """
    查询「产品表-同步」数据

    Returns:
        产品记录列表，每条记录包含所有字段
    """
    if not settings.bitable_app_id or not settings.bitable_table_id:
        print("[WARN] BITABLE_APP_ID or BITABLE_TABLE_ID not configured")
        return []

    client = get_bitable_client()
    records = client.list_records(
        app_token=settings.bitable_app_id,
        table_id=settings.bitable_table_id,
    )

    # 提取 fields
    products = []
    for record in records:
        fields = record.get("fields", {})
        products.append(fields)

    return products


def get_field_names() -> List[str]:
    """获取产品表的字段名列表（用于调试和字段映射）"""
    if not settings.bitable_app_id or not settings.bitable_table_id:
        return []

    client = get_bitable_client()
    fields = client.get_table_fields(
        app_token=settings.bitable_app_id,
        table_id=settings.bitable_table_id,
    )
    return [f.get("field_name", "") for f in fields]


def build_index_code_map() -> Dict[str, str]:
    """
    从产品表的「代码」字段中解析并构建指数代码映射

    代码格式如：沪深300（000300.SH）→ 提取出 沪深300 → 000300

    Returns:
        {"上证指数": "000001", "沪深300": "000300", ...}
    """
    import re

    products = query_product_table()
    code_map = {}
    seen_codes = set()

    for p in products:
        code_field = p.get("代码", "")
        if not code_field:
            continue
        # 匹配 "指数名（代码.SH）" 或 "指数名（代码.SZ）" 等格式
        m = re.match(r"(.+?)（(\d+)\.(?:SH|SZ)）", str(code_field))
        if m:
            name, num = m.group(1).strip(), m.group(2)
            if num not in seen_codes:
                code_map[name] = num
                seen_codes.add(num)

    return code_map
