"""Core domain - wiki page parsing utilities"""
import re
from pathlib import Path
from typing import Optional


class PageParser:
    """Parse and validate wiki pages"""

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
    def extract_frontmatter(content: str) -> dict:
        """Parse frontmatter into dict"""
        fm_match = re.match(r"^---\n(.+?)\n---", content, re.DOTALL)
        if not fm_match:
            return {}

        result = {}
        for line in fm_match.group(1).split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                result[key.strip()] = val.strip()
        return result

    @staticmethod
    def extract_links(content: str) -> list[str]:
        """Extract all [[wiki links]] from content"""
        return re.findall(r"\[\[([^\]]+)\]\]", content)

    @staticmethod
    def extract_sources(content: str) -> list[str]:
        """Extract sources from frontmatter"""
        fm = PageParser.extract_frontmatter(content)
        sources_str = fm.get("sources", "")
        if not sources_str:
            return []
        # Handle [source1, source2] format
        sources_str = sources_str.strip("[]")
        return [s.strip().strip("'\"") for s in sources_str.split(",") if s.strip()]

    @staticmethod
    def build_frontmatter(
        title: str,
        page_type: str = "entity",
        access: str = "public",
        sources: list[str] = None,
        last_updated: str = None,
    ) -> str:
        """Build frontmatter string"""
        fm = [
            f"title: {title}",
            f"type: {page_type}",
            f"access: {access}",
        ]
        if sources:
            fm.append(f"sources: [{', '.join(sources)}]")
        if last_updated:
            fm.append(f"last_updated: {last_updated}")
        return "---\n" + "\n".join(fm) + "\n---\n"

    @staticmethod
    def is_valid_page_path(path: Path, valid_types: list[str] = None) -> bool:
        """Check if path is a valid wiki page path"""
        if path.name in ("index.md", "log.md"):
            return False
        if valid_types:
            return any(f"{t}/" in str(path) or str(path).startswith(f"{t}/") for t in valid_types)
        return path.suffix == ".md"