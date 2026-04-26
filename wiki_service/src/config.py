"""Configuration for wiki_service - aligns with ARCHITECTURE.md三层架构"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM Provider - support Claude or MiniMax
    llm_provider: str = "claude"  # "claude" or "minimax"

    # Feishu (optional - for sync)
    feishu_app_id: str = ""
    feishu_app_secret: str = ""

    # Claude API
    claude_api_key: str = ""

    # MiniMax API (alternative to Claude)
    minimax_api_key: str = ""
    minimax_api_base: str = "https://api.minimax.chat/v1"

    # Wiki repository - Git仓库结构定义在 ARCHITECTURE.md 第二章
    wiki_repo_path: Path = Path(__file__).parent.parent / "wiki_repo"

    # Feishu sync (optional)
    feishu_space_id: str = ""

    # Ingest token budget
    max_ingest_tokens: int = 6000

    # Derived paths - WikiRepo 结构
    @property
    def claude_md_path(self) -> Path:
        return self.wiki_repo_path / "CLAUDE.md"

    @property
    def wiki_dir(self) -> Path:
        return self.wiki_repo_path / "wiki"

    @property
    def raw_dir(self) -> Path:
        return self.wiki_repo_path / "raw"

    @property
    def index_md_path(self) -> Path:
        return self.wiki_dir / "index.md"

    @property
    def log_md_path(self) -> Path:
        return self.wiki_dir / "log.md"

    # Subdirectories
    @property
    def raw_articles_dir(self) -> Path:
        return self.raw_dir / "articles"

    @property
    def raw_pdfs_dir(self) -> Path:
        return self.raw_dir / "pdfs"

    @property
    def raw_meeting_notes_dir(self) -> Path:
        return self.raw_dir / "meeting-notes"

    @property
    def raw_tables_dir(self) -> Path:
        return self.raw_dir / "tables"


settings = Settings()