"""Wiki Agent - core orchestrator for ingest/query/lint operations"""
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional
from loguru import logger

from src.config import settings
from src.claude_client import get_claude_client, ClaudeClient


class WikiAgent:
    """LLM Wiki Agent - manages the wiki via Claude"""

    def __init__(self, client: Optional[ClaudeClient] = None):
        self.client = client or get_claude_client()
        self.repo_path = settings.wiki_repo_path
        self.claude_md = settings.claude_md_path
        self.wiki_dir = settings.wiki_dir
        self.raw_dir = settings.raw_dir
        self.index_md = settings.index_md_path
        self.log_md = settings.log_md_path

    # ─── System prompt ────────────────────────────────────────────────────

    def _get_system_prompt(self) -> str:
        """Load CLAUDE.md as system prompt"""
        if self.claude_md.exists():
            return self.claude_md.read_text(encoding="utf-8")
        return ""

    # ─── Git helpers ──────────────────────────────────────────────────────

    def _git_commit(self, message: str):
        """Auto git commit after wiki modification"""
        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            logger.info(f"Git commit: {message}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git commit failed (may be no changes): {e.stderr}")

    def _init_git_repo(self):
        """Initialize git repo if not exists"""
        git_dir = self.repo_path / ".git"
        if not git_dir.exists():
            subprocess.run(
                ["git", "init"],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "Initial wiki commit"],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            logger.info("Git repo initialized")

    # ─── Ingest ───────────────────────────────────────────────────────────

    def ingest(self, doc_path: str) -> dict:
        """
        Ingest a raw document into the wiki.

        Steps:
        1. Read raw document content
        2. Call LLM to extract entities/concepts and generate wiki pages
        3. Write pages to wiki/
        4. Update index.md
        5. Update log.md
        6. Git commit

        Args:
            doc_path: Path to raw document (relative to raw_dir or absolute)

        Returns:
            dict with success status and pages created/updated
        """
        self._init_git_repo()

        # Resolve path
        if Path(doc_path).is_absolute():
            raw_file = Path(doc_path)
        else:
            raw_file = self.raw_dir / doc_path

        if not raw_file.exists():
            raise FileNotFoundError(f"Raw document not found: {raw_file}")

        content = raw_file.read_text(encoding="utf-8")
        relative_path = str(raw_file.relative_to(self.repo_path))
        system_prompt = self._get_system_prompt()

        # Determine doc type and category
        category = self._categorize_doc(raw_file)
        title = raw_file.stem  # filename without extension

        # Build LLM prompt for ingest
        ingest_prompt = f"""你是一个知识库管理员。请仔细阅读以下文档，然后按照规则创建或更新 wiki 页面。

原始文档路径: {relative_path}
文档类型: {category}
建议页面类型: {self._guess_page_type(category)}

## 原始文档内容
{content[:8000]}

## 你的任务
1. 提取文档中的关键实体（人名、产品名、公司名、术语）
2. 提取核心概念和流程
3. 判断该文档属于哪个类别（entities / concepts / overviews）
4. 生成 wiki 页面内容（使用 [[双向链接]] 引用相关页面）
5. 给出你将创建/更新的页面列表

请以 JSON 格式返回，字段说明：
- "pages": [
    {{
      "title": "页面标题",
      "type": "entity / concept / overview",
      "access": "public / dept-sales / admin",
      "content": "# 页面标题\\n\\n正文内容...",
      "path": "entities/xxx.md 或 concepts/xxx.md 或 overviews/xxx.md"
    }}
  ]
- "index_updates": 建议添加到 index.md 的条目列表
- "related_existing": 建议链接到的已有页面标题列表

只返回 JSON，不要有其他文字。"""

        logger.info(f"Ingesting document: {raw_file.name}")
        raw_response = self.client.generate(
            system=system_prompt,
            user_message=ingest_prompt,
            max_tokens=4000,
        )

        # Parse JSON response
        pages_data = self._parse_json_response(raw_response)

        if not pages_data:
            logger.warning(f"Failed to parse LLM ingest response for {raw_file.name}")
            return {"success": False, "pages_created": 0, "pages_updated": 0}

        created = 0
        updated = 0

        for page in pages_data.get("pages", []):
            page_path = self.wiki_dir / page["path"]
            is_new = not page_path.exists()
            page_path.parent.mkdir(parents=True, exist_ok=True)
            page_path.write_text(page["content"], encoding="utf-8")

            if is_new:
                created += 1
            else:
                updated += 1
            logger.info(f"{'Created' if is_new else 'Updated'}: {page['path']}")

        # Update index.md
        self._update_index(pages_data.get("index_updates", []))

        # Update log.md
        self._append_log("ingest", relative_path, doc_path, created, updated)

        # Git commit
        self._git_commit(f"ingest: {raw_file.name} (+{created}/~{updated})")

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

        Steps:
        1. Read index.md to find relevant pages
        2. Call LLM to identify which pages are relevant
        3. Deep read those pages
        4. Synthesize answer
        5. Return structured response

        Args:
            question: User's question
            user_id: Optional user identifier for history

        Returns:
            QueryResponse with answer, wiki_pages, raw_sources, confidence
        """
        self._init_git_repo()
        system_prompt = self._get_system_prompt()

        # Read index.md
        if not self.index_md.exists():
            return {
                "answer": "知识库尚未初始化，请先摄入文档。",
                "wiki_pages": [],
                "raw_sources": [],
                "confidence": "low",
            }

        index_content = self.index_md.read_text(encoding="utf-8")

        # Phase 1: Find relevant pages using index
        find_prompt = f"""你是知识库助手。用户提问时，先从索引中找相关页面。

