"""统一配置管理"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 飞书
    feishu_app_id: str
    feishu_app_secret: str
    feishu_verification_token: str = ""
    feishu_encrypt_key: str = ""

    # 数据库
    postgres_dsn: str
    redis_url: str = "redis://localhost:6379/0"

    # 向量库
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "pe_kb_chunks"

    # LLM
    dashscope_api_key: str = ""
    embedding_model: str = "text-embedding-v3"
    embedding_dim: int = 1024
    llm_model: str = "qwen-max"


settings = Settings()