import pytest

import database.db as db


VALID_FORM = {
    "amount": "75.5",
    "category": "Bills",
    "date": "2026-03-21",
    "description": "Power",
}


def _insert(user_id, amount=25.0, category="Food", date_str="2026-03-10", description="Lunch"):
    return db.insert_expense(user_id, amount, category, date_str, description)


def _row(expense_id):
    conn = db.get_db()
    try:
        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


# ------------------------------------------------------------------ #
# Unit tests: db helpers                                              #
# ------------------------------------------------------------------ #

def test_get_expense_by_id_returns_owned_expense(seed_user_id):
    expense_id = _insert(seed_user_id)
    expense = db.get_expense_by_id(expense_id, seed_user_id)
    assert expense["id"] == expense_id
    assert expense["amount"] == 25.0
    assert expense["category"] == "Food"
    assert expense["date"] == "2026-03-10"
    assert expense["description"] == "Lunch"


def test_get_expense_by_id_wrong_user_returns_none(seed_user_id, empty_user_id):
    expense_id = _insert(seed_user_id)
    assert db.get_expense_by_id(expense_id, empty_user_id) is None


def test_get_expense_by_id_missing_returns_none(seed_user_id):
    assert db.get_expense_by_id(999_999, seed_user_id) is None


def test_update_expense_updates_owned_row(seed_user_id):
    expense_id = _insert(seed_user_id)
    changed = db.update_expense(expense_id, seed_user_id, 99.0, "Health", "2026-04-01", "Checkup")
    assert changed is True
    row = _row(expense_id)
    assert row["amount"] == 99.0
    assert row["category"] == "Health"
    assert row["date"] == "2026-04-01"
    assert row["description"] == "Checkup"


def test_update_expense_stores_null_description(seed_user_id):
    expense_id = _insert(seed_user_id)
    db.update_expense(expense_id, seed_user_id, 10.0, "Food", "2026-03-10", None)
    assert _row(expense_id)["description"] is None


def test_update_expense_wrong_user_changes_nothing(seed_user_id, empty_user_id):
    expense_id = _insert(seed_user_id, amount=25.0)
    changed = db.update_expense(expense_id, empty_user_id, 99.0, "Health", "2026-04-01", "Hijack")
    assert changed is False
    row = _row(expense_id)
    assert row["amount"] == 25.0
    assert row["description"] == "Lunch"


# ------------------------------------------------------------------ #
# Route tests: GET                                                    #
# ------------------------------------------------------------------ #

def test_get_edit_unauthenticated_redirects_to_login(client, seed_user_id):
    expense_id = _insert(seed_user_id)
    response = client.get(f"/expenses/{expense_id}/edit")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_get_edit_own_expense_prefills_form(auth_client, seed_user_id):
    expense_id = _insert(seed_user_id, amount=25.0, category="Bills",
                         date_str="2026-03-10", description="Lunch")
    response = auth_client.get(f"/expenses/{expense_id}/edit")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert '<form' in html and 'method="POST"' in html
    assert f'action="/expenses/{expense_id}/edit"' in html
    assert 'value="25.0"' in html
    assert 'value="2026-03-10"' in html
    assert 'value="Lunch"' in html
    assert 'value="Bills" selected' in html


def test_get_edit_other_users_expense_returns_404(auth_client, empty_user_id):
    expense_id = _insert(empty_user_id)
    assert auth_client.get(f"/expenses/{expense_id}/edit").status_code == 404


def test_get_edit_missing_expense_returns_404(auth_client):
    assert auth_client.get("/expenses/999999/edit").status_code == 404


# ------------------------------------------------------------------ #
# Route tests: POST                                                   #
# ------------------------------------------------------------------ #

def test_post_edit_unauthenticated_redirects_and_changes_nothing(client, seed_user_id):
    expense_id = _insert(seed_user_id, amount=25.0)
    response = client.post(f"/expenses/{expense_id}/edit", data=VALID_FORM)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert _row(expense_id)["amount"] == 25.0


def test_post_edit_valid_updates_and_redirects(auth_client, seed_user_id):
    expense_id = _insert(seed_user_id)
    response = auth_client.post(f"/expenses/{expense_id}/edit", data=VALID_FORM)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")
    row = _row(expense_id)
    assert row["amount"] == 75.5
    assert row["category"] == "Bills"
    assert row["date"] == "2026-03-21"
    assert row["description"] == "Power"


def test_post_edit_blank_description_stores_null(auth_client, seed_user_id):
    expense_id = _insert(seed_user_id)
    form = {**VALID_FORM, "description": "   "}
    response = auth_client.post(f"/expenses/{expense_id}/edit", data=form)
    assert response.status_code == 302
    assert _row(expense_id)["description"] is None


def test_post_edit_other_users_expense_returns_404_and_changes_nothing(
    auth_client, empty_user_id
):
    expense_id = _insert(empty_user_id, amount=25.0)
    response = auth_client.post(f"/expenses/{expense_id}/edit", data=VALID_FORM)
    assert response.status_code == 404
    assert _row(expense_id)["amount"] == 25.0


def test_post_edit_missing_expense_returns_404(auth_client):
    response = auth_client.post("/expenses/999999/edit", data=VALID_FORM)
    assert response.status_code == 404


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": ""},
        {"amount": "0"},
        {"amount": "abc"},
        {"category": "Hacker"},
        {"date": "not-a-date"},
        {"date": "2026-1-5"},
    ],
    ids=["missing-amount", "zero-amount", "non-numeric-amount",
         "invalid-category", "invalid-date", "non-padded-date"],
)
def test_post_edit_invalid_rerenders_with_error_and_keeps_row(
    auth_client, seed_user_id, overrides
):
    expense_id = _insert(seed_user_id, amount=25.0)
    form = {**VALID_FORM, **overrides}
    response = auth_client.post(f"/expenses/{expense_id}/edit", data=form)
    assert response.status_code == 200
    assert 'class="auth-error"' in response.get_data(as_text=True)
    assert _row(expense_id)["amount"] == 25.0


def test_post_edit_error_keeps_submitted_values(auth_client, seed_user_id):
    expense_id = _insert(seed_user_id, amount=25.0, description="Lunch")
    form = {**VALID_FORM, "amount": "0", "description": "Submitted note"}
    response = auth_client.post(f"/expenses/{expense_id}/edit", data=form)
    html = response.get_data(as_text=True)
    assert 'value="Submitted note"' in html
    assert 'value="Lunch"' not in html


# ------------------------------------------------------------------ #
# Profile page                                                        #
# ------------------------------------------------------------------ #

def test_profile_rows_link_to_edit(auth_client, seed_user_id):
    expense_id = _insert(seed_user_id)
    html = auth_client.get("/profile").get_data(as_text=True)
    assert f'href="/expenses/{expense_id}/edit"' in html
