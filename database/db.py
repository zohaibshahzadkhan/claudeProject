import sqlite3
from datetime import date, datetime
from pathlib import Path

from werkzeug.security import generate_password_hash

DB_PATH = Path(__file__).resolve().parent.parent / "spendly.db"


def get_db():
    """Return a SQLite connection with dict-like rows and foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the users and expenses tables if they do not already exist."""
    conn = get_db()
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    date TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
                """
            )
    finally:
        conn.close()


def seed_db():
    """Insert a demo user and 8 sample expenses, only if the users table is empty."""
    conn = get_db()
    try:
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count > 0:
            return

        today = date.today()
        year, month = today.year, today.month

        # Days 1-28 are valid in every month, so no month-length checks are needed.
        sample_expenses = [
            (3, "Food", 12.50, "Lunch at the cafe"),
            (7, "Food", 48.20, "Weekly groceries"),
            (9, "Transport", 25.00, "Monthly bus pass top-up"),
            (12, "Bills", 80.00, "Electricity bill"),
            (15, "Health", 35.75, "Pharmacy visit"),
            (18, "Entertainment", 15.00, "Movie tickets"),
            (22, "Shopping", 60.99, "New running shoes"),
            (26, "Other", 9.99, "Miscellaneous"),
        ]

        password_hash = generate_password_hash("demo123")

        with conn:
            cursor = conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("Demo User", "demo@spendly.com", password_hash),
            )
            user_id = cursor.lastrowid

            conn.executemany(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        user_id,
                        amount,
                        category,
                        date(year, month, day).isoformat(),
                        description,
                    )
                    for day, category, amount, description in sample_expenses
                ],
            )
    finally:
        conn.close()


def get_user_by_email(email):
    """Return the user row with this email, or None if no user matches."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()


def create_user(name, email, password_hash):
    """Insert a new user and return its id. Raises sqlite3.IntegrityError on duplicate email."""
    conn = get_db()
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, password_hash),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def get_user_by_id(user_id):
    """Return name, email, initials and member_since for this user, or None if missing."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    parts = row["name"].split()
    if len(parts) > 1:
        initials = (parts[0][0] + parts[-1][0]).upper()
    else:
        initials = parts[0][0].upper() if parts else ""

    created = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
    return {
        "name": row["name"],
        "email": row["email"],
        "initials": initials,
        "member_since": created.strftime("%B %Y"),
    }


def get_summary_stats(user_id):
    """Return total_spent, transaction_count, top_category and avg_per_transaction for a user."""
    conn = get_db()
    try:
        totals = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count
            FROM expenses WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        top = conn.execute(
            """
            SELECT category FROM expenses WHERE user_id = ?
            GROUP BY category ORDER BY SUM(amount) DESC, category ASC LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    count = totals["count"]
    total = round(totals["total"], 2)
    return {
        "total_spent": total,
        "transaction_count": count,
        "top_category": top["category"] if top else "—",
        "avg_per_transaction": round(total / count, 2) if count else 0,
    }


def get_recent_transactions(user_id, limit=10):
    """Return up to `limit` expenses for a user, newest first."""
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT date, description, category, amount FROM expenses
            WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def get_category_breakdown(user_id):
    """Return per-category name, amount and integer pct (summing to 100), largest first."""
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT category AS name, SUM(amount) AS amount FROM expenses
            WHERE user_id = ? GROUP BY category ORDER BY amount DESC, name ASC
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    grand_total = sum(row["amount"] for row in rows)
    if not rows or grand_total <= 0:
        return []

    breakdown = [
        {
            "name": row["name"],
            "amount": round(row["amount"], 2),
            "pct": round(row["amount"] * 100 / grand_total),
        }
        for row in rows
    ]
    # Give the rounding remainder to the largest category so pct sums to exactly 100.
    remainder = 100 - sum(item["pct"] for item in breakdown)
    breakdown[0]["pct"] += remainder
    return breakdown
