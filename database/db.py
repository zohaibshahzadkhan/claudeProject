import sqlite3
from datetime import date
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
