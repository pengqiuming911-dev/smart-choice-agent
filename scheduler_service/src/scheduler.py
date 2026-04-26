"""APScheduler-based scheduler entry point"""
import sys
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from src.config import settings
from src.jobs import daily_report_job, daily_report_card_job


def main():
    """Start the scheduler service"""
    logger.info("Starting scheduler service...")

    # Validate required config
    if not settings.feishu_app_id or not settings.feishu_app_secret:
        logger.error("FEISHU_APP_ID and FEISHU_APP_SECRET are required")
        sys.exit(1)

    if not settings.scheduler_target_open_id:
        logger.warning("SCHEDULER_TARGET_OPEN_ID not set, reports will not be sent")

    logger.info(f"Scheduled hourly report at minute=0 ({settings.timezone})")
    logger.info(f"Indices: {settings.indices_list}")
    logger.info(f"Bitable: app_id={settings.bitable_app_id}, table_id={settings.bitable_table_id}")

    scheduler = BlockingScheduler(timezone=settings.timezone)

    # 每小时推送报告
    scheduler.add_job(
        daily_report_job,
        CronTrigger(minute=0, timezone=settings.timezone),
        id="hourly_report",
        name="每小时收盘简报",
        replace_existing=True,
    )

    try:
        logger.info("Scheduler started. Press Ctrl+C to exit.")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
