"""FastAPI server for wiki_service"""
import re
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.models import QueryRequest, QueryResponse, IngestRequest, IngestResponse, LintReport
from src.wiki_agent import WikiAgent
from src.config import settings

app = FastAPI(title="LLM Wiki Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Health check"""
    return {
        "status": "ok",
        "wiki_repo": str(settings.wiki_repo_path),
        "repo_exists": settings.wiki_repo_path.exists(),
    }


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    """Query the wiki knowledge base."""
    try:
        agent = WikiAgent()
        result = agent.query(req.question, req.user_id)
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest", response_model=IngestResponse)
def ingest(req: IngestRequest):
    """Ingest a document into the wiki."""
    try:
        agent = WikiAgent()

        if req.doc_token:
            from src.feishu_client import FeishuClient

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
            raise HTTPException(
                status_code=400,
                detail="Either doc_token or file_path is required",
            )

        return IngestResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/lint", response_model=LintReport)
def lint():
    """Run wiki health check"""
    try:
        agent = WikiAgent()
        report = agent.lint()
        return LintReport(**report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/wiki/list")
def wiki_list():
    """List all wiki pages"""
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
    """Get wiki page content"""
    try:
        # Security: prevent directory traversal
        safe_path = settings.wiki_repo_path / path
        if not safe_path.resolve().is_relative_to(settings.wiki_repo_path.resolve()):
            raise HTTPException(status_code=400, detail="Invalid path")

        file_path = settings.wiki_repo_path / path
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Page not found")

        content = file_path.read_text(encoding="utf-8")

        # Extract title from frontmatter or filename
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
    return {
        "service": "LLM Wiki Agent",
        "version": "1.0.0",
        "endpoints": ["/health", "/query", "/ingest", "/lint", "/wiki/list", "/wiki/page"],
    }
