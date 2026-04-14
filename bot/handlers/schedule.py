import logging
from datetime import timedelta

from telegram.ext import ContextTypes

from bot import database as db
from bot.config import GROUP_CHAT_ID
from bot.handlers.status import build_weekly_report
from bot.utils import today_kst

logger = logging.getLogger(__name__)


async def weekly_report_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scheduled job: post weekly score report every Monday 10:00 KST.

    When this fires on Monday, the "last completed week" is the previous
    Mon-Sun, so we pass yesterday (Sunday) as the report date.
    """
    yesterday = today_kst() - timedelta(days=1)
    report = build_weekly_report(report_date=yesterday)
    await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=report)
    logger.info("Weekly report sent for week ending %s", yesterday)


async def daily_summary_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scheduled job: post daily verification summary at 23:00 KST."""
    d = today_kst()
    verifications = db.get_daily_verifications(d)

    if not verifications:
        names_str = "없음"
    else:
        names = [v["display_name"] for v in verifications]
        names_str = " ".join(names)

    weekday_names = ["월", "화", "수", "목", "금", "토", "일"]
    weekday = weekday_names[d.weekday()]

    text = f"{d.month}/{d.day} {weekday}\n{names_str}"
    await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=text)
    logger.info("Daily summary sent for %s: %s", d, names_str)
