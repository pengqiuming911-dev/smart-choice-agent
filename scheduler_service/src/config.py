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
    bitable_token: str = os.getenv("BITABLE_TOKEN", "")

    # Feishu spreadsheet (每月递减参考表)
    decrement_sheet_token: str = os.getenv("DECREMENT_SHEET_TOKEN", "")
    decrement_sheet_id: str = os.getenv("DECREMENT_SHEET_ID", "")

    # Market data - indices to track (optional override; defaults to all indices from Bitable)
    market_indices: list = os.getenv("MARKET_INDICES", "").split(",")

    # 敲出点位每月递减比例（全局默认值，若参考表有则用参考表中的值）
    monthly_decrement: float = float(os.getenv("MONTHLY_DECREMENT", "0.5"))

    # Timezone
    timezone: str = "Asia/Shanghai"

    @property
    def indices_list(self) -> list:
        if self.market_indices and self.market_indices != [""]:
            return [idx.strip() for idx in self.market_indices if idx.strip()]
        # No env override: dynamically fetch all unique indices from Bitable
        try:
            from src.feishu_bitable import build_index_code_map
            code_map = build_index_code_map()
            if code_map:
                return list(code_map.keys())
        except Exception:
            pass
        return []


settings = Settings()
