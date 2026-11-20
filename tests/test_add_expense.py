import database.db as db


def expense_count(user_id):
    conn = db.get_db()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
    finally:
        conn.close()


def latest_expense(user_id):
    conn = db.get_db()
    try:
        return conn.execute(
            "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()


VALID_FORM = {
    "amount": "50.0",
    "category": "Food",
    "date": "2026-03-20",
    "description": "Lunch",
}


# ---------------------------------------------------------------- unit tests

def test_insert_expense_stores_row(test_db, seed_user_id):
    new_id = db.insert_expense(seed_user_id, 50.0, "Food", "2026-03-20", "Lunch")

    row = latest_expense(seed_user_id)
    assert row["id"] == new_id
    assert row["amount"] == 50.0
    assert row["category"] == "Food"
    assert row["date"] == "2026-03-20"
    assert row["description"] == "Lunch"


def test_insert_expense_with_none_description_stores_null(test_db, seed_user_id):
    db.insert_expense(seed_user_id, 12.5, "Transport", "2026-03-21", None)

    row = latest_expense(seed_user_id)
    assert row["description"] is None


# ------------------------------------------------------------ GET route tests

def test_get_add_expense_unauthenticated_redirects_to_login(client):
    response = client.get("/expenses/add")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_get_add_expense_authenticated_shows_form(auth_client):
    response = auth_client.get("/expenses/add")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '<form' in body
    assert 'method="POST"' in body
    assert '<select' in body
    for category in ("Food", "Transport", "Bills", "Health",
                     "Entertainment", "Shopping", "Other"):
        assert f'value="{category}"' in body


# ----------------------------------------------------------- POST route tests

def test_post_add_expense_unauthenticated_redirects_to_login(client, seed_user_id):
    before = expense_count(seed_user_id)
    response = client.post("/expenses/add", data=VALID_FORM)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert expense_count(seed_user_id) == before


def test_post_add_expense_valid_redirects_and_inserts(auth_client, seed_user_id):
    before = expense_count(seed_user_id)
    response = auth_client.post("/expenses/add", data=VALID_FORM)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")
    assert expense_count(seed_user_id) == before + 1

    row = latest_expense(seed_user_id)
    assert row["amount"] == 50.0
    assert row["category"] == "Food"
    assert row["date"] == "2026-03-20"
    assert row["description"] == "Lunch"


def test_post_add_expense_without_description_inserts_null(auth_client, seed_user_id):
    form = {**VALID_FORM, "description": ""}
    response = auth_client.post("/expenses/add", data=form)

    assert response.status_code == 302
    assert latest_expense(seed_user_id)["description"] is None


def _assert_rejected(auth_client, seed_user_id, **overrides):
    before = expense_count(seed_user_id)
    form = {**VALID_FORM, **overrides}
    response = auth_client.post("/expenses/add", data=form)

    assert response.status_code == 200
    assert 'class="auth-error"' in response.get_data(as_text=True)
    assert expense_count(seed_user_id) == before


def test_post_missing_amount_rejected(auth_client, seed_user_id):
    _assert_rejected(auth_client, seed_user_id, amount="")


def test_post_zero_amount_rejected(auth_client, seed_user_id):
    _assert_rejected(auth_client, seed_user_id, amount="0")


def test_post_negative_amount_rejected(auth_client, seed_user_id):
    _assert_rejected(auth_client, seed_user_id, amount="-5")


def test_post_non_numeric_amount_rejected(auth_client, seed_user_id):
    _assert_rejected(auth_client, seed_user_id, amount="abc")


def test_post_infinite_amount_rejected(auth_client, seed_user_id):
    _assert_rejected(auth_client, seed_user_id, amount="inf")


def test_post_invalid_category_rejected(auth_client, seed_user_id):
    _assert_rejected(auth_client, seed_user_id, category="Groceries")


def test_post_invalid_date_rejected(auth_client, seed_user_id):
    _assert_rejected(auth_client, seed_user_id, date="2026-13-01")


def test_post_non_padded_date_rejected(auth_client, seed_user_id):
    _assert_rejected(auth_client, seed_user_id, date="2026-1-5")


def test_post_description_too_long_rejected(auth_client, seed_user_id):
    _assert_rejected(auth_client, seed_user_id, description="x" * 201)


def test_post_error_keeps_submitted_values(auth_client):
    response = auth_client.post(
        "/expenses/add", data={**VALID_FORM, "amount": "0", "description": "Keep me"}
    )
    body = response.get_data(as_text=True)

    assert 'value="Keep me"' in body
    assert 'value="2026-03-20"' in body


def test_post_error_does_not_redirect(auth_client):
    response = auth_client.post("/expenses/add", data={**VALID_FORM, "amount": "abc"})
    assert response.status_code == 200


def test_post_each_valid_category_is_accepted(auth_client, seed_user_id):
    categories = ("Food", "Transport", "Bills", "Health",
                  "Entertainment", "Shopping", "Other")
    before = expense_count(seed_user_id)
    for category in categories:
        response = auth_client.post("/expenses/add", data={**VALID_FORM, "category": category})
        assert response.status_code == 302
    assert expense_count(seed_user_id) == before + len(categories)


def test_post_description_exactly_200_chars_accepted(auth_client, seed_user_id):
    response = auth_client.post(
        "/expenses/add", data={**VALID_FORM, "description": "x" * 200}
    )
    assert response.status_code == 302
    assert len(latest_expense(seed_user_id)["description"]) == 200


def test_post_description_is_stripped(auth_client, seed_user_id):
    auth_client.post("/expenses/add", data={**VALID_FORM, "description": "  Lunch  "})
    assert latest_expense(seed_user_id)["description"] == "Lunch"


def test_post_sql_injection_in_description_stored_literally(auth_client, seed_user_id):
    payload = "'); DROP TABLE expenses; --"
    auth_client.post("/expenses/add", data={**VALID_FORM, "description": payload})
    assert latest_expense(seed_user_id)["description"] == payload


def test_post_amount_above_maximum_rejected(auth_client, seed_user_id):
    _assert_rejected(auth_client, seed_user_id, amount="1e308")


def test_post_amount_rounded_to_two_decimals(auth_client, seed_user_id):
    auth_client.post("/expenses/add", data={**VALID_FORM, "amount": "0.014"})
    assert latest_expense(seed_user_id)["amount"] == 0.01


def test_post_valid_expense_appears_on_profile(auth_client):
    auth_client.post("/expenses/add", data={**VALID_FORM, "description": "Visible lunch"})
    response = auth_client.get("/profile")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Visible lunch" in body
    assert "₹" in body


def test_post_expense_isolated_to_logged_in_user(auth_client, empty_user_id, seed_user_id):
    before = expense_count(empty_user_id)
    auth_client.post("/expenses/add", data=VALID_FORM)
    assert expense_count(empty_user_id) == before


def test_get_add_expense_date_defaults_to_today(auth_client):
    from datetime import date

    body = auth_client.get("/expenses/add").get_data(as_text=True)
    assert f'value="{date.today().isoformat()}"' in body


def test_get_add_expense_has_cancel_link_to_profile(auth_client):
    body = auth_client.get("/expenses/add").get_data(as_text=True)
    assert 'href="/profile"' in body


def test_profile_page_has_add_expense_link(auth_client):
    body = auth_client.get("/profile").get_data(as_text=True)
    assert 'href="/expenses/add"' in body


def test_navbar_shows_add_expense_when_logged_in(auth_client):
    body = auth_client.get("/profile").get_data(as_text=True)
    assert 'href="/expenses/add"' in body


def test_navbar_hides_add_expense_when_logged_out(client):
    body = client.get("/login").get_data(as_text=True)
    assert "Add Expense" not in body
