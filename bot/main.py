import logging
from datetime import time

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from bot.config import TELEGRAM_BOT_TOKEN
from bot.database import init_db
from bot.handlers.admin import (
    add_log_command,
    del_log_command,
    register_command,
    report_command,
    set_quarter_command,
)
from bot.handlers.goals import my_goal_command, set_goal_command
from bot.handlers.schedule import daily_summary_job, weekly_report_job
from bot.handlers.status import score_command, status_command, weekly_command
from bot.handlers.verification import handle_photo
from bot.utils import KST

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    init_db()
    logger.info("Database initialized")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # ── Command handlers ────────────────────────────────────────
    # Goal setting
    app.add_handler(CommandHandler(["목표설정", "setgoal"], set_goal_command))
    app.add_handler(CommandHandler(["내목표", "mygoal"], my_goal_command))

    # Status / scores
    app.add_handler(CommandHandler(["현황", "status"], status_command))
    app.add_handler(CommandHandler(["주간", "weekly"], weekly_command))
    app.add_handler(CommandHandler(["점수", "score"], score_command))

    # Admin
    app.add_handler(CommandHandler(["수동인증", "addlog"], add_log_command))
    app.add_handler(CommandHandler(["수동인증삭제", "dellog"], del_log_command))
    app.add_handler(CommandHandler(["분기설정", "setquarter"], set_quarter_command))
    app.add_handler(CommandHandler(["리포트", "report"], report_command))

    # Registration
    app.add_handler(CommandHandler(["등록", "register"], register_command))

    # ── Photo handler (exercise verification) ───────────────────
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # ── Scheduled jobs ──────────────────────────────────────────
    job_queue = app.job_queue

    # Weekly report: every Monday at 10:00 KST
    job_queue.run_daily(
        weekly_report_job,
        time=time(hour=10, minute=0, tzinfo=KST),
        days=(0,),  # 0 = Monday
        name="weekly_report",
    )

    # Daily summary: every day at 23:00 KST
    job_queue.run_daily(
        daily_summary_job,
        time=time(hour=23, minute=0, tzinfo=KST),
        name="daily_summary",
    )

    logger.info("Bot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
