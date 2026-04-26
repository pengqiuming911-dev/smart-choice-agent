"""Daily market report job - fetches market data + product data and pushes to Feishu"""
import time
from datetime import datetime
from src.config import settings
from src.sender import get_sender
from src.jobs.report_builder import build_daily_report, build_daily_report_card


def _send_with_retry(sender, method, open_id, content, max_retries=3):
    """Send message with exponential backoff retry"""
    for attempt in range(max_retries):
        try:
            ok = method(open_id, content)
            if ok:
                return True
        except Exception as e:
            print(f"[RETRY] Attempt {attempt+1} failed: {e}")
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)
    return False


def daily_report_job():
    """
    每日收盘报告任务

    流程：
    1. 从同花顺获取指数行情（AKShare）
    2. 从飞书「产品表-同步」获取产品净值
    3. 组合成报告卡片发送到飞书
    """
    sender = get_sender()
    now = datetime.now()

    target_open_id = settings.scheduler_target_open_id
    if not target_open_id:
        print("[WARN] SCHEDULER_TARGET_OPEN_ID not configured, skipping push")
        return

    # 构建纯文本报告
    text_report = build_daily_report()
    success = _send_with_retry(sender, sender.send_message, target_open_id, text_report)

    if success:
        print(f"[INFO] Daily report sent at {now}")
    else:
        print(f"[ERROR] Failed to send daily report at {now}")


def daily_report_card_job():
    """
    每日收盘报告任务（卡片版本）

    发送富文本卡片消息（指数行情表格 + 产品净值表格）
    """
    sender = get_sender()
    now = datetime.now()

    target_open_id = settings.scheduler_target_open_id
    if not target_open_id:
        print("[WARN] SCHEDULER_TARGET_OPEN_ID not configured, skipping push")
        return

    # 构建卡片
    card = build_daily_report_card()
    success = _send_with_retry(sender, sender.send_card, target_open_id, card)

    if success:
        print(f"[INFO] Daily report card sent at {now}")
    else:
        print(f"[ERROR] Failed to send daily report card at {now}")
