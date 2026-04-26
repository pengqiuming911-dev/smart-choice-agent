"""APScheduler 定时调度器"""
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from rag_service.config import settings
from rag_service.scheduler.jobs import daily_report_job, test_job


def main():
    """启动定时调度器"""
    logger.info("Starting scheduler service...")

    # 配置日志
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )

    # 每日推送时间，默认 15:30
    hour = getattr(settings, "scheduler_hour", 15)
    minute = getattr(settings, "scheduler_minute", 30)

    scheduler = BlockingScheduler(timezone="Asia/Shanghai")

    # 添加每日定时任务
    scheduler.add_job(
        daily_report_job,
        CronTrigger(hour=hour, minute=minute, timezone="Asia/Shanghai"),
        id="daily_report",
        name="每日行业动态推送",
        replace_existing=True,
    )

    logger.info(f"Scheduled daily report job at {hour:02d}:{minute:02d}")

    # 可选：添加测试任务（每小时运行一次用于调试）
    # scheduler.add_job(
    #     test_job,
    #     CronTrigger(minute=0),  # 每小时整点
    #     id="test_job",
    #     name="测试任务",
    # )

    try:
        logger.info("Scheduler started. Press Ctrl+C to exit.")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
