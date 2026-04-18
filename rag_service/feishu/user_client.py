"""Feishu client using user_access_token for personal file access"""
import os
import time
import httpx
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://open.feishu.cn/open-apis"


class FeishuUserClient:
    """
    Feishu API client using user_access_token.
    This allows access to files the user has permission to view.
    """

    def __init__(self, user_access_token: str = None):
        self.user_access_token = user_access_token
        self._token_refresh_time = 0
        self._refresh_token = None

    def set_token(self, access_token: str, refresh_token: str = None, expires_in: int = 7200):
        """Set user access token and refresh token"""
        self.user_access_token = access_token
        self._refresh_token = refresh_token
        # Token typically expires in 2 hours (7200 seconds)
        self._token_refresh_time = time.time() + expires_in - 300  # Refresh 5 min before expiry

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.user_access_token}"}

    def _get(self, path: str, **kwargs) -> dict:
        url = f"{BASE_URL}{path}"
        resp = httpx.get(url, headers=self._headers(), timeout=30, **kwargs)
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"API error {path}: {data}")
        return data.get("data", {})

    def _post(self, path: str, **kwargs) -> dict:
        url = f"{BASE_URL}{path}"
        resp = httpx.post(url, headers=self._headers(), timeout=30, **kwargs)
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"API error {path}: {data}")
        return data.get("data", {})

    # === Drive APIs ===

    def list_my_drive_files(self, folder_token: str = None, page_token: str = None) -> dict:
        """
        List files in user's personal drive or specified folder.

        Args:
            folder_token: Folder token. If None, lists My Drive root.
            page_token: Pagination token

        Returns:
            {"files": [...], "page_token": ...}
        """
        params = {"page_size": 100}
        if page_token:
            params["page_token"] = page_token

        if folder_token:
            # Use drive/explorer API for folder listing (works for wiki folders)
            url = f"{BASE_URL}/drive/explorer/v2/folder/{folder_token}/children"
            resp = httpx.get(url, headers=self._headers(), timeout=30, params=params)
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"API error listing folder {folder_token}: {data}")
            # Convert explorer API response format to standard format
            children = data.get("data", {}).get("children", {})
            files = []
            for item in children.values():
                files.append({
                    "token": item.get("token"),
                    "name": item.get("name"),
                    "type": item.get("type"),
                })
            return {"files": files}
        else:
            path = "/drive/v1/files"
            return self._get(path, params=params)

    def list_all_files_recursive(self, folder_token: str = None) -> List[dict]:
        """
        Recursively list all files in folder (including subfolders).

        Returns:
            List of all file dicts with type, token, name
        """
        all_files = []
        files_to_process = [{"token": folder_token, "type": "folder"}]
        processed_folders = set()

        while files_to_process:
            current = files_to_process.pop(0)
            token = current.get("token")
            ftype = current.get("type")

            if ftype == "folder" and token:
                if token in processed_folders:
                    continue
                processed_folders.add(token)

                page_token = None
                while True:
                    data = self.list_my_drive_files(token, page_token)
                    files = data.get("files", [])
                    for f in files:
                        all_files.append(f)
                        if f.get("type") == "folder":
                            files_to_process.append({
                                "token": f.get("token"),
                                "type": "folder"
                            })

                    page_token = data.get("page_token")
                    if not page_token:
                        break
                    time.sleep(0.1)  # Rate limit protection

        return all_files

    def get_file_info(self, file_token: str) -> dict:
        """Get file metadata"""
        return self._get(f"/drive/v1/files/{file_token}/metadata")

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
            if not page_token:
                break

        return members

    # === Docx APIs ===

    def get_docx_blocks(self, document_id: str, page_token: str = None) -> dict:
        """Get docx blocks with pagination"""
        path = f"/docx/v1/documents/{document_id}/blocks"
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token

        return self._get(path, params=params)

    def get_docx_raw_content(self, document_id: str) -> str:
        """Get docx raw text content"""
        data = self._get(f"/docx/v1/documents/{document_id}/raw_content")
        return data.get("content", "")


# Singleton instance
_user_client = None


def get_user_client() -> FeishuUserClient:
    global _user_client
    if _user_client is None:
        _user_client = FeishuUserClient()
    return _user_client


def set_user_token(access_token: str, refresh_token: str = None):
    """Set user token for subsequent API calls"""
    client = get_user_client()
    client.set_token(access_token, refresh_token)
