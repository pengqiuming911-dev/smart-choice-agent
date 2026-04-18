"""Feishu API client for document sync"""
import os
import time
import httpx
from typing import Optional


class FeishuClient:
    """Feishu API client with automatic token refresh"""

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id: str = None, app_secret: str = None):
        self.app_id = app_id or os.getenv("FEISHU_APP_ID")
        self.app_secret = app_secret or os.getenv("FEISHU_APP_SECRET")
        self._token = None
        self._token_expires_at = 0

    def get_token(self) -> str:
        """Get tenant access token, auto-refresh if expired"""
        # Add 60s buffer before expiry
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        resp = httpx.post(
            f"{self.BASE_URL}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=30,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Failed to get token: {data}")

        self._token = data["tenant_access_token"]
        # Default 2 hours, subtract buffer
        self._token_expires_at = time.time() + 7200
        return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.get_token()}"}

    def _get(self, path: str, **kwargs) -> dict:
        """GET request with auth"""
        url = f"{self.BASE_URL}{path}"
        resp = httpx.get(url, headers=self._headers(), timeout=30, **kwargs)
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"API error {path}: {data}")
        return data.get("data", {})

    def _post(self, path: str, **kwargs) -> dict:
        """POST request with auth"""
        url = f"{self.BASE_URL}{path}"
        resp = httpx.post(url, headers=self._headers(), timeout=30, **kwargs)
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"API error {path}: {data}")
        return data.get("data", {})

    # === Wiki APIs ===

    def list_wiki_spaces(self) -> list:
        """List all wiki spaces"""
        spaces = []
        page_token = None

        while True:
            params = {"page_size": 50}
            if page_token:
                params["page_token"] = page_token

            data = self._get("/wiki/v2/spaces", params=params)
            items = data.get("items", [])
            spaces.extend(items)

            page_token = data.get("page_token")
            if not page_token or not items:
                break

        return spaces

    def walk_wiki_tree(self, space_id: str, parent_token: str = None) -> list:
        """Walk wiki node tree, return all nodes under parent"""
        nodes = []
        page_token = None

        while True:
            params = {"page_size": 100}
            if page_token:
                params["page_token"] = page_token

            if parent_token:
                path = f"/wiki/v2/spaces/{space_id}/nodes"
                params["parent_node_token"] = parent_token
            else:
                path = f"/wiki/v2/spaces/{space_id}/nodes"

            data = self._get(path, params=params)
            items = data.get("items", [])
            nodes.extend(items)

            page_token = data.get("page_token")
            if not page_token or not items:
                break

        return nodes

    def get_wiki_node(self, node_token: str) -> dict:
        """Get wiki node info"""
        return self._get(f"/wiki/v2/spaces/{node_token}/nodes/{node_token}")

    # === Docx APIs ===

    def get_docx_blocks(self, document_id: str, page_token: str = None) -> dict:
        """Get docx blocks with pagination"""
        path = f"/docx/v1/documents/{document_id}/blocks"
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token

        return self._get(path, params=params)

    def get_docx_raw_content(self, document_id: str) -> str:
        """Get docx raw text content (fallback)"""
        data = self._get(f"/docx/v1/documents/{document_id}/raw_content")
        return data.get("content", "")

    # === Drive APIs (云盘/共享文件夹) ===

    def get_document_info(self, document_id: str) -> dict:
        """Get document metadata"""
        return self._get(f"/drive/v1/files/{document_id}/metadata")

    def list_folder_files(self, folder_token: str = None, page_token: str = None) -> dict:
        """
        List files in a folder or My Drive root.

        Args:
            folder_token: Folder token (from folder object)
            page_token: Pagination token

        Returns:
            {"items": [...], "page_token": ...}
        """
        if folder_token:
            # List files in specific folder
            path = f"/drive/v1/files/{folder_token}/children"
        else:
            # List My Drive root files
            path = "/drive/v1/files"

        params = {"page_size": 100}
        if page_token:
            params["page_token"] = page_token

        return self._get(path, params=params)

    def list_all_folder_files(self, folder_token: str = None) -> list:
        """Recursively list all files in a folder"""
        all_files = []
        page_token = None

        while True:
            data = self.list_folder_files(folder_token, page_token)
            items = data.get("files", []) or data.get("items", [])
            all_files.extend(items)

            page_token = data.get("page_token")
            if not page_token:
                break

        return all_files

    def batch_get_file_metadata(self, file_tokens: list) -> list:
        """Batch get metadata for multiple files"""
        if not file_tokens:
            return []

        data = self._post(
            "/drive/v1/metas/batch_query",
            json={"request_docs": [{"doc_token": t} for t in file_tokens]}
        )
        return data.get("metas", [])

    def get_document_permissions(self, document_id: str) -> list:
        """Get document permission members"""
        members = []
        page_token = None

        while True:
            params = {"page_size": 100}
            if page_token:
                params["page_token"] = page_token

            data = self._get(f"/drive/v1/permissions/{document_id}/members", params=params)
            items = data.get("items", [])
            members.extend(items)

            page_token = data.get("page_token")
            if not page_token or not items:
                break

        return members


# Singleton instance
_client = None


def get_client() -> FeishuClient:
    """Get or create Feishu client singleton"""
    global _client
    if _client is None:
        _client = FeishuClient()
    return _client