当前索引内容:
{index_content[:5000]}

用户问题: {question}

请从索引中找出与问题最相关的 3~5 个页面，只返回页面标题列表，用逗号分隔。

只返回页面标题列表，其他什么都不要。"""

        relevant_titles_raw = self.client.generate(
            system=system_prompt,
            user_message=find_prompt,
            max_tokens=500,
        )

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
        answer_prompt = f"""基于以下 wiki 页面内容，回答用户问题。

## Wiki 页面内容
{wiki_context}

## 用户问题
{question}

请综合以上内容给出回答。回答格式要求：
- 给出清晰、结构化的答案
- 引用相关页面（用 [[页面标题]] 格式）
- 标注答案的可信度 (high/medium/low)
- 如果发现知识空白，在回答末尾注明"待补充"

最后以 JSON 格式返回：
{{
  "answer": "综合回答...",
  "confidence": "high/medium/low",
  "cited_pages": ["页面标题1", "页面标题2"]
}}

只返回 JSON。"""

        raw_response = self.client.generate(
            system=system_prompt,
            user_message=answer_prompt,
            max_tokens=2000,
        )

        answer_data = self._parse_json_response(raw_response)

        if not answer_data:
            # Fallback: return raw text
            return {
                "answer": raw_response[:1000],
                "wiki_pages": [{"title": t, "path": self._find_wiki_page(t) or ""} for t in relevant_titles],
                "raw_sources": [],
                "confidence": "medium",
            }

        # Build wiki_pages list
        wiki_pages = []
        for title in answer_data.get("cited_pages", relevant_titles):
            page_path = self._find_wiki_page(title)
            if page_path:
                wiki_pages.append({"title": title, "path": str(page_path.relative_to(self.wiki_dir))})

        return {
            "answer": answer_data.get("answer", ""),
            "wiki_pages": wiki_pages,
            "raw_sources": [],
            "confidence": answer_data.get("confidence", "medium"),
        }

    # ─── Lint ────────────────────────────────────────────────────────────

    def lint(self) -> dict:
        """
        Check wiki health: orphaned pages, broken links, contradictions.

        Returns:
            LintReport dict
        """
        self._init_git_repo()
        system_prompt = self._get_system_prompt()

        # Collect all wiki pages
        all_pages = {}
        for page_path in self.wiki_dir.rglob("*.md"):
            if page_path.name in ("index.md", "log.md"):
                continue
            rel = page_path.relative_to(self.wiki_dir)
            content = page_path.read_text(encoding="utf-8")
            all_pages[str(rel)] = {"content": content, "title": self._extract_title(content)}

        # Find all [[links]]
        all_links = set()
        link_source = {}
        for rel, data in all_pages.items():
            links = re.findall(r"\[\[([^\]]+)\]\]", data["content"])
            for link in links:
                all_links.add(link)
                link_source.setdefault(link, []).append(rel)

        # Check orphaned pages (not linked from any other page)
        all_titles = {d["title"] for d in all_pages.values()}
        orphaned = []
        for rel, data in all_pages.items():
            if data["title"] not in all_links and rel not in ["index.md"]:
                orphaned.append(data["title"])

        # Check broken links (link target doesn't exist)
        broken_links = []
        for link in all_links:
            if link not in all_titles:
                for source in link_source.get(link, []):
                    broken_links.append(f"{link} (from {source})")

        # LLM-powered deeper analysis
        all_content = "\n\n".join(
            f"=== {d['title']} ===\n{d['content'][:1000]}" for d in all_pages.values()
        )

        lint_prompt = f"""你是知识库健康检查员。请分析以下 wiki 内容，发现问题。

