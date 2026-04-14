import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot import database as db
from bot.config import GROUP_CHAT_ID
from bot.utils import today_kst, week_bounds

logger = logging.getLogger(__name__)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process a photo sent to the group as an exercise verification."""
    message = update.effective_message
    if message is None or message.photo is None:
        return

    chat = update.effective_chat
    if chat is None or chat.id != GROUP_CHAT_ID:
        return

    user = update.effective_user
    if user is None:
        return

    telegram_id = user.id
    display_name = user.full_name
    username = user.username

    # Ensure member is registered
    db.upsert_member(telegram_id, username, display_name)

    exercise_date = today_kst()

    # Check if the user has a goal set for the current quarter
    quarter_start = db.get_quarter_start()
    if exercise_date < quarter_start:
        return

    goal = db.get_goal(telegram_id, quarter_start)
    if goal is None:
        await message.reply_text(
            f"{display_name}님, 이번 분기 주간 목표가 설정되지 않았습니다.\n"
            f"/목표설정 N 명령어로 목표를 먼저 설정해주세요! (예: /목표설정 3)",
        )
        return

    # Get the best quality photo (last in the list = largest)
    photo_file_id = message.photo[-1].file_id

    # Extract note from caption
    note = message.caption.strip() if message.caption else None

    # Try to add verification
    success = db.add_verification(
        telegram_id=telegram_id,
        exercise_date=exercise_date,
        photo_file_id=photo_file_id,
        is_manual=False,
        note=note,
    )

    if success:
        monday, sunday = week_bounds(exercise_date)
        week_count = db.count_verifications_range(telegram_id, monday, sunday)
        await message.reply_text(
            f"{display_name}님 오늘 운동 인증 완료!\n"
            f"이번 주: {week_count}/{goal}회",
        )
        logger.info(
            "Verification recorded: user=%s date=%s", telegram_id, exercise_date
        )
    else:
        await message.reply_text(
            f"{display_name}님, 오늘은 이미 인증되었습니다.",
        )
