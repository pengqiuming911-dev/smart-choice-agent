"""Configuration for wiki_service"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Feishu
    feishu_app_id: str = ""
    feishu_app_secret: str = ""

    # Claude API
    claude_api_key: str = ""
    claude_model: str = "claude-sonnet-4-7"

    # Wiki repository
    wiki_repo_path: Path = Path(__file__).parent.parent / "wiki_repo"

    # Feishu sync
    feishu_space_id: str = ""  # 知识空间 ID，留空则使用第一个空间
    feishu_folder_fanfei: str = ""   # 返费文件夹 token
    feishu_folder_chanpin: str = ""  # 产品运营文件夹 token
    feishu_folder_zhuanhuan: str = ""  # 转换运营文件夹 token
    feishu_high_freq: bool = True  # 高频文档每天同步

    # Ingest
    max_ingest_tokens: int = 6000  # 单次 ingest 最大 token 预算

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


settings = Settings()
