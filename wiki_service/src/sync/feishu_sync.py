"""
Sync - Feishu document synchronization

Directory structure (from ARCHITECTURE.md section 8):

/opt/wiki/
├── sync/
│   ├── feishu_client.py       # 飞书 API 封装
│   ├── differ.py              # 变更检测
│   ├── parser.py              # docx → markdown 转换
│   └── sync_main.py           # 主同步脚本
├── tasks/
│   ├── celery_app.py
│   ├── ingest.py              # ingest 任务
│   └── lint.py                # lint 任务
├── webhook/
│   └── feishu_webhook.py      # 飞书事件接收(Phase 3)
├── wiki-repo/                 # Git 仓库
│   ├── raw/
│   ├── wiki/
│   └── CLAUDE.md
├── logs/
└── .env                       # 凭证(不提交 Git)
"""

import hashlib
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


BASE_URL = "https://open.feishu.cn/open-apis"


class WikiNode:
    """Knowledge space node"""
    def __init__(self, node_token: str, title: str, obj_type: str, parent_token: Optional[str], has_child: bool):
        self.node_token = node_token
        self.title = title
        self.obj_type = obj_type
        self.parent_token = parent_token
        self.has_child = has_child


class FeishuClient:
    """
    Feishu API client for wiki/docx/sheet reading.
    Implements token caching and recursive node traversal.
    """

    def __init__(self, app_id: str, app_secret: str):
        if not HAS_HTTPX:
            raise RuntimeError("httpx package not installed. Run: pip install httpx")
        self.app_id = app_id
        self.app_secret = app_secret
        self._token = None
        self._token_expires_at = 0

    def _get_token(self) -> str:
        """Get tenant access token with caching (refresh 60s before expiry)"""
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        resp = httpx.post(
            f"{BASE_URL}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=30,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Failed to get Feishu token: {data}")

        self._token = data["tenant_access_token"]
        self._token_expires_at = time.time() + 7200
        return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def _api_get(self, path: str, params: dict = None) -> dict:
        """Make authenticated GET request"""
        resp = httpx.get(
            f"{BASE_URL}{path}",
            headers=self._headers(),
            params=params,
            timeout=30,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"API error {path}: {data}")
        return data

    # ─── Knowledge Space ─────────────────────────────────────────────────

    def list_spaces(self) -> list[dict]:
        """List all wiki spaces"""
        return self._api_get("/wiki/v2/spaces").get("data", {}).get("items", [])

    def get_wiki_space_id(self) -> str:
        """Get the first wiki space ID"""
        spaces = self.list_spaces()
        if not spaces:
            raise RuntimeError("No wiki spaces found")
        return spaces[0]["space_id"]

    def list_wiki_nodes(self, space_id: str, parent_token: str = None) -> list[WikiNode]:
        """
        Recursively list all wiki nodes in a space.
        This is needed because Feishu wiki is a tree structure.
        """
        nodes = []
        page_token = None

        while True:
            params = {"page_size": 500, "space_id": space_id}
            if parent_token:
                params["parent_node_token"] = parent_token
            if page_token:
                params["page_token"] = page_token

            data = self._api_get("/wiki/v2/spaces/nodes", params)
            items = data.get("data", {}).get("items", [])

            for item in items:
                node = WikiNode(
                    node_token=item.get("node_token", ""),
                    title=item.get("title", ""),
                    obj_type=item.get("obj_type", ""),
                    parent_token=parent_token,
                    has_child=item.get("has_child", False),
                )
                nodes.append(node)

                if node.has_child:
                    nodes.extend(self.list_wiki_nodes(space_id, node.node_token))

            has_more = data.get("data", {}).get("has_more", False)
            if not has_more:
                break
            page_token = data.get("data", {}).get("page_token")

        return nodes

    # ─── Docx Content ────────────────────────────────────────────────────

    def get_docx_blocks(self, doc_token: str) -> list[dict]:
        """Get docx document block tree with pagination"""
        blocks = []
        page_token = None

        while True:
            params = {"page_size": 500}
            if page_token:
                params["page_token"] = page_token

            data = self._api_get(f"/docx/v1/documents/{doc_token}/blocks", params)
            blocks.extend(data.get("data", {}).get("items", []))

            has_more = data.get("data", {}).get("has_more", False)
            if not has_more:
                break
            page_token = data.get("data", {}).get("next_page_token")

        return blocks

    def blocks_to_markdown(self, blocks: list[dict]) -> str:
        """Convert Feishu block tree to markdown text"""
        lines = []

        def extract_text(block: dict) -> str:
            """Extract plain text from block elements"""
            block_type = block.get("block_type", 0)
            # Handle different block types with their element keys
            type_map = {
                2: "text", 3: "heading1", 4: "heading2", 5: "heading3",
                6: "heading4", 7: "heading5", 8: "heading6",
                10: "bullet", 12: "ordered",
            }
            key = block.get("block_type_map_key", "")
            if not key and block_type in type_map:
                key = type_map.get(block_type, "text")

            elements = block.get(key, {}).get("elements", [])
            return "".join(
                el.get("text_run", {}).get("content", "")
                for el in elements
                if el.get("type") == "text_run"
            )

        for block in blocks:
            block_type = block.get("block_type", 0)

            if block_type == 2:  # paragraph
                text = extract_text(block).strip()
                if text:
                    lines.append(text)

            elif block_type == 3:  # heading1
                text = extract_text(block).strip()
                if text:
                    lines.append(f"# {text}")

            elif block_type == 4:  # heading2
                text = extract_text(block).strip()
                if text:
                    lines.append(f"## {text}")

            elif block_type == 5:  # heading3
                text = extract_text(block).strip()
                if text:
                    lines.append(f"### {text}")

            elif block_type == 10:  # bullet list
                text = extract_text(block).strip()
                if text:
                    lines.append(f"- {text}")

            elif block_type == 12:  # ordered list
                text = extract_text(block).strip()
                if text:
                    lines.append(f"1. {text}")

            elif block_type == 14:  # code block
                lines.append("```")
                elements = block.get("code", {}).get("elements", [])
                for el in elements:
                    if el.get("type") == "text_run":
                        lines.append(el.get("text_run", {}).get("content", ""))
                lines.append("```")

            elif block_type == 22:  # quote
                text = extract_text(block).strip()
                if text:
                    lines.append(f"> {text}")

            elif block_type == 35:  # table
                lines.append("[表格内容，请参考原文档]")

        return "\n".join(lines)

    def get_docx_markdown(self, doc_token: str) -> str:
        """Get docx content converted to markdown"""
        blocks = self.get_docx_blocks(doc_token)
        return self.blocks_to_markdown(blocks)

    # ─── Spreadsheet ────────────────────────────────────────────────────

    def get_sheet_values(self, spreadsheet_token: str, range_str: str) -> list[list]:
        """Read spreadsheet values from a range"""
        data = self._api_get(
            f"/sheets/v2/spreadsheets/{spreadsheet_token}/values/{range_str}"
        )
        return data.get("data", {}).get("valueRange", {}).get("values", [])

    def sheet_to_markdown(self, spreadsheet_token: str, sheet_id: str) -> str:
        """Convert spreadsheet sheet to markdown table"""
        try:
            values = self.get_sheet_values(spreadsheet_token, f"{sheet_id}!A1:Z100")
            if not values:
                return ""

            lines = []
            for row in values:
                cells = [str(c) if c is not None else "" for c in row]
                lines.append("| " + " | ".join(cells) + " |")
                if len(lines) == 1:
                    lines.append("|" + "|".join([" --- " for _ in row]) + "|")
            return "\n".join(lines)
        except Exception as e:
            return f"[表格读取失败: {e}]"


