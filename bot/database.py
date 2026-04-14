import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any

from bot.config import DATABASE_PATH

_DB_PATH = DATABASE_PATH

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS members (
    telegram_id  INTEGER PRIMARY KEY,
    username     TEXT,
    display_name TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS quarter_goals (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id   INTEGER NOT NULL REFERENCES members(telegram_id),
    quarter_start TEXT    NOT NULL,  -- ISO date 'YYYY-MM-DD'
    weekly_target INTEGER NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(telegram_id, quarter_start)
);

CREATE TABLE IF NOT EXISTS verifications (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id   INTEGER NOT NULL REFERENCES members(telegram_id),
    exercise_date TEXT    NOT NULL,  -- ISO date 'YYYY-MM-DD'
    verified_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    photo_file_id TEXT,
    is_manual     INTEGER NOT NULL DEFAULT 0,
    note          TEXT,
    UNIQUE(telegram_id, exercise_date)
);

CREATE TABLE IF NOT EXISTS quarter_config (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    quarter_start TEXT NOT NULL  -- ISO date 'YYYY-MM-DD'
);
"""


def init_db() -> None:
    Path(_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.executescript(_SCHEMA)
        # Seed default quarter start if not exists
        row = conn.execute("SELECT quarter_start FROM quarter_config WHERE id = 1").fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO quarter_config (id, quarter_start) VALUES (1, ?)",
                ("2026-03-30",),
            )


@contextmanager
def _connect():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ── quarter config ──────────────────────────────────────────────

def get_quarter_start() -> date:
    with _connect() as conn:
        row = conn.execute("SELECT quarter_start FROM quarter_config WHERE id = 1").fetchone()
        return date.fromisoformat(row["quarter_start"])


def set_quarter_start(d: date) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO quarter_config (id, quarter_start) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET quarter_start = excluded.quarter_start",
            (d.isoformat(),),
        )


# ── members ─────────────────────────────────────────────────────

def upsert_member(telegram_id: int, username: str | None, display_name: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO members (telegram_id, username, display_name) VALUES (?, ?, ?) "
            "ON CONFLICT(telegram_id) DO UPDATE SET username = excluded.username, "
            "display_name = excluded.display_name",
            (telegram_id, username, display_name),
        )


def get_member(telegram_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM members WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        return dict(row) if row else None


def get_member_by_username(username: str) -> dict[str, Any] | None:
    clean = username.lstrip("@")
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM members WHERE username = ? COLLATE NOCASE", (clean,)
        ).fetchone()
        return dict(row) if row else None


def get_all_members() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM members ORDER BY display_name"
        ).fetchall()
        return [dict(r) for r in rows]


# ── quarter goals ───────────────────────────────────────────────

def set_goal(telegram_id: int, quarter_start: date, weekly_target: int) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO quarter_goals (telegram_id, quarter_start, weekly_target) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(telegram_id, quarter_start) DO UPDATE SET weekly_target = excluded.weekly_target",
            (telegram_id, quarter_start.isoformat(), weekly_target),
        )


def get_goal(telegram_id: int, quarter_start: date) -> int | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT weekly_target FROM quarter_goals "
            "WHERE telegram_id = ? AND quarter_start = ?",
            (telegram_id, quarter_start.isoformat()),
        ).fetchone()
        return row["weekly_target"] if row else None


def get_all_goals(quarter_start: date) -> dict[int, int]:
    """Return {telegram_id: weekly_target} for a quarter."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT telegram_id, weekly_target FROM quarter_goals WHERE quarter_start = ?",
            (quarter_start.isoformat(),),
        ).fetchall()
        return {r["telegram_id"]: r["weekly_target"] for r in rows}


# ── verifications ───────────────────────────────────────────────

def add_verification(
    telegram_id: int,
    exercise_date: date,
    photo_file_id: str | None = None,
    is_manual: bool = False,
    note: str | None = None,
) -> bool:
    """Insert a verification. Returns True on success, False if duplicate."""
    with _connect() as conn:
        try:
            conn.execute(
                "INSERT INTO verifications (telegram_id, exercise_date, photo_file_id, is_manual, note) "
                "VALUES (?, ?, ?, ?, ?)",
                (telegram_id, exercise_date.isoformat(), photo_file_id, int(is_manual), note),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def delete_verification(telegram_id: int, exercise_date: date) -> bool:
    """Delete a verification. Returns True if a row was deleted."""
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM verifications WHERE telegram_id = ? AND exercise_date = ?",
            (telegram_id, exercise_date.isoformat()),
        )
        return cur.rowcount > 0


def get_verifications_range(
    telegram_id: int, start: date, end: date
) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM verifications "
            "WHERE telegram_id = ? AND exercise_date BETWEEN ? AND ? "
            "ORDER BY exercise_date",
            (telegram_id, start.isoformat(), end.isoformat()),
        ).fetchall()
        return [dict(r) for r in rows]


def count_verifications_range(telegram_id: int, start: date, end: date) -> int:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM verifications "
            "WHERE telegram_id = ? AND exercise_date BETWEEN ? AND ?",
            (telegram_id, start.isoformat(), end.isoformat()),
        ).fetchone()
        return row["cnt"]


def get_daily_verifications(exercise_date: date) -> list[dict[str, Any]]:
    """All verifications for a specific date, joined with member info."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT v.*, m.display_name, m.username "
            "FROM verifications v "
            "JOIN members m ON v.telegram_id = m.telegram_id "
            "WHERE v.exercise_date = ? "
            "ORDER BY m.display_name",
            (exercise_date.isoformat(),),
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_verifications_range(start: date, end: date) -> list[dict[str, Any]]:
    """All verifications in a date range, joined with member info."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT v.*, m.display_name, m.username "
            "FROM verifications v "
            "JOIN members m ON v.telegram_id = m.telegram_id "
            "WHERE v.exercise_date BETWEEN ? AND ? "
            "ORDER BY v.exercise_date, m.display_name",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [dict(r) for r in rows]
