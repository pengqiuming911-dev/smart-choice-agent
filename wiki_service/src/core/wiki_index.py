"""Core domain - wiki index management"""
import re
from pathlib import Path
from typing import Optional


class WikiIndex:
    """Manages wiki/index.md - the global index of all wiki pages"""

    def __init__(self, index_path: Path):
        self.index_path = index_path

    def exists(self) -> bool:
        return self.index_path.exists()

    def read(self) -> str:
        if not self.exists():
            return ""
        return self.index_path.read_text(encoding="utf-8")

    def write(self, content: str):
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(content, encoding="utf-8")

    def add_entries(self, entries: list[str]):
        """Append new entries to index"""
        content = self.read()
        if not content:
            content = "# 知识库索引\n\n"

        new_entries_md = "\n".join(f"- {e}" for e in entries)
        content += f"\n## 新增页面\n{new_entries_md}\n"
        self.write(content)

    @staticmethod
    def extract_title(content: str) -> Optional[str]:
        """Extract title from frontmatter or first heading"""
        m = re.search(r"^title:\s*(.+)$", content, re.MULTILINE)
        if m:
            return m.group(1).strip()
        m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if m:
            return m.group(1).strip()
        return None

    @staticmethod
    def extract_page_type(content: str) -> str:
        """Extract page type from frontmatter"""
        m = re.search(r"^type:\s*(.+)$", content, re.MULTILINE)
        if m:
            return m.group(1).strip()
        return "unknown"

    @staticmethod
    def extract_access(content: str) -> str:
        """Extract access level from frontmatter"""
        m = re.search(r"^access:\s*(.+)$", content, re.MULTILINE)
        if m:
            return m.group(1).strip()
        return "public"