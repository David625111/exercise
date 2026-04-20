import logging
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from bot import database as db
from bot.config import ADMIN_IDS, GROUP_CHAT_ID
from bot.handlers.status import build_weekly_report

logger = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def _parse_target_and_date(
    args: list[str],
) -> tuple[str | None, date | None, str | None]:
    """Parse command args: @username YYYY-MM-DD [note].

    Returns (username, exercise_date, error_message).
    """
    if len(args) < 2:
        return None, None, "사용법: /수동인증 @username YYYY-MM-DD [메모]"

    username = args[0]
    if not username.startswith("@"):
        return None, None, "첫 번째 인자는 @username 형식이어야 합니다."

    try:
        exercise_date = date.fromisoformat(args[1])
    except ValueError:
        return None, None, "날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요."

    return username, exercise_date, None


async def add_log_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """/수동인증 @username YYYY-MM-DD [메모]  or  /addlog"""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None:
        return
    if chat.id != GROUP_CHAT_ID:
        return

    if not _is_admin(user.id):
        await message.reply_text("관리자만 사용할 수 있는 명령어입니다.")
        return

    username, exercise_date, err = _parse_target_and_date(context.args or [])
    if err:
        await message.reply_text(err)
        return

    member = db.get_member_by_username(username)
    if member is None:
        await message.reply_text(
            f"{username} 사용자를 찾을 수 없습니다.\n"
            "해당 사용자가 먼저 그룹에서 메시지를 보내야 등록됩니다.",
        )
        return

    note_parts = (context.args or [])[2:]
    note = " ".join(note_parts) if note_parts else "수동 인증"

    success = db.add_verification(
        telegram_id=member["telegram_id"],
        exercise_date=exercise_date,
        photo_file_id=None,
        is_manual=True,
        note=note,
    )

    if success:
        await message.reply_text(
            f"{member['display_name']}님의 {exercise_date} 운동 기록이 추가되었습니다.",
        )
        logger.info(
            "Manual verification added: user=%s date=%s by admin=%s",
            member["telegram_id"],
            exercise_date,
            user.id,
        )
    else:
        await message.reply_text(
            f"{member['display_name']}님의 {exercise_date} 기록이 이미 존재합니다.",
        )


async def del_log_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """/수동인증삭제 @username YYYY-MM-DD  or  /dellog"""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None:
        return
    if chat.id != GROUP_CHAT_ID:
        return

    if not _is_admin(user.id):
        await message.reply_text("관리자만 사용할 수 있는 명령어입니다.")
        return

    args = context.args or []
    if len(args) < 2:
        await message.reply_text("사용법: /수동인증삭제 @username YYYY-MM-DD")
        return

    username = args[0]
    if not username.startswith("@"):
        await message.reply_text("첫 번째 인자는 @username 형식이어야 합니다.")
        return

    try:
        exercise_date = date.fromisoformat(args[1])
    except ValueError:
        await message.reply_text("날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요.")
        return

    member = db.get_member_by_username(username)
    if member is None:
        await message.reply_text(f"{username} 사용자를 찾을 수 없습니다.")
        return

    deleted = db.delete_verification(member["telegram_id"], exercise_date)
    if deleted:
        await message.reply_text(
            f"{member['display_name']}님의 {exercise_date} 기록이 삭제되었습니다.",
        )
        logger.info(
            "Verification deleted: user=%s date=%s by admin=%s",
            member["telegram_id"],
            exercise_date,
            user.id,
        )
    else:
        await message.reply_text(
            f"{member['display_name']}님의 {exercise_date} 기록이 존재하지 않습니다.",
        )


async def set_quarter_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """/분기설정 YYYY-MM-DD  or  /setquarter"""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None:
        return
    if chat.id != GROUP_CHAT_ID:
        return

    if not _is_admin(user.id):
        await message.reply_text("관리자만 사용할 수 있는 명령어입니다.")
        return

    args = context.args or []
    if len(args) != 1:
        await message.reply_text("사용법: /분기설정 YYYY-MM-DD (예: /분기설정 2026-06-29)")
        return

    try:
        new_start = date.fromisoformat(args[0])
    except ValueError:
        await message.reply_text("날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요.")
        return

    db.set_quarter_start(new_start)
    await message.reply_text(
        f"분기 시작일이 {new_start}(으)로 설정되었습니다.\n"
        f"모든 팀원은 /목표설정 N 으로 새 분기 목표를 설정해주세요!",
    )
    logger.info("Quarter start updated to %s by admin=%s", new_start, user.id)


async def report_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """/리포트 or /report — generate weekly report now."""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None:
        return
    if chat.id != GROUP_CHAT_ID:
        return

    if not _is_admin(user.id):
        await message.reply_text("관리자만 사용할 수 있는 명령어입니다.")
        return

    report = build_weekly_report()
    await message.reply_text(report)


async def bulk_score_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """/bulkscore @user1 N1 @user2 N2 ... — set manual score adjustments."""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None:
        return
    if chat.id != GROUP_CHAT_ID:
        return

    if not _is_admin(user.id):
        await message.reply_text("관리자만 사용할 수 있는 명령어입니다.")
        return

    args = context.args or []
    if not args or len(args) % 2 != 0:
        await message.reply_text(
            "사용법: /bulkscore @user1 N @user2 N ...\n"
            "예: /bulkscore @robin 2 @kaido 2 @gemma 2\n"
            "• N은 정수 (음수 가능). 현재 분기의 수동 조정값을 덮어씁니다.",
        )
        return

    updates: list[tuple[dict, int]] = []
    errors: list[str] = []
    for i in range(0, len(args), 2):
        username, val = args[i], args[i + 1]
        if not username.startswith("@"):
            errors.append(f"'{username}'는 @username 형식이 아닙니다.")
            continue
        try:
            adjustment = int(val)
        except ValueError:
            errors.append(f"'{val}'는 정수가 아닙니다.")
            continue
        member = db.get_member_by_username(username)
        if member is None:
            errors.append(f"{username} 사용자를 찾을 수 없습니다.")
            continue
        updates.append((member, adjustment))

    if errors:
        await message.reply_text(
            "아래 오류로 인해 아무 것도 적용되지 않았습니다:\n" + "\n".join(errors),
        )
        return

    quarter_start = db.get_quarter_start()
    lines = [f"분기({quarter_start}) 점수 조정이 적용되었습니다:"]
    for member, adj in updates:
        db.set_score_adjustment(member["telegram_id"], quarter_start, adj)
        sign = "+" if adj >= 0 else ""
        lines.append(f"  {member['display_name']}: {sign}{adj}")
        logger.info(
            "Score adjustment set: user=%s quarter=%s adj=%s by admin=%s",
            member["telegram_id"],
            quarter_start,
            adj,
            user.id,
        )
    await message.reply_text("\n".join(lines))


async def register_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """/등록 — register yourself as a member (any user)."""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None:
        return
    if chat.id != GROUP_CHAT_ID:
        return

    db.upsert_member(user.id, user.username, user.full_name)
    await message.reply_text(
        f"{user.full_name}님이 등록되었습니다.\n"
        f"/목표설정 N 으로 이번 분기 주간 목표를 설정해주세요!",
    )
