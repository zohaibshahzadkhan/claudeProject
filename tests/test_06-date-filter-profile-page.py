"""Tests for Step 6: date filter on GET /profile (see .claude/specs/06-date-filter-profile-page.md).

Seed data (from the spec / demo user): 8 expenses in the current month on days
3, 7, 9, 12, 15, 18, 22, 26 totalling 287.43. Descriptions are unique so they are
used to detect which transactions are listed.
"""
import re
from datetime import date

import pytest

import database.db as db

TODAY = date.today()
YEAR, MONTH = TODAY.year, TODAY.month

# day -> (category, amount, description)
SEED = {
    3: ("Food", 12.50, "Lunch at the cafe"),
    7: ("Food", 48.20, "Weekly groceries"),
    9: ("Transport", 25.00, "Monthly bus pass top-up"),
    12: ("Bills", 80.00, "Electricity bill"),
    15: ("Health", 35.75, "Pharmacy visit"),
    18: ("Entertainment", 15.00, "Movie tickets"),
    22: ("Shopping", 60.99, "New running shoes"),
    26: ("Other", 9.99, "Miscellaneous"),
}


def d(day):
    return date(YEAR, MONTH, day).isoformat()


def login_as(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


@pytest.fixture
def auth_client(client, seed_user_id):
    login_as(client, seed_user_id)
    return client


def get_profile(client, **params):
    return client.get("/profile", query_string=params)


def text(response):
    return response.get_data(as_text=True)


def listed(response, days):
    """Return (shown, hidden) assertions helper data: which seed days appear in the page."""
    body = text(response)
    return {day for day, (_, _, desc) in SEED.items() if desc in body}


def add_expense(user_id, amount, category, date_str, description):
    conn = db.get_db()
    try:
        with conn:
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, category, date_str, description),
            )
    finally:
        conn.close()


class TestAuthGuard:
    def test_profile_without_login_redirects_to_login(self, client):
        response = client.get("/profile")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_profile_with_filter_without_login_redirects_to_login(self, client):
        response = get_profile(client, start_date=d(1), end_date=d(28))
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


class TestNoFilter:
    def test_no_params_shows_all_time_total_and_all_transactions(self, auth_client):
        response = get_profile(auth_client)
        assert response.status_code == 200
        body = text(response)
        assert "287.43" in body, "Expected all-time total of 287.43"
        assert listed(response, None) == set(SEED), "All 8 seed expenses should be listed"

    def test_no_params_label_reads_all_time(self, auth_client):
        body = text(get_profile(auth_client))
        assert "All time" in body

    def test_no_params_inputs_not_prefilled(self, auth_client):
        body = text(get_profile(auth_client))
        # Check only the date inputs' value attributes, not the transaction table.
        assert not re.search(r'<input[^>]*type="date"[^>]*value="\d{4}-\d{2}-\d{2}"', body)
        assert f'value="{d(3)}"' not in body


class TestFilterForm:
    def test_form_has_two_date_inputs_with_expected_names(self, auth_client):
        body = text(get_profile(auth_client))
        assert re.search(r'<input[^>]*type="date"[^>]*name="start_date"|'
                         r'<input[^>]*name="start_date"[^>]*type="date"', body), \
            "Expected a date input named start_date"
        assert re.search(r'<input[^>]*type="date"[^>]*name="end_date"|'
                         r'<input[^>]*name="end_date"[^>]*type="date"', body), \
            "Expected a date input named end_date"

    def test_form_uses_get_method_and_posts_to_profile(self, auth_client):
        body = text(get_profile(auth_client))
        form = re.search(r"<form[^>]*>", body[body.find("start_date") - 600:], re.S)
        assert form is not None, "Expected a filter form"
        tag = form.group(0).lower()
        assert 'method="get"' in tag, "Filter form must use GET"
        assert "/profile" in tag, "Filter form must target the profile URL"

    def test_form_has_apply_button(self, auth_client):
        body = text(get_profile(auth_client))
        assert "Apply" in body

    def test_form_has_clear_link_to_profile(self, auth_client):
        # The Clear link is shown only while a filter is active.
        body = text(get_profile(auth_client, start_date=d(10)))
        assert re.search(r'<a[^>]*href="/profile"[^>]*>\s*Clear', body), \
            "Expected a Clear link pointing to /profile"

    def test_inputs_keep_chosen_values_after_filtering(self, auth_client):
        body = text(get_profile(auth_client, start_date=d(10), end_date=d(20)))
        assert f'value="{d(10)}"' in body, "start_date input should be pre-filled"
        assert f'value="{d(20)}"' in body, "end_date input should be pre-filled"

    def test_only_start_date_prefills_only_start_input(self, auth_client):
        body = text(get_profile(auth_client, start_date=d(10)))
        assert f'value="{d(10)}"' in body

    def test_clear_link_target_shows_all_time_data(self, auth_client):
        response = auth_client.get("/profile")
        assert "287.43" in text(response)
        assert "All time" in text(response)


class TestFiltering:
    def test_range_limits_stats_and_transactions(self, auth_client):
        response = get_profile(auth_client, start_date=d(10), end_date=d(20))
        assert response.status_code == 200
        body = text(response)
        assert listed(response, None) == {12, 15, 18}
        assert "130.75" in body, "Total for days 12, 15, 18 should be 130.75"
        assert "287.43" not in body

    def test_start_boundary_is_inclusive(self, auth_client):
        response = get_profile(auth_client, start_date=d(12), end_date=d(20))
        assert 12 in listed(response, None), "Expense on start_date must be included"

    def test_end_boundary_is_inclusive(self, auth_client):
        response = get_profile(auth_client, start_date=d(10), end_date=d(18))
        assert 18 in listed(response, None), "Expense on end_date must be included"

    def test_single_day_range_includes_only_that_day(self, auth_client):
        response = get_profile(auth_client, start_date=d(12), end_date=d(12))
        assert listed(response, None) == {12}
        assert "80.00" in text(response)

    def test_expenses_just_outside_boundaries_are_excluded(self, auth_client):
        response = get_profile(auth_client, start_date=d(13), end_date=d(17))
        assert listed(response, None) == {15}

    def test_only_start_date_is_open_ended_upward(self, auth_client):
        response = get_profile(auth_client, start_date=d(22))
        assert listed(response, None) == {22, 26}
        assert "70.98" in text(response)

    def test_only_end_date_is_open_ended_downward(self, auth_client):
        response = get_profile(auth_client, end_date=d(7))
        assert listed(response, None) == {3, 7}
        assert "60.70" in text(response)

    def test_wide_range_matches_all_time(self, auth_client):
        response = get_profile(
            auth_client, start_date=f"{YEAR - 1}-01-01", end_date=f"{YEAR + 1}-12-31"
        )
        assert listed(response, None) == set(SEED)
        assert "287.43" in text(response)

    def test_category_breakdown_is_filtered(self, auth_client):
        body = text(get_profile(auth_client, start_date=d(3), end_date=d(7)))
        assert "Food" in body
        for excluded in ("Transport", "Bills", "Health", "Entertainment", "Shopping"):
            assert excluded not in body, f"{excluded} should not appear in a Food-only range"

    def test_other_users_expenses_are_not_included(self, auth_client, empty_user_id):
        add_expense(empty_user_id, 999.0, "Food", d(12), "Someone elses purchase")
        body = text(get_profile(auth_client, start_date=d(10), end_date=d(20)))
        assert "Someone elses purchase" not in body
        assert "130.75" in body

    def test_filter_does_not_modify_database(self, auth_client):
        get_profile(auth_client, start_date=d(10), end_date=d(20))
        conn = db.get_db()
        try:
            count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        finally:
            conn.close()
        assert count == 8


class TestActiveRangeLabel:
    def test_label_shows_both_dates_when_filter_active(self, auth_client):
        start, end = date(YEAR, MONTH, 10), date(YEAR, MONTH, 20)
        body = text(get_profile(auth_client, start_date=start.isoformat(),
                                end_date=end.isoformat()))
        assert f"{start.isoformat()} to {end.isoformat()}" in body
        assert "All time" not in body

    def test_label_not_all_time_when_only_start_given(self, auth_client):
        start = date(YEAR, MONTH, 10)
        body = text(get_profile(auth_client, start_date=start.isoformat()))
        assert f"From {start.isoformat()}" in body
        assert "All time" not in body

    def test_label_not_all_time_when_only_end_given(self, auth_client):
        end = date(YEAR, MONTH, 10)
        body = text(get_profile(auth_client, end_date=end.isoformat()))
        assert f"Until {end.isoformat()}" in body
        assert "All time" not in body


class TestEmptyRange:
    @pytest.fixture
    def empty_range_body(self, auth_client):
        response = get_profile(
            auth_client, start_date=f"{YEAR - 5}-01-01", end_date=f"{YEAR - 5}-01-31"
        )
        assert response.status_code == 200
        return text(response)

    def test_empty_range_shows_zero_total(self, empty_range_body):
        assert "₹0.00" in empty_range_body

    def test_empty_range_shows_no_transactions_message(self, empty_range_body):
        assert "No transactions in this period" in empty_range_body

    def test_empty_range_shows_no_expenses_message(self, empty_range_body):
        assert "No expenses in this period" in empty_range_body

    def test_empty_range_lists_no_seed_transactions(self, empty_range_body):
        for _, _, desc in SEED.values():
            assert desc not in empty_range_body

    def test_user_with_no_expenses_and_active_filter_shows_period_messages(
        self, client, empty_user_id
    ):
        login_as(client, empty_user_id)
        body = text(get_profile(client, start_date=d(1), end_date=d(28)))
        assert "No transactions in this period" in body
        assert "No expenses in this period" in body


