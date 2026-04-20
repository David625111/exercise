import logging
from datetime import time

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, TypeHandler, filters

from bot.config import TELEGRAM_BOT_TOKEN
from bot.database import init_db
from bot.config import GROUP_CHAT_ID
from bot.handlers.admin import (
    add_log_command,
    bulk_score_command,
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

HELP_TEXT = """\
🏋 논클 운동인증봇 사용 안내

📌 기본 규칙
• 하루 50분 이상 운동하면 1회 인증 완료
• 운동 사진 + 시간을 함께 보내야 기록됩니다
• 여러 번 나눠서 보내도 하루 합산으로 계산됩니다
  (예: 요가 20분 + 산책 30분 = 50분 → 인증 완료!)
• 한 주(월~일) 동안 목표 횟수를 채우면 분기 점수 +1

📸 운동 인증 방법
사진을 보내면서 캡션에 운동 시간을 적어주세요
  예: "크로스핏 50분"
  예: "러닝 1시간"
  예: "요가 30분 + 필라테스 25분"

📋 명령어

[처음 시작]
/register — 봇에 멤버 등록
/setgoal N — 주간 목표 설정 (예: /setgoal 3 → 주 3회)

[현황 확인]
/status — 내 이번 주 인증 현황 + 분기 점수
/weekly — 이번 주 전체 팀원 현황
/score — 분기 누적 점수 랭킹
/mygoal — 내 주간 목표 확인

[관리자 전용]
/addlog @user YYYY-MM-DD — 수동 인증 추가
/dellog @user YYYY-MM-DD — 인증 삭제
/setquarter YYYY-MM-DD — 분기 시작일 설정
/report — 주간 리포트 즉시 생성
/bulkscore @u1 N @u2 N ... — 분기 점수 일괄 조정 (가산점 덮어쓰기)

⏰ 자동 알림
• 매일 밤 11시 — 당일 인증 현황 요약
• 매주 월요일 오전 10시 — 지난 주 점수 집계"""


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

    # ── Debug: reply with diagnostic info for media messages ───
    async def log_update(update: Update, context):
        msg = update.message or update.edited_message
        if msg and msg.chat_id == GROUP_CHAT_ID:
            has_photo = bool(msg.photo)
            has_doc = bool(msg.document)
            mime = msg.document.mime_type if msg.document else None
            has_video = bool(msg.video)
            has_anim = bool(msg.animation)
            has_sticker = bool(msg.sticker)

            # Log debug info for any non-text message (logs only, not chat)
            if not msg.text:
                logger.info(
                    "[DEBUG] photo=%s, doc=%s, mime=%s, video=%s, "
                    "anim=%s, sticker=%s, caption=%r",
                    has_photo, has_doc, mime, has_video,
                    has_anim, has_sticker, msg.caption,
                )

    app.add_handler(TypeHandler(Update, log_update), group=-1)

    # ── Error handler ──────────────────────────────────────────
    async def error_handler(update, context):
        logger.error("Unhandled exception: %s", context.error, exc_info=context.error)

    app.add_error_handler(error_handler)

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
    app.add_handler(CommandHandler("bulkscore", bulk_score_command))

    # Registration
    app.add_handler(CommandHandler("register", register_command))

    # ── Photo handler (exercise verification) ───────────────────
    # Handle photos sent as "photo" OR as "file/document" (image)
    photo_or_image_doc = filters.PHOTO | filters.Document.ALL
    app.add_handler(MessageHandler(photo_or_image_doc, handle_photo))
    app.add_handler(MessageHandler(
        photo_or_image_doc & filters.UpdateType.EDITED_MESSAGE, handle_photo
    ))

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
