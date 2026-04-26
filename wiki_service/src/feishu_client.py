"""Feishu API client for wiki sync - wiki/docx reading"""
import time
import httpx
from typing import Optional
from dataclasses import dataclass


BASE_URL = "https://open.feishu.cn/open-apis"


@dataclass
class WikiNode:
    node_token: str
    title: str
    obj_type: str  # docx / sheet / bitable / folder / wiki
    parent_token: Optional[str]
    has_child: bool


class FeishuClient:
    """Feishu API client for reading wiki and docx content"""

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token = None
        self._token_expires_at = 0

    def _get_token(self) -> str:
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

    # ─── Knowledge Space ────────────────────────────────────────────────

    def list_spaces(self) -> list[dict]:
        """列出所有知识空间"""
        resp = httpx.get(
            f"{BASE_URL}/wiki/v2/spaces",
            headers=self._headers(),
            timeout=30,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Failed to list wiki spaces: {data}")
        return data.get("data", {}).get("items", [])

    def list_folder_files(self, folder_token: str) -> list[dict]:
        """列出云文档文件夹中的所有文件（递归）"""
        files = []
        page_token = None

        while True:
            params = {"page_size": 500}
            if page_token:
                params["page_token"] = page_token

            resp = httpx.get(
                f"{BASE_URL}/drive/v1/files",
                headers=self._headers(),
                params={**params, "folder_token": folder_token},
                timeout=30,
            )
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Failed to list folder files: {data}")

            items = data.get("data", {}).get("files", [])
            for item in items:
                files.append({
                    "token": item.get("token", ""),
                    "name": item.get("name", ""),
                    "type": item.get("type", ""),  # docx / sheet / xlsx / etc
                })
                # 如果是文件夹，递归
                if item.get("type") == "folder":
                    sub_files = self.list_folder_files(item["token"])
                    files.extend(sub_files)

            has_more = data.get("data", {}).get("has_more", False)
            if not has_more:
                break
            page_token = data.get("data", {}).get("next_page_token")

        return files

    def list_wiki_nodes(self, space_id: str, parent_token: str = None) -> list[WikiNode]:
        """递归拉取知识空间节点树"""
        nodes = []
        page_token = None

        while True:
            params = {"page_size": 500}
            if parent_token:
                params["parent_node_token"] = parent_token
            if page_token:
                params["page_token"] = page_token

            resp = httpx.get(
                f"{BASE_URL}/wiki/v2/spaces/{space_id}/nodes",
                headers=self._headers(),
                params=params,
                timeout=30,
            )
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Failed to list wiki nodes: {data}")

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
                # 递归子节点
                if node.has_child:
                    child_nodes = self.list_wiki_nodes(space_id, node.node_token)
                    nodes.extend(child_nodes)

            has_more = data.get("data", {}).get("has_more", False)
            if not has_more:
                break
            page_token = data.get("data", {}).get("page_token")

        return nodes

    def get_wiki_space_id(self) -> str:
        """获取第一个知识空间 ID"""
        spaces = self.list_spaces()
        if not spaces:
            raise RuntimeError("No wiki spaces found")
        return spaces[0]["space_id"]

    # ─── Docx Content ────────────────────────────────────────────────────

    def get_docx_blocks(self, doc_token: str) -> list[dict]:
        """获取 docx 文档的 block 树"""
        blocks = []
        page_token = None

        while True:
            params = {"page_size": 500}
            if page_token:
                params["page_token"] = page_token

            resp = httpx.get(
                f"{BASE_URL}/docx/v1/documents/{doc_token}/blocks",
                headers=self._headers(),
                params=params,
                timeout=30,
            )
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Failed to get docx blocks: {data}")

            items = data.get("data", {}).get("items", [])
            blocks.extend(items)

            has_more = data.get("data", {}).get("has_more", False)
            if not has_more:
                break
            page_token = data.get("data", {}).get("next_page_token")

        return blocks

    def blocks_to_markdown(self, blocks: list[dict]) -> str:
        """将飞书 block 树转换为 markdown"""

        def extract_text(block: dict) -> str:
            """从 block 中提取纯文本"""
            text = ""
            block_type = block.get("block_type", 0)

            # 文本段落
            if block_type in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25):
                elements = block.get(block.get("block_type_map_key", ""), {}).get("elements", [])
                for el in elements:
                    if el.get("type") == "text_run":
                        text += el.get("text_run", {}).get("content", "")
            # 列表项
            elif block_type == 3:  # bullet
                elements = block.get("bullet", {}).get("elements", [])
                for el in elements:
                    if el.get("type") == "text_run":
                        text += el.get("text_run", {}).get("content", "")
            elif block_type == 4:  # ordered
                elements = block.get("ordered", {}).get("elements", [])
                for el in elements:
                    if el.get("type") == "text_run":
                        text += el.get("text_run", {}).get("content", "")

            return text

        lines = []

        for block in blocks:
            block_type = block.get("block_type", 0)

            if block_type == 2:  # 文本段落
                text = extract_text(block).strip()
                if text:
                    lines.append(text)

            elif block_type == 3:  # bullet list
                text = extract_text(block).strip()
                if text:
                    lines.append(f"- {text}")

            elif block_type == 4:  # ordered list
                text = extract_text(block).strip()
                if text:
                    lines.append(f"1. {text}")

            elif block_type == 14:  # heading 1
                text = extract_text(block).strip()
                if text:
                    lines.append(f"# {text}")

            elif block_type == 15:  # heading 2
                text = extract_text(block).strip()
                if text:
                    lines.append(f"## {text}")

            elif block_type == 16:  # heading 3
                text = extract_text(block).strip()
                if text:
                    lines.append(f"### {text}")

            elif block_type == 22:  # code block
                lines.append("```")
                elements = block.get("code", {}).get("elements", [])
                for el in elements:
                    if el.get("type") == "text_run":
                        lines.append(el.get("text_run", {}).get("content", ""))
                lines.append("```")

            elif block_type == 27:  # quote
                text = extract_text(block).strip()
                if text:
                    lines.append(f"> {text}")

            elif block_type == 35:  # table
                lines.append("[表格内容，请参考原文档]")

        return "\n".join(lines)

    def get_docx_markdown(self, doc_token: str) -> str:
        """获取 docx 文档并转换为 markdown"""
        blocks = self.get_docx_blocks(doc_token)
        return self.blocks_to_markdown(blocks)

    # ─── Spreadsheet ──────────────────────────────────────────────────────

    def get_sheet_values(self, spreadsheet_token: str, range_str: str) -> list[list]:
        """读取 spreadsheet 指定范围的值"""
        resp = httpx.get(
            f"{BASE_URL}/sheets/v2/spreadsheets/{spreadsheet_token}/values/{range_str}",
            headers=self._headers(),
            timeout=30,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Failed to get sheet values: {data}")
        return data.get("data", {}).get("valueRange", {}).get("values", [])

    def sheet_to_markdown(self, spreadsheet_token: str, sheet_id: str) -> str:
        """将 spreadsheet sheet 转换为 markdown 表格"""
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