class FeishuSyncer:
    """
    Sync manager for Feishu wiki to raw documents.
    Handles document fetching, hash-based change detection, and raw storage.
    """

    def __init__(self, client: FeishuClient, raw_dir: Path):
        self.client = client
        self.raw_dir = raw_dir

    def sync_doc(self, doc_token: str, title: str, doc_type: str = "docx") -> dict:
        """
        Sync a single Feishu document to raw directory.

        Args:
            doc_token: Feishu document token
            title: Document title (for filename)
            doc_type: "docx" or "sheet"

        Returns:
            dict with success status, path, and content hash
        """
        try:
            if doc_type == "sheet":
                content = self.client.sheet_to_markdown(doc_token, "Sheet1")
            else:
                content = self.client.get_docx_markdown(doc_token)

            safe_name = re.sub(r"[^\w\-\u4e00-\u9fff]", "_", title)
            subdir = "articles"
            if doc_type == "sheet":
                subdir = "tables"

            raw_path = self.raw_dir / subdir / f"{safe_name}.md"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(content, encoding="utf-8")

            content_hash = self.compute_hash(content)
            logger.info(f"Synced: {title} -> {raw_path}")

            return {
                "success": True,
                "path": str(raw_path),
                "hash": content_hash,
                "title": title,
            }
        except Exception as e:
            logger.error(f"Failed to sync doc {doc_token}: {e}")
            return {"success": False, "error": str(e)}

    def compute_hash(self, content: str) -> str:
        """Compute MD5 hash of content for change detection"""
        return hashlib.md5(content.encode()).hexdigest()


def build_sync_stats(new: int, updated: int, archived: int, failed: int) -> dict:
    """Build sync statistics report"""
    return {
        "timestamp": datetime.now().isoformat(),
        "new": new,
        "updated": updated,
        "archived": archived,
        "failed": failed,
    }