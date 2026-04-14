import logging
from datetime import time

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from bot.config import TELEGRAM_BOT_TOKEN
from bot.database import init_db
from bot.config import GROUP_CHAT_ID
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

HELP_TEXT = """운동인증봇 명령어 안내

[인증]
사진 전송 → 오늘 운동 인증 (캡션에 메모 가능)

[목표]
/setgoal N — 이번 분기 주간 목표 설정 (예: /setgoal 5)
/mygoal — 내 목표 확인

[현황]
/status — 내 이번 주 현황 + 분기 점수
/weekly — 이번 주 전체 팀원 현황
/score — 분기 누적 점수 랭킹

[등록]
/register — 봇에 멤버 등록

[관리자]
/addlog @user YYYY-MM-DD — 수동 인증 추가
/dellog @user YYYY-MM-DD — 인증 삭제
/setquarter YYYY-MM-DD — 분기 시작일 설정
/report — 주간 리포트 즉시 생성"""


async def help_command(update, context):
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    if chat.id != GROUP_CHAT_ID:
        return
    await message.reply_text(HELP_TEXT)


def main() -> None:
    init_db()
    logger.info("Database initialized")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # ── Command handlers ────────────────────────────────────────
    # Help
    app.add_handler(CommandHandler("help", help_command))

    # Goal setting
    app.add_handler(CommandHandler("setgoal", set_goal_command))
    app.add_handler(CommandHandler("mygoal", my_goal_command))

    # Status / scores
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("weekly", weekly_command))
    app.add_handler(CommandHandler("score", score_command))

    # Admin
    app.add_handler(CommandHandler("addlog", add_log_command))
    app.add_handler(CommandHandler("dellog", del_log_command))
    app.add_handler(CommandHandler("setquarter", set_quarter_command))
    app.add_handler(CommandHandler("report", report_command))

    # Registration
    app.add_handler(CommandHandler("register", register_command))

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