class TestValidation:
    @pytest.mark.parametrize(
        "params",
        [
            {"start_date": "not-a-date"},
            {"end_date": "not-a-date"},
            {"start_date": "2026-13-01"},
            {"start_date": "2026-02-30"},
            {"end_date": "2026-02-30"},
            {"start_date": "01/01/2026"},
            {"start_date": "2026-1-1x"},
            {"start_date": "20260101"},
            {"start_date": "2026-01-01", "end_date": "garbage"},
            {"start_date": "garbage", "end_date": "2026-01-31"},
            {"start_date": "2026-01-01'; DROP TABLE expenses;--"},
            {"end_date": "' OR '1'='1"},
        ],
    )
    def test_invalid_date_returns_400(self, auth_client, params):
        response = get_profile(auth_client, **params)
        assert response.status_code == 400, f"Expected 400 for {params}"

    def test_start_after_end_returns_400(self, auth_client):
        response = get_profile(auth_client, start_date="2026-02-01", end_date="2026-01-01")
        assert response.status_code == 400

    def test_start_equal_to_end_is_valid(self, auth_client):
        response = get_profile(auth_client, start_date=d(12), end_date=d(12))
        assert response.status_code == 200

    def test_sql_injection_attempt_does_not_drop_table(self, auth_client):
        get_profile(auth_client, start_date="2026-01-01'; DROP TABLE expenses;--")
        conn = db.get_db()
        try:
            count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        finally:
            conn.close()
        assert count == 8, "expenses table must be intact after injection attempt"

    def test_invalid_date_checked_for_logged_out_user_redirects(self, client):
        response = get_profile(client, start_date="not-a-date")
        assert response.status_code in (302, 400)
        if response.status_code == 302:
            assert "/login" in response.headers["Location"]


class TestCurrencyAndPercentages:
    def test_filtered_amounts_use_rupee_symbol(self, auth_client):
        body = text(get_profile(auth_client, start_date=d(10), end_date=d(20)))
        assert "₹" in body
        assert "£" not in body
        assert "$" not in body

    def test_empty_range_uses_rupee_symbol(self, auth_client):
        body = text(get_profile(auth_client, start_date=f"{YEAR - 5}-01-01",
                                end_date=f"{YEAR - 5}-01-31"))
        assert "₹0.00" in body
        assert "£" not in body

    @pytest.mark.parametrize(
        "start,end",
        [(None, None), (3, 15), (7, 26), (12, 22), (3, 3)],
    )
    def test_breakdown_pct_sums_to_100_for_filtered_set(
        self, test_db, seed_user_id, start, end
    ):
        start_date = d(start) if start else None
        end_date = d(end) if end else None
        rows = db.get_category_breakdown(
            seed_user_id, start_date=start_date, end_date=end_date
        )
        assert rows, "Expected at least one category in range"
        assert sum(r["pct"] for r in rows) == 100


class TestDbHelpers:
    def test_helpers_default_to_all_time(self, test_db, seed_user_id):
        assert len(db.get_recent_transactions(seed_user_id)) == 8
        assert len(db.get_category_breakdown(seed_user_id)) == 7

    def test_helpers_accept_none_explicitly(self, test_db, seed_user_id):
        assert len(db.get_recent_transactions(
            seed_user_id, start_date=None, end_date=None)) == 8

    def test_recent_transactions_filtered_by_range(self, test_db, seed_user_id):
        rows = db.get_recent_transactions(
            seed_user_id, start_date=d(10), end_date=d(20)
        )
        assert len(rows) == 3

    def test_recent_transactions_inclusive_bounds(self, test_db, seed_user_id):
        rows = db.get_recent_transactions(
            seed_user_id, start_date=d(12), end_date=d(12)
        )
        assert len(rows) == 1

    def test_recent_transactions_open_ended(self, test_db, seed_user_id):
        assert len(db.get_recent_transactions(seed_user_id, start_date=d(22))) == 2
        assert len(db.get_recent_transactions(seed_user_id, end_date=d(7))) == 2

    def test_category_breakdown_filtered_by_range(self, test_db, seed_user_id):
        rows = db.get_category_breakdown(
            seed_user_id, start_date=d(3), end_date=d(7)
        )
        assert len(rows) == 1, "Only Food falls in days 3-7"

    def test_helpers_return_empty_for_range_with_no_expenses(self, test_db, seed_user_id):
        start, end = f"{YEAR - 5}-01-01", f"{YEAR - 5}-01-31"
        assert db.get_recent_transactions(seed_user_id, start_date=start, end_date=end) == []
        assert db.get_category_breakdown(seed_user_id, start_date=start, end_date=end) == []
