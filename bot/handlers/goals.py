from telegram import Update
from telegram.ext import ContextTypes

from bot import database as db
from bot.config import GROUP_CHAT_ID


async def set_goal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/목표설정 N  or  /setgoal N"""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None:
        return
    if chat.id != GROUP_CHAT_ID:
        return

    if not context.args or len(context.args) != 1:
        await message.reply_text("사용법: /목표설정 N (예: /목표설정 3)")
        return

    try:
        target = int(context.args[0])
    except ValueError:
        await message.reply_text("숫자를 입력해주세요. (예: /목표설정 3)")
        return

    if not 1 <= target <= 7:
        await message.reply_text("주간 목표는 1~7 사이여야 합니다.")
        return

    telegram_id = user.id
    display_name = user.full_name
    username = user.username

    db.upsert_member(telegram_id, username, display_name)

    quarter_start = db.get_quarter_start()
    old_goal = db.get_goal(telegram_id, quarter_start)

    db.set_goal(telegram_id, quarter_start, target)

    if old_goal is None:
        await message.reply_text(
            f"{display_name}님의 이번 분기 주간 목표가 주 {target}회로 설정되었습니다!",
        )
    else:
        await message.reply_text(
            f"{display_name}님의 이번 분기 주간 목표가 주 {old_goal}회 → 주 {target}회로 변경되었습니다.",
        )


async def my_goal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/내목표  or  /mygoal"""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None:
        return
    if chat.id != GROUP_CHAT_ID:
        return

    quarter_start = db.get_quarter_start()
    goal = db.get_goal(user.id, quarter_start)

    if goal is None:
        await message.reply_text(
            "이번 분기 목표가 아직 설정되지 않았습니다.\n"
            "/목표설정 N 으로 설정해주세요!",
        )
    else:
        await message.reply_text(
            f"{user.full_name}님의 이번 분기 주간 목표: 주 {goal}회",
        )
