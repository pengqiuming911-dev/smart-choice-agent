"""Agent - WikiAgent orchestrator implementing the 3 core operations"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

from src.core import GitManager, WikiIndex, PageParser, WikiRepo
from src.llm import get_llm_client, build_ingest_prompt, build_query_prompt, build_answer_prompt, build_lint_prompt


class WikiAgent:
    """
    LLM Wiki Agent - core orchestrator for the 3 operations:
    - ingest: LLM reads raw doc → creates/updates wiki pages
    - query: LLM reads index → finds pages → synthesizes answer
    - lint: LLM checks for orphaned pages, broken links, contradictions
    """

    def __init__(self, llm_client=None, repo_path: Path = None):
        from src.config import settings

        self.llm = llm_client or get_llm_client()
        repo_root = repo_path or settings.wiki_repo_path
        self.repo = WikiRepo(repo_root)
        self.repo.ensure_structure()
        self.git = GitManager(repo_root)
        self.index = WikiIndex(self.repo.index_md_path)

    def _system_prompt(self) -> str:
        """Load CLAUDE.md as system prompt"""
        if self.repo.claude_md_path.exists():
            return self.repo.claude_md_path.read_text(encoding="utf-8")
        return ""

    def _categorize_doc(self, path: Path) -> str:
        """Guess document category from path"""
        rel = str(path.relative_to(self.repo.raw_dir))
        if "meeting" in rel.lower() or "会议" in rel:
            return "meeting-notes"
        if "article" in rel.lower():
            return "articles"
        if "pdf" in rel.lower():
            return "pdfs"
        if "sheet" in rel.lower() or "表格" in rel or "table" in rel.lower():
            return "tables"
        return "articles"

    def _guess_page_type(self, category: str) -> str:
        if category == "meeting-notes":
            return "overview"
        if category in ("tables", "pdfs"):
            return "overview"
        return "entity"

    def _find_wiki_page(self, title: str) -> Optional[Path]:
        """Find a wiki page by title"""
        for page_path in self.repo.wiki_dir.rglob("*.md"):
            if page_path.name in ("index.md", "log.md"):
                continue
            content = page_path.read_text(encoding="utf-8")
            if PageParser.extract_title(content) == title:
                return page_path
        return None

    def _parse_json_response(self, text: str) -> Optional[dict]:
        """Extract JSON from LLM response"""
        text = text.strip()
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
        else:
            start, end = text.find("{"), text.rfind("}")
            if start != -1 and end != -1 and end > start:
                text = text[start : end + 1]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON: {text[:200]}")
            return None

    # ─── Ingest ────────────────────────────────────────────────────────────

    def ingest(self, doc_path: str) -> dict:
        """
        Ingest a raw document into the wiki.

        Steps (from ARCHITECTURE.md):
        1. Read raw document content
        2. Call LLM to extract entities/concepts and generate wiki pages
        3. Write pages to wiki/ (entities/, concepts/, overviews/)
        4. Update index.md
        5. Update log.md
        6. Git commit
        """
        raw_file = Path(doc_path) if Path(doc_path).is_absolute() else self.repo.raw_dir / doc_path

        if not raw_file.exists():
            raise FileNotFoundError(f"Raw document not found: {raw_file}")

        content = raw_file.read_text(encoding="utf-8")
        relative_path = str(raw_file.relative_to(self.repo.root))
        category = self._categorize_doc(raw_file)
        page_type = self._guess_page_type(category)
        system = self._system_prompt()

        prompt = build_ingest_prompt(relative_path, content, category, page_type)
        logger.info(f"Ingesting document: {raw_file.name}")

        raw_response = self.llm.generate(system=system, user_message=prompt, max_tokens=4000)
        pages_data = self._parse_json_response(raw_response)

        if not pages_data:
            logger.warning(f"Failed to parse LLM ingest response for {raw_file.name}")
            return {"success": False, "pages_created": 0, "pages_updated": 0}

        created = updated = 0
        for page in pages_data.get("pages", []):
            page_path = self.repo.wiki_dir / page["path"]
            is_new = not page_path.exists()
            page_path.parent.mkdir(parents=True, exist_ok=True)
            page_path.write_text(page["content"], encoding="utf-8")
            if is_new:
                created += 1
            else:
                updated += 1

        self.index.add_entries(pages_data.get("index_updates", []))
        self._append_log("ingest", relative_path, created, updated)
        self.git.commit(f"ingest: {raw_file.name} (+{created}/~{updated})")

        return {
            "success": True,
            "pages_created": created,
            "pages_updated": updated,
            "pages": pages_data.get("pages", []),
        }

    # ─── Query ────────────────────────────────────────────────────────────

    def query(self, question: str, user_id: str = None) -> dict:
        """
        Answer a user question using the wiki.

        Steps (from ARCHITECTURE.md):
        1. Read index.md to find relevant pages
        2. Call LLM to identify which pages are relevant
        3. Deep read those pages
        4. Synthesize answer
        5. Return structured response with sources
        """
        if not self.index.exists():
            return {
                "answer": "知识库尚未初始化，请先摄入文档。",
                "wiki_pages": [],
                "raw_sources": [],
                "confidence": "low",
            }

        system = self._system_prompt()
        index_content = self.index.read()

        # Phase 1: Find relevant pages
        find_prompt = build_query_prompt(index_content, question)
        relevant_titles_raw = self.llm.generate(system=system, user_message=find_prompt, max_tokens=500)
        relevant_titles = [t.strip() for t in relevant_titles_raw.split(",") if t.strip()]

        # Phase 2: Deep read relevant pages
        wiki_pages_content = []
        for title in relevant_titles:
            page_path = self._find_wiki_page(title)
            if page_path and page_path.exists():
                wiki_pages_content.append(
                    f"=== {title} ({page_path.name}) ===\n{page_path.read_text(encoding='utf-8')[:3000]}"
                )

        if not wiki_pages_content:
            return {
                "answer": f"我在知识库中没有找到与「{question}」相关的内容。",
                "wiki_pages": [],
                "raw_sources": [],
                "confidence": "low",
            }

        wiki_context = "\n\n".join(wiki_pages_content)

        # Phase 3: Synthesize answer
        answer_prompt = build_answer_prompt(wiki_context, question)
        raw_response = self.llm.generate(system=system, user_message=answer_prompt, max_tokens=2000)
        answer_data = self._parse_json_response(raw_response)

        wiki_pages = []
        for title in (answer_data.get("cited_pages", []) if answer_data else relevant_titles):
            page_path = self._find_wiki_page(title)
            if page_path:
                wiki_pages.append({"title": title, "path": str(page_path.relative_to(self.repo.wiki_dir))})

        if not answer_data:
            return {
                "answer": raw_response[:1000],
                "wiki_pages": wiki_pages,
                "raw_sources": [],
                "confidence": "medium",
            }

        # Extract raw sources from cited pages
        raw_sources = []
        for page in wiki_pages:
            page_path = self.repo.wiki_dir / page["path"]
            if page_path.exists():
                sources = PageParser.extract_sources(page_path.read_text(encoding="utf-8"))
                for s in sources:
                    raw_sources.append({"title": s, "path": s})

        return {
            "answer": answer_data.get("answer", ""),
            "wiki_pages": wiki_pages,
            "raw_sources": raw_sources,
            "confidence": answer_data.get("confidence", "medium"),
        }

    # ─── Lint ────────────────────────────────────────────────────────────

    def lint(self) -> dict:
        """
        Check wiki health: orphaned pages, broken links, contradictions.

        Returns LintReport with:
        - orphaned_pages: pages not linked from any other page
        - broken_links: [[links]] pointing to non-existent pages
        - contradictions: conflicting statements across pages
        - stale_pages: pages not updated in >3 months
        - suggestions: optimization suggestions
        """
        # Collect all wiki pages
        all_pages = {}
        for page_path in self.repo.wiki_dir.rglob("*.md"):
            if page_path.name in ("index.md", "log.md"):
                continue
            rel = page_path.relative_to(self.repo.wiki_dir)
            content = page_path.read_text(encoding="utf-8")
            all_pages[str(rel)] = {"content": content, "title": PageParser.extract_title(content) or ""}

        # Find all [[links]]
        all_links = set()
        link_source = {}
        for rel, data in all_pages.items():
            links = PageParser.extract_links(data["content"])
            for link in links:
                all_links.add(link)
                link_source.setdefault(link, []).append(rel)

        # Check orphaned pages
        all_titles = {d["title"] for d in all_pages.values()}
        orphaned = [d["title"] for d in all_pages.values() if d["title"] not in all_links]

        # Check broken links
        broken_links = []
        for link in all_links:
            if link not in all_titles:
                for source in link_source.get(link, []):
                    broken_links.append(f"{link} (from {source})")

        # LLM-powered deeper analysis
        all_content = "\n\n".join(f"=== {d['title']} ===\n{d['content'][:1000]}" for d in all_pages.values())
        lint_prompt = build_lint_prompt(all_content, orphaned, broken_links)
        raw_response = self.llm.generate(system=self._system_prompt(), user_message=lint_prompt, max_tokens=2000)
        lint_data = self._parse_json_response(raw_response) or {}

        return {
            "orphaned_pages": orphaned,
            "broken_links": broken_links,
            "contradictions": lint_data.get("contradictions", []),
            "stale_pages": lint_data.get("stale_pages", []),
            "suggestions": lint_data.get("suggestions", []),
        }

    # ─── Log ────────────────────────────────────────────────────────────

    def _append_log(self, operation: str, doc_path: str, created: int, updated: int):
        """Append to log.md"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        log_entry = f"- [{now}] {operation}: `{doc_path}` (+{created}/~{updated})\n"

        if self.repo.log_md_path.exists():
            content = self.repo.log_md_path.read_text(encoding="utf-8")
        else:
            content = "# 操作日志\n\n"

        self.repo.log_md_path.write_text(content + log_entry, encoding="utf-8")