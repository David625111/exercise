import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot import database as db
from bot.config import GROUP_CHAT_ID
from bot.utils import MINUTES_THRESHOLD, parse_minutes, today_kst, week_bounds

logger = logging.getLogger(__name__)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process a photo sent to the group as an exercise verification.

    Flow:
    1. Parse minutes from caption
    2. Add to exercise_logs
    3. Check daily total — if >= 50 min and not yet verified, mark verified
    """
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

    # Check quarter
    quarter_start = db.get_quarter_start()
    if exercise_date < quarter_start:
        return

    # Check goal
    goal = db.get_goal(telegram_id, quarter_start)
    if goal is None:
        await message.reply_text(
            f"{display_name}님, 이번 분기 주간 목표가 설정되지 않았습니다.\n"
            "/setgoal N 명령어로 목표를 먼저 설정해주세요! (예: /setgoal 3)",
        )
        return

    # Parse minutes from caption
    caption = message.caption.strip() if message.caption else None
    minutes = parse_minutes(caption)

    if minutes is None:
        await message.reply_text(
            "운동 시간을 적어주세요!\n"
            "예: 30분, 1시간, 크로스핏 50분",
        )
        return

    if minutes <= 0:
        await message.reply_text("운동 시간은 1분 이상이어야 합니다.")
        return

    # Get best quality photo
    photo_file_id = message.photo[-1].file_id

    # Record exercise log
    db.add_exercise_log(
        telegram_id=telegram_id,
        exercise_date=exercise_date,
        minutes=minutes,
        photo_file_id=photo_file_id,
        note=caption,
    )

    # Check daily total
    daily_total = db.get_daily_total_minutes(telegram_id, exercise_date)
    already_verified = db.count_verifications_range(
        telegram_id, exercise_date, exercise_date
    ) > 0

    if daily_total >= MINUTES_THRESHOLD and not already_verified:
        # Mark as verified
        db.add_verification(
            telegram_id=telegram_id,
            exercise_date=exercise_date,
            photo_file_id=photo_file_id,
            is_manual=False,
            note=f"누적 {daily_total}분",
        )
        monday, sunday = week_bounds(exercise_date)
        week_count = db.count_verifications_range(telegram_id, monday, sunday)
        await message.reply_text(
            f"{display_name}님 {minutes}분 기록! "
            f"오늘 누적: {daily_total}/{MINUTES_THRESHOLD}분 \u2705 인증 완료!\n"
            f"이번 주: {week_count}/{goal}회",
        )
        logger.info(
            "Verification completed: user=%s date=%s total=%d min",
            telegram_id, exercise_date, daily_total,
        )
    elif already_verified:
        await message.reply_text(
            f"{display_name}님 {minutes}분 추가 기록! "
            f"오늘 누적: {daily_total}분 (이미 인증 완료)",
        )
    else:
        remaining = MINUTES_THRESHOLD - daily_total
        await message.reply_text(
            f"{display_name}님 {minutes}분 기록! "
            f"오늘 누적: {daily_total}/{MINUTES_THRESHOLD}분 "
            f"(앞으로 {remaining}분 더!)",
        )
        logger.info(
            "Exercise log added: user=%s date=%s +%d min (total=%d)",
            telegram_id, exercise_date, minutes, daily_total,
        )
