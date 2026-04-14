from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))


def now_kst() -> datetime:
    return datetime.now(KST)


def today_kst() -> date:
    return now_kst().date()


def week_bounds(d: date) -> tuple[date, date]:
    """Return (monday, sunday) of the week containing *d*."""
    monday = d - timedelta(days=d.weekday())  # weekday(): Mon=0
    sunday = monday + timedelta(days=6)
    return monday, sunday


def week_number_in_quarter(d: date, quarter_start: date) -> int:
    """1-based week index since quarter_start (weeks run Mon-Sun)."""
    qs_monday, _ = week_bounds(quarter_start)
    d_monday, _ = week_bounds(d)
    diff = (d_monday - qs_monday).days
    return diff // 7 + 1


def month_name_en(month: int) -> str:
    names = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    return names[month]


def quarter_label(quarter_start: date) -> str:
    """e.g. 'Q2 2026'.

    Uses a date 14 days after quarter_start to determine the quarter number,
    so a quarter starting on March 30 is correctly labelled Q2 (not Q1).
    """
    ref = quarter_start + timedelta(days=14)
    month = ref.month
    if month <= 3:
        q = 1
    elif month <= 6:
        q = 2
    elif month <= 9:
        q = 3
    else:
        q = 4
    return f"Q{q} {ref.year}"


def season_emoji(month: int) -> str:
    emojis = {
        1: "\U0001f324",   # 🌤
        2: "\U0001f9da",   # 🧚
        3: "\U0001f33c",   # 🌼
        4: "\U0001f340",   # 🍀
        5: "\U0001f33b",   # 🌻
        6: "\u2600\ufe0f", # ☀️
        7: "\U0001f3d6",   # 🏖
        8: "\U0001f30a",   # 🌊
        9: "\U0001f342",   # 🍂
        10: "\U0001f43f",  # 🐿
        11: "\U0001f350",  # 🍐
        12: "\U0001f936",  # 🤶
    }
    return emojis.get(month, "\U0001f3cb")  # 🏋 fallback


MINUTES_THRESHOLD = 50


def parse_minutes(text: str | None) -> int | None:
    """Extract total exercise minutes from a caption string.

    Supported patterns:
      "30분"           → 30
      "1시간"          → 60
      "1시간 30분"     → 90
      "50"             → 50  (bare number, treated as minutes)
      "요가 20분 + 산책 15분" → 35  (multiple, summed)
      "크로스핏 1시간" → 60

    Returns None if no number is found.
    """
    if not text:
        return None

    total = 0
    found = False

    # Pattern: N시간 [M분]
    for m in re.finditer(r'(\d+)\s*시간(?:\s*(\d+)\s*분)?', text):
        hours = int(m.group(1))
        mins = int(m.group(2)) if m.group(2) else 0
        total += hours * 60 + mins
        found = True

    # Pattern: N분 (standalone, not already captured as part of 시간 M분)
    # Remove the 시간...분 matches first to avoid double-counting
    cleaned = re.sub(r'\d+\s*시간(?:\s*\d+\s*분)?', '', text)
    for m in re.finditer(r'(\d+)\s*분', cleaned):
        total += int(m.group(1))
        found = True

    # Fallback: bare number (only if nothing else matched)
    if not found:
        m = re.search(r'(\d+)', text)
        if m:
            total = int(m.group(1))
            found = True

    return total if found else None
