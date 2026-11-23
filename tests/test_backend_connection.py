import re
from datetime import datetime

import database.db as db

SEED_TOTAL = 287.43
SEED_COUNT = 8
SEED_CATEGORIES = {"Bills", "Shopping", "Food", "Health", "Transport", "Entertainment", "Other"}


def login(client, email, password):
    return client.post("/login", data={"email": email, "password": password})


# ------------------------------------------------------------------ #
# Unit tests: database/db.py helpers                                  #
# ------------------------------------------------------------------ #

def test_get_user_by_id_returns_user_fields(test_db, seed_user_id):
    user = db.get_user_by_id(seed_user_id)

    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert user["initials"] == "DU"
    assert re.fullmatch(r"[A-Z][a-z]+ \d{4}", user["member_since"])


def test_get_user_by_id_member_since_matches_created_at(test_db, seed_user_id):
    conn = db.get_db()
    try:
        created_at = conn.execute(
            "SELECT created_at FROM users WHERE id = ?", (seed_user_id,)
        ).fetchone()["created_at"]
    finally:
        conn.close()

    expected = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S").strftime("%B %Y")
    assert db.get_user_by_id(seed_user_id)["member_since"] == expected


def test_get_user_by_id_single_word_name_initials(test_db):
    user_id = db.create_user("Madonna", "mono@example.com", "hash")
    assert db.get_user_by_id(user_id)["initials"] == "M"


def test_get_user_by_id_missing_returns_none(test_db):
    assert db.get_user_by_id(999999) is None


def test_get_summary_stats_with_expenses(test_db, seed_user_id):
    stats = db.get_summary_stats(seed_user_id)

    assert stats["total_spent"] == SEED_TOTAL
    assert stats["transaction_count"] == SEED_COUNT
    assert stats["top_category"] == "Bills"
    assert stats["avg_per_transaction"] == round(SEED_TOTAL / SEED_COUNT, 2)


def test_get_summary_stats_without_expenses(test_db, empty_user_id):
    stats = db.get_summary_stats(empty_user_id)

    assert stats["total_spent"] == 0
    assert stats["transaction_count"] == 0
    assert stats["top_category"] == "—"
    assert stats["avg_per_transaction"] == 0


def test_get_recent_transactions_newest_first(test_db, seed_user_id):
    rows = db.get_recent_transactions(seed_user_id)

    assert len(rows) == SEED_COUNT
    dates = [row["date"] for row in rows]
    assert dates == sorted(dates, reverse=True)
    for row in rows:
        assert set(row.keys()) == {"id", "date", "description", "category", "amount"}


def test_get_recent_transactions_respects_limit(test_db, seed_user_id):
    assert len(db.get_recent_transactions(seed_user_id, limit=3)) == 3


def test_get_recent_transactions_without_expenses(test_db, empty_user_id):
    assert db.get_recent_transactions(empty_user_id) == []


def test_get_category_breakdown_ordered_and_pct_sums_to_100(test_db, seed_user_id):
    breakdown = db.get_category_breakdown(seed_user_id)

    assert {item["name"] for item in breakdown} == SEED_CATEGORIES
    amounts = [item["amount"] for item in breakdown]
    assert amounts == sorted(amounts, reverse=True)
    assert all(isinstance(item["pct"], int) for item in breakdown)
    assert sum(item["pct"] for item in breakdown) == 100


def test_get_category_breakdown_rounding_remainder_goes_to_largest(test_db, empty_user_id):
    # Three equal categories: 33 + 33 + 33 = 99, so the remainder must land on the first row.
    conn = db.get_db()
    try:
        with conn:
            conn.executemany(
                "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
                [
                    (empty_user_id, 10.0, "Food", "2026-01-01"),
                    (empty_user_id, 10.0, "Bills", "2026-01-02"),
                    (empty_user_id, 10.0, "Health", "2026-01-03"),
                ],
            )
    finally:
        conn.close()

    breakdown = db.get_category_breakdown(empty_user_id)
    pcts = [item["pct"] for item in breakdown]
    assert sum(pcts) == 100
    assert pcts[0] == 34
    assert pcts[1:] == [33, 33]


def test_get_category_breakdown_without_expenses(test_db, empty_user_id):
    assert db.get_category_breakdown(empty_user_id) == []


# ------------------------------------------------------------------ #
# Route tests: GET /profile                                           #
# ------------------------------------------------------------------ #

def test_profile_redirects_when_logged_out(client):
    response = client.get("/profile")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_profile_shows_seed_user_data(client):
    login(client, "demo@spendly.com", "demo123")
    response = client.get("/profile")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Demo User" in html
    assert "demo@spendly.com" in html
    assert "₹" in html
    assert "₹287.43" in html
    assert "Bills" in html
    assert html.count('class="profile-category"') == 7


def test_profile_transactions_listed_newest_first(client):
    login(client, "demo@spendly.com", "demo123")
    html = client.get("/profile").get_data(as_text=True)

    # Day 26 ("Miscellaneous") is the newest seeded expense; day 3 ("Lunch at the cafe") the oldest.
    assert html.index("Miscellaneous") < html.index("Lunch at the cafe")


def test_profile_empty_state_for_new_user(client, empty_user_id):
    login(client, "new@example.com", "password123")
    response = client.get("/profile")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "New Person" in html
    assert "₹0.00" in html
    assert "No transactions yet" in html
    assert "No expenses yet" in html


def test_profile_only_shows_own_expenses(client, empty_user_id):
    login(client, "new@example.com", "password123")
    html = client.get("/profile").get_data(as_text=True)

    assert "Demo User" not in html
    assert "Miscellaneous" not in html


def test_profile_missing_user_clears_session_and_redirects(client, seed_user_id, test_db):
    login(client, "demo@spendly.com", "demo123")

    conn = db.get_db()
    try:
        with conn:
            conn.execute("DELETE FROM expenses WHERE user_id = ?", (seed_user_id,))
            conn.execute("DELETE FROM users WHERE id = ?", (seed_user_id,))
    finally:
        conn.close()

    response = client.get("/profile")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    with client.session_transaction() as sess:
        assert "user_id" not in sess
