"""FastAPI application - API layer as defined in ARCHITECTURE.md"""
import re
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.api.models import (
    QueryRequest,
    QueryResponse,
    IngestRequest,
    IngestResponse,
    LintReport,
    HealthResponse,
)
from src.agent import WikiAgent
from src.sync import FeishuClient
from src.config import settings

app = FastAPI(title="LLM Wiki Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health():
    """Health check - verify wiki repo exists"""
    return HealthResponse(
        status="ok",
        wiki_repo=str(settings.wiki_repo_path),
        repo_exists=settings.wiki_repo_path.exists(),
    )


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    """
    Query the wiki knowledge base.

    Flow (from ARCHITECTURE.md):
    1. LLM reads index.md to find relevant pages
    2. Deep reads those pages
    3. Synthesizes answer
    4. Returns structured response with sources
    """
    try:
        agent = WikiAgent()
        result = agent.query(req.question, req.user_id)
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest", response_model=IngestResponse)
def ingest(req: IngestRequest):
    """
    Ingest a document into the wiki.

    Supports two modes:
    - Feishu: pass doc_token, we fetch and convert
    - Local: pass file_path directly
    """
    try:
        agent = WikiAgent()

        if req.doc_token:
            # Fetch from Feishu
            if not settings.feishu_app_id:
                raise HTTPException(status_code=400, detail="FEISHU_APP_ID not configured")

            client = FeishuClient(settings.feishu_app_id, settings.feishu_app_secret)
            md_content = client.get_docx_markdown(req.doc_token)

            safe_name = f"feishu_{req.doc_token[:8]}"
            raw_path = settings.raw_dir / "articles" / f"{safe_name}.md"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(md_content, encoding="utf-8")

            result = agent.ingest(str(raw_path.relative_to(settings.wiki_repo_path)))

        elif req.file_path:
            result = agent.ingest(req.file_path)
        else:
            raise HTTPException(status_code=400, detail="Either doc_token or file_path is required")

        return IngestResponse(
            success=result.get("success", False),
            message=f"+{result.get('pages_created', 0)} created, ~{result.get('pages_updated', 0)} updated",
            pages_created=result.get("pages_created", 0),
            pages_updated=result.get("pages_updated", 0),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/lint", response_model=LintReport)
def lint():
    """Run wiki health check - detect orphaned pages, broken links, contradictions"""
    try:
        agent = WikiAgent()
        report = agent.lint()
        return LintReport(**report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/wiki/list")
def wiki_list():
    """List all wiki pages with metadata"""
    try:
        wiki_dir = settings.wiki_dir
        if not wiki_dir.exists():
            return {"pages": []}

        pages = []
        for md_file in wiki_dir.rglob("*.md"):
            if md_file.name in ("index.md", "log.md"):
                continue
            rel_path = str(md_file.relative_to(settings.wiki_repo_path))
            content = md_file.read_text(encoding="utf-8")

            title = md_file.stem
            page_type = "page"
            access = "public"

            # Parse frontmatter
            fm_match = re.match(r"^---\n(.+?)\n---", content, re.DOTALL)
            if fm_match:
                fm_text = fm_match.group(1)
                title_m = re.search(r"title:\s*(.+)", fm_text)
                type_m = re.search(r"type:\s*(.+)", fm_text)
                access_m = re.search(r"access:\s*(.+)", fm_text)
                if title_m:
                    title = title_m.group(1).strip()
                if type_m:
                    page_type = type_m.group(1).strip()
                if access_m:
                    access = access_m.group(1).strip()

            pages.append({
                "title": title,
                "path": rel_path,
                "type": page_type,
                "access": access,
            })

        return {"pages": pages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/wiki/page")
def wiki_page(path: str = Query(...)):
    """Get wiki page content with access control"""
    try:
        safe_path = settings.wiki_repo_path / path
        if not safe_path.resolve().is_relative_to(settings.wiki_repo_path.resolve()):
            raise HTTPException(status_code=400, detail="Invalid path")

        file_path = settings.wiki_repo_path / path
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Page not found")

        content = file_path.read_text(encoding="utf-8")

        # Extract title from frontmatter
        title = file_path.stem
        fm_match = re.match(r"^---\n(.+?)\n---", content, re.DOTALL)
        if fm_match:
            title_m = re.search(r"title:\s*(.+)", fm_match.group(1))
            if title_m:
                title = title_m.group(1).strip()

        return {"content": content, "title": title}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def root():
    """Root endpoint - service info"""
    return {
        "service": "LLM Wiki Agent",
        "version": "1.0.0",
        "endpoints": ["/health", "/query", "/ingest", "/lint", "/wiki/list", "/wiki/page"],
        "architecture": "Layer 3 Schema → Layer 2 Wiki (LLM managed) → Layer 1 Raw",
    }