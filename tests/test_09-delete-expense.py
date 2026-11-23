import pytest

import database.db as db


def _insert(
    user_id, amount=25.0, category="Food", date_str="2026-03-10", description="Lunch"
):
    return db.insert_expense(user_id, amount, category, date_str, description)


def _row(expense_id):
    conn = db.get_db()
    try:
        row = conn.execute(
            "SELECT * FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def _count(user_id):
    conn = db.get_db()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# Unit tests: db helper                                               #
# ------------------------------------------------------------------ #


def test_delete_expense_owned_row_returns_true_and_removes_row(seed_user_id):
    expense_id = _insert(seed_user_id)
    assert db.delete_expense(expense_id, seed_user_id) is True
    assert _row(expense_id) is None


def test_delete_expense_wrong_user_returns_false_and_keeps_row(
    seed_user_id, empty_user_id
):
    expense_id = _insert(seed_user_id)
    assert db.delete_expense(expense_id, empty_user_id) is False
    assert _row(expense_id) is not None


def test_delete_expense_missing_id_returns_false(seed_user_id):
    assert db.delete_expense(999_999, seed_user_id) is False


def test_delete_expense_only_removes_target_row(seed_user_id):
    target = _insert(seed_user_id, description="Target")
    other = _insert(seed_user_id, description="Other")
    before = _count(seed_user_id)
    assert db.delete_expense(target, seed_user_id) is True
    assert _count(seed_user_id) == before - 1
    assert _row(other) is not None


def test_delete_expense_twice_second_call_returns_false(seed_user_id):
    expense_id = _insert(seed_user_id)
    assert db.delete_expense(expense_id, seed_user_id) is True
    assert db.delete_expense(expense_id, seed_user_id) is False


# ------------------------------------------------------------------ #
# Route tests: auth guard                                             #
# ------------------------------------------------------------------ #


def test_post_delete_unauthenticated_redirects_to_login(client, seed_user_id):
    expense_id = _insert(seed_user_id)
    response = client.post(f"/expenses/{expense_id}/delete")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_post_delete_unauthenticated_does_not_delete(client, seed_user_id):
    expense_id = _insert(seed_user_id)
    client.post(f"/expenses/{expense_id}/delete")
    assert _row(expense_id) is not None


def test_post_delete_unauthenticated_missing_id_redirects_not_404(client):
    response = client.post("/expenses/999999/delete")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ------------------------------------------------------------------ #
# Route tests: method restrictions                                    #
# ------------------------------------------------------------------ #


def test_get_delete_authenticated_returns_405_and_keeps_row(auth_client, seed_user_id):
    expense_id = _insert(seed_user_id)
    response = auth_client.get(f"/expenses/{expense_id}/delete")
    assert response.status_code == 405
    assert _row(expense_id) is not None


def test_get_delete_unauthenticated_returns_405(client, seed_user_id):
    expense_id = _insert(seed_user_id)
    response = client.get(f"/expenses/{expense_id}/delete")
    assert response.status_code == 405
    assert _row(expense_id) is not None


@pytest.mark.parametrize("method", ["put", "delete", "patch"])
def test_other_methods_on_delete_route_return_405(auth_client, seed_user_id, method):
    expense_id = _insert(seed_user_id)
    response = getattr(auth_client, method)(f"/expenses/{expense_id}/delete")
    assert response.status_code == 405
    assert _row(expense_id) is not None


# ------------------------------------------------------------------ #
# Route tests: 404 behaviour                                          #
# ------------------------------------------------------------------ #


def test_post_delete_missing_expense_returns_404(auth_client):
    assert auth_client.post("/expenses/999999/delete").status_code == 404


def test_post_delete_other_users_expense_returns_404_and_row_remains(
    auth_client, empty_user_id
):
    expense_id = _insert(empty_user_id, description="Not yours")
    response = auth_client.post(f"/expenses/{expense_id}/delete")
    assert response.status_code == 404
    row = _row(expense_id)
    assert row is not None
    assert row["user_id"] == empty_user_id
    assert row["description"] == "Not yours"


def test_post_delete_non_integer_id_returns_404(auth_client):
    assert auth_client.post("/expenses/abc/delete").status_code == 404


def test_post_delete_already_deleted_expense_returns_404(auth_client, seed_user_id):
    expense_id = _insert(seed_user_id)
    assert auth_client.post(f"/expenses/{expense_id}/delete").status_code == 302
    assert auth_client.post(f"/expenses/{expense_id}/delete").status_code == 404


# ------------------------------------------------------------------ #
# Route tests: happy path and DB side effects                         #
# ------------------------------------------------------------------ #


def test_post_delete_own_expense_redirects_to_profile(auth_client, seed_user_id):
    expense_id = _insert(seed_user_id)
    response = auth_client.post(f"/expenses/{expense_id}/delete")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")


def test_post_delete_own_expense_removes_row(auth_client, seed_user_id):
    expense_id = _insert(seed_user_id)
    auth_client.post(f"/expenses/{expense_id}/delete")
    assert _row(expense_id) is None


def test_post_delete_own_expense_reduces_count_by_one(auth_client, seed_user_id):
    expense_id = _insert(seed_user_id)
    before = _count(seed_user_id)
    auth_client.post(f"/expenses/{expense_id}/delete")
    assert _count(seed_user_id) == before - 1


def test_post_delete_leaves_other_expenses_untouched(auth_client, seed_user_id):
    target = _insert(seed_user_id, description="Target")
    other = _insert(seed_user_id, description="Keeper")
    auth_client.post(f"/expenses/{target}/delete")
    assert _row(target) is None
    assert _row(other) is not None


def test_post_delete_does_not_affect_other_users_expenses(
    auth_client, seed_user_id, empty_user_id
):
    mine = _insert(seed_user_id)
    theirs = _insert(empty_user_id)
    auth_client.post(f"/expenses/{mine}/delete")
    assert _row(theirs) is not None


def test_post_delete_follow_redirect_lands_on_profile_200(auth_client, seed_user_id):
    expense_id = _insert(seed_user_id)
    response = auth_client.post(f"/expenses/{expense_id}/delete", follow_redirects=True)
    assert response.status_code == 200


def test_deleted_expense_no_longer_listed_on_profile(auth_client, seed_user_id):
    expense_id = _insert(seed_user_id, description="UniqueVanishingItem")
    assert "UniqueVanishingItem" in auth_client.get("/profile").get_data(as_text=True)
    auth_client.post(f"/expenses/{expense_id}/delete")
    html = auth_client.get("/profile").get_data(as_text=True)
    assert "UniqueVanishingItem" not in html


def test_delete_updates_profile_summary_total(auth_client, empty_user_id):
    # Log in as the user with no seeded expenses so totals are fully controlled.
    with auth_client.session_transaction() as sess:
        sess["user_id"] = empty_user_id
        sess["user_name"] = "New Person"
    expense_id = _insert(empty_user_id, amount=777.0, description="BigOne")
    before = auth_client.get("/profile").get_data(as_text=True)
    # Match the full rendered currency string so unrelated page text can't collide.
    assert "₹777.00" in before, "Expected amount in profile before delete"
    auth_client.post(f"/expenses/{expense_id}/delete")
    after = auth_client.get("/profile").get_data(as_text=True)
    assert "₹777.00" not in after, "Deleted amount should vanish from totals/list"
    assert "BigOne" not in after


def test_sql_injection_in_description_does_not_break_delete(auth_client, seed_user_id):
    evil = _insert(seed_user_id, description="x'; DROP TABLE expenses;--")
    other = _insert(seed_user_id, description="Safe")
    assert auth_client.post(f"/expenses/{evil}/delete").status_code == 302
    assert _row(evil) is None
    assert _row(other) is not None


# ------------------------------------------------------------------ #
# Template tests: profile page                                        #
# ------------------------------------------------------------------ #


def test_profile_shows_delete_form_for_each_row(auth_client, seed_user_id):
    expense_id = _insert(seed_user_id)
    html = auth_client.get("/profile").get_data(as_text=True)
    assert f'action="/expenses/{expense_id}/delete"' in html
    assert "Delete" in html


def test_profile_delete_form_uses_post_method(auth_client, seed_user_id):
    expense_id = _insert(seed_user_id)
    html = auth_client.get("/profile").get_data(as_text=True)
    start = html.index(f'action="/expenses/{expense_id}/delete"')
    form_start = html.rfind("<form", 0, start)
    form_end = html.index("</form>", start)
    form_html = html[form_start:form_end].lower()
    assert 'method="post"' in form_html


def test_profile_delete_button_has_data_confirm(auth_client, seed_user_id):
    expense_id = _insert(seed_user_id)
    html = auth_client.get("/profile").get_data(as_text=True)
    start = html.index(f'action="/expenses/{expense_id}/delete"')
    form_end = html.index("</form>", start)
    assert "data-confirm" in html[start:form_end]


def test_profile_delete_appears_after_edit_link(auth_client, seed_user_id):
    expense_id = _insert(seed_user_id)
    html = auth_client.get("/profile").get_data(as_text=True)
    edit_pos = html.index(f"/expenses/{expense_id}/edit")
    delete_pos = html.index(f"/expenses/{expense_id}/delete")
    assert edit_pos < delete_pos, "Delete should follow the Edit link"


def test_profile_edit_link_and_actions_header_still_render(auth_client, seed_user_id):
    expense_id = _insert(seed_user_id)
    html = auth_client.get("/profile").get_data(as_text=True)
    assert f"/expenses/{expense_id}/edit" in html
    assert "Actions" in html


def test_profile_has_no_inline_script_or_onclick(auth_client, seed_user_id):
    _insert(seed_user_id)
    html = auth_client.get("/profile").get_data(as_text=True).lower()
    assert "onclick" not in html
    # Only external scripts (with src) are allowed.
    import re

    inline_scripts = [
        m for m in re.findall(r"<script\b([^>]*)>", html) if "src=" not in m
    ]
    assert inline_scripts == [], "No inline <script> tags allowed"


def test_profile_empty_state_has_no_delete_form(auth_client, empty_user_id):
    with auth_client.session_transaction() as sess:
        sess["user_id"] = empty_user_id
        sess["user_name"] = "New Person"
    response = auth_client.get("/profile")
    assert response.status_code == 200
    assert "/delete" not in response.get_data(as_text=True)
