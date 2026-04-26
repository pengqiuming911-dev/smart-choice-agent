"""Configuration for scheduler service"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Feishu
    feishu_app_id: str = os.getenv("FEISHU_APP_ID", "")
    feishu_app_secret: str = os.getenv("FEISHU_APP_SECRET", "")

    # Push target
    scheduler_target_open_id: str = os.getenv("SCHEDULER_TARGET_OPEN_ID", "")
    scheduler_hour: int = int(os.getenv("SCHEDULER_HOUR", "15"))
    scheduler_minute: int = int(os.getenv("SCHEDULER_MINUTE", "30"))

    # Feishu Bitable (产品表-同步)
    bitable_app_id: str = os.getenv("BITABLE_APP_ID", "")
    bitable_table_id: str = os.getenv("BITABLE_TABLE_ID", "")
    bitable_token: str = os.getenv("BITABLE_TOKEN", "")  # 多维表格 token

    # Market data - indices to track
    market_indices: list = os.getenv(
        "MARKET_INDICES",
        "上证指数,创业板指,科创50,沪深300"
    ).split(",")

    # 敲出点位每月递减比例（来自参考表格，单位%，如 0.5 表示 0.5%）
    monthly_decrement: float = float(os.getenv("MONTHLY_DECREMENT", "0.5"))

    # Timezone
    timezone: str = "Asia/Shanghai"

    @property
    def indices_list(self) -> list:
        return [idx.strip() for idx in self.market_indices if idx.strip()]


settings = Settings()