## Wiki 内容摘要
{all_content[:8000]}

## 已发现的问题
- 孤立页面（未被引用）: {orphaned}
- 断链: {broken_links}

请深入检查以下问题：
1. 矛盾陈述（两个页面说法冲突）
2. 过时内容（明显失效的信息）
3. 页面类型错误（entity 放在 concepts 或反之）
4. 访问级别错误（敏感内容标记为 public）

请以 JSON 格式返回：
{{
  "contradictions": ["矛盾描述1", "矛盾描述2"],
  "stale_pages": ["过时页面标题1"],
  "suggestions": ["优化建议1", "优化建议2"]
}}

如果某项为空，返回空列表。只返回 JSON。"""

        raw_response = self.client.generate(
            system=system_prompt,
            user_message=lint_prompt,
            max_tokens=2000,
        )

        lint_data = self._parse_json_response(raw_response) or {}

        return {
            "orphaned_pages": orphaned,
            "broken_links": broken_links,
            "contradictions": lint_data.get("contradictions", []),
            "stale_pages": lint_data.get("stale_pages", []),
            "suggestions": lint_data.get("suggestions", []),
        }

    # ─── Helpers ─────────────────────────────────────────────────────────

    def _parse_json_response(self, text: str) -> Optional[dict]:
        """Extract JSON from LLM response (handles markdown code blocks)"""
        text = text.strip()
        # Try to find JSON in code block
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
        else:
            # Try to find first { to last }
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                text = text[start : end + 1]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON: {text[:200]}")
            return None

    def _categorize_doc(self, path: Path) -> str:
        """Guess document category from path"""
        rel = str(path.relative_to(self.raw_dir))
        if "meeting" in rel.lower() or "会议" in rel:
            return "meeting-notes"
        if "article" in rel.lower():
            return "articles"
        if "sheet" in rel.lower() or "表格" in rel:
            return "sheets"
        return "articles"

    def _guess_page_type(self, category: str) -> str:
        if category == "meeting-notes":
            return "overview"
        if category == "sheets":
            return "overview"
        return "entity"

    def _extract_title(self, content: str) -> str:
        """Extract title from markdown frontmatter or first heading"""
        m = re.search(r"^title:\s*(.+)$", content, re.MULTILINE)
        if m:
            return m.group(1).strip()
        m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if m:
            return m.group(1).strip()
        return ""

    def _find_wiki_page(self, title: str) -> Optional[Path]:
        """Find a wiki page by title"""
        for page_path in self.wiki_dir.rglob("*.md"):
            if page_path.name in ("index.md", "log.md"):
                continue
            content = page_path.read_text(encoding="utf-8")
            page_title = self._extract_title(content)
            if page_title == title:
                return page_path
        return None

    def _update_index(self, new_entries: list[str]):
        """Add new entries to index.md"""
        if not new_entries:
            return

        if not self.index_md.exists():
            index_content = "# 知识库索引\n\n"
        else:
            index_content = self.index_md.read_text(encoding="utf-8")

        # Simple append (LLM will refine in future)
        new_entries_md = "\n".join(f"- {e}" for e in new_entries)
        index_content += f"\n## 新增页面\n{new_entries_md}\n"

        self.index_md.write_text(index_content, encoding="utf-8")
        logger.info(f"Updated index.md with {len(new_entries)} entries")

    def _append_log(self, operation: str, doc_path: str, source: str, created: int, updated: int):
        """Append to log.md"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        log_entry = f"- [{now}] {operation}: `{doc_path}` (+{created}/~{updated})\n"

        if self.log_md.exists():
            content = self.log_md.read_text(encoding="utf-8")
        else:
            content = "# 操作日志\n\n"

        self.log_md.write_text(content + log_entry, encoding="utf-8")
        logger.info(f"Logged: {operation} on {doc_path}")
