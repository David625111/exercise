from datetime import date, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from bot import database as db
from bot.config import GROUP_CHAT_ID
from bot.utils import (
    month_name_en,
    quarter_label,
    season_emoji,
    today_kst,
    week_bounds,
    week_number_in_quarter,
)


def _compute_quarter_scores(
    quarter_start: date, up_to: date
) -> dict[int, tuple[int, int]]:
    """Compute cumulative quarter scores for all members.

    Returns {telegram_id: (total_score, gained_this_week)} where
    gained_this_week is 1 if the member scored in the most recent completed
    week (used for the ⬆️ indicator), 0 otherwise.

    Only fully elapsed weeks (Monday-Sunday where Sunday <= up_to) are counted.
    """
    members = db.get_all_members()
    goals = db.get_all_goals(quarter_start)

    qs_monday, _ = week_bounds(quarter_start)

    results: dict[int, tuple[int, int]] = {}

    for member in members:
        tid = member["telegram_id"]
        target = goals.get(tid)
        if target is None:
            results[tid] = (0, 0)
            continue

        # Collect completed weeks in chronological order
        completed_weeks: list[tuple[date, date]] = []
        ws = qs_monday
        while True:
            we = ws + timedelta(days=6)
            if we > up_to:
                break
            completed_weeks.append((ws, we))
            ws += timedelta(days=7)

        total_score = 0
        last_week_gained = 0
        for i, (ws, we) in enumerate(completed_weeks):
            count = db.count_verifications_range(tid, ws, we)
            if count >= target:
                total_score += 1
                if i == len(completed_weeks) - 1:
                    last_week_gained = 1

        results[tid] = (total_score, last_week_gained)

    return results


def build_weekly_report(report_date: date | None = None) -> str:
    """Build the weekly score report string in the team's traditional format."""
    if report_date is None:
        report_date = today_kst()

    quarter_start = db.get_quarter_start()
    scores = _compute_quarter_scores(quarter_start, report_date)

    members = db.get_all_members()
    goals = db.get_all_goals(quarter_start)

    week_num = week_number_in_quarter(report_date, quarter_start)
    emoji = season_emoji(report_date.month)
    month_name = month_name_en(report_date.month)

    q_label = quarter_label(quarter_start)
    is_q_start = week_num <= 1
    # Check if this is potentially Q end (we don't know next quarter start, so skip auto-detect)

    header = f"{emoji} {month_name} Week {week_num} Scores"
    if is_q_start:
        header += f" ({q_label} Start)"

    # Sort by score descending, then by display_name
    ranked = sorted(
        members,
        key=lambda m: (-scores.get(m["telegram_id"], (0, 0))[0], m["display_name"]),
    )

    lines = [header, ""]
    for member in ranked:
        tid = member["telegram_id"]
        total, gained = scores.get(tid, (0, 0))
        name = member["display_name"]

        if tid not in goals:
            lines.append(f"{name} - (목표 미설정)")
            continue

        indicator = ""
        if gained > 0:
            indicator = " \u2b06\ufe0f"  # ⬆️

        lines.append(f"{name} +{total}{indicator}")

    return "\n".join(lines)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/status or /현황 — personal status for the current week and quarter."""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None:
        return
    if chat.id != GROUP_CHAT_ID:
        return

    tid = user.id
    display_name = user.full_name
    d = today_kst()
    quarter_start = db.get_quarter_start()

    goal = db.get_goal(tid, quarter_start)
    if goal is None:
        await message.reply_text(
            f"{display_name}님, 이번 분기 목표가 설정되지 않았습니다.\n"
            "/목표설정 N 으로 설정해주세요!",
        )
        return

    monday, sunday = week_bounds(d)
    week_count = db.count_verifications_range(tid, monday, sunday)
    week_logs = db.get_verifications_range(tid, monday, sunday)
    logged_dates = [v["exercise_date"] for v in week_logs]

    scores = _compute_quarter_scores(quarter_start, d)
    total_score = scores.get(tid, (0, 0))[0]

    lines = [
        f"[{display_name}] 이번 주 현황",
        f"주간 목표: {week_count}/{goal}회",
        f"인증 날짜: {', '.join(logged_dates) if logged_dates else '없음'}",
        "",
        f"분기 누적 점수: +{total_score}",
    ]

    await message.reply_text("\n".join(lines))


async def weekly_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/주간 or /weekly — this week's verification status for all members."""
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    if chat.id != GROUP_CHAT_ID:
        return

    d = today_kst()
    monday, sunday = week_bounds(d)
    quarter_start = db.get_quarter_start()
    goals = db.get_all_goals(quarter_start)
    members = db.get_all_members()

    lines = [f"이번 주 인증 현황 ({monday} ~ {sunday})", ""]

    for member in sorted(members, key=lambda m: m["display_name"]):
        tid = member["telegram_id"]
        name = member["display_name"]
        target = goals.get(tid)
        count = db.count_verifications_range(tid, monday, sunday)

        if target is None:
            lines.append(f"{name}: {count}회 (목표 미설정)")
        else:
            check = "\u2705" if count >= target else ""  # ✅
            lines.append(f"{name}: {count}/{target}회 {check}")

    await message.reply_text("\n".join(lines))


async def score_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/점수 or /score — quarter ranking."""
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    if chat.id != GROUP_CHAT_ID:
        return

    report = build_weekly_report()
    await message.reply_text(report)
