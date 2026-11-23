# Spec: Delete Expense

## Overview
Step 9 lets a logged-in user delete one of their own expenses from the
profile page. The existing placeholder at `/expenses/<id>/delete` is replaced
with a real handler that removes the row through a new `delete_expense` helper
in `database/db.py`, then redirects back to `/profile`. Ownership is enforced
in the query itself, so a user can never delete another user's expense; a
missing or foreign id returns a 404. Each transaction row gains a "Delete"
action next to "Edit", and a small confirmation prompt guards against
accidental clicks. This completes the basic CRUD cycle for expenses (add in
Step 7, edit in Step 8, delete here) and follows the same ownership and
redirect pattern established by the edit feature.

## Depends on
- Step 1: Database setup (`expenses` table exists)
- Step 3: Login / Logout (`session["user_id"]` is set and enforced)
- Step 5: Profile page renders transactions (the delete action lives there)
- Step 7: Add Expense (gives us expenses to delete)
- Step 8: Edit Expense (establishes the Actions column in the transactions table and the ownership pattern)

## Routes
- `POST /expenses/<int:id>/delete` — delete the expense if it belongs to the
  logged-in user, then redirect to `/profile`; 404 if not found or not owned —
  logged-in only. Unauthenticated requests redirect to `/login`. `GET` returns 405.

## Database changes
No new tables or columns. Add one helper, `delete_expense(expense_id, user_id)`,
to `database/db.py` (see "Files to change").

## Templates
- **Create:** none. The route redirects on success and aborts 404 on failure,
  so no new page is rendered.
- **Modify:** `templates/profile.html`
  - In the Actions cell of each transaction row, add a `<form method="post">`
    after the existing "Edit" link, with action `url_for('delete_expense', id=tx.id)`,
    containing a submit button labelled "Delete" that has a `data-confirm`
    attribute holding the confirmation message.
  - The empty-state `colspan` stays at 5 (no column added).

## Files to change
- `database/db.py`
  - Add `delete_expense(expense_id, user_id)` — issues a parameterised
    `DELETE FROM expenses WHERE id = ? AND user_id = ?` and returns `True` if
    a row was removed, `False` otherwise. Follows the same `get_db()` /
    `try` / `finally: conn.close()` shape as `update_expense`.
- `app.py`
  - Import `delete_expense` from `database.db`.
  - Replace the placeholder at `/expenses/<int:id>/delete` (currently returns a
    raw string) with a handler that:
    - redirects to `url_for("login")` if `session["user_id"]` is not set
    - calls `delete_expense(id, session["user_id"])`
    - `abort(404)` if it returned `False`
    - otherwise `redirect(url_for("profile"))`
  - Route decorator: `@app.route("/expenses/<int:id>/delete", methods=["POST"])`.
- `templates/profile.html`
  - Add the Delete form described under Templates.
- `static/css/profile.css`
  - Style the Delete button to match the Edit link.
- `static/js/main.js`
  - Add a small vanilla JS handler: on `click`, for any element with a
    `data-confirm` attribute, call `window.confirm(el.dataset.confirm)` and
    call `preventDefault()` if the user cancels. Use event delegation on
    `document` so it works without per-link listeners.

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Foreign keys PRAGMA is already enabled in `get_db()`; do not bypass it
- `delete_expense` must scope its `WHERE` clause to both `id = ?` and
  `user_id = ?` — never delete by `id` alone
- Route logic stays in `app.py` and holds no SQL; all SQL lives in `database/db.py`
- Unauthenticated access must redirect to `/login` before any DB call
- If the expense does not exist or belongs to another user, return a 404 via `abort(404)` — no raw string responses
- On success, redirect to `url_for("profile")` — do not render a page
- Delete is `POST` only, so a plain link or image on another site cannot
  trigger a deletion. Do not add a `GET` handler.
- No inline `<script>` tags or inline `onclick` handlers — the confirm behaviour
  goes in `static/js/main.js`
- No inline styles
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Currency must always display as ₹ — never £ or $

## Definition of done
- [ ] Submitting a delete while logged out redirects to `/login`
- [ ] Submitting a delete for a non-existent expense id returns 404
- [ ] Submitting a delete for an expense owned by another user returns 404 and the row still exists
- [ ] Submitting a delete for your own expense removes it and redirects to `/profile`
- [ ] After the redirect, the deleted expense no longer appears in the profile transaction list
- [ ] A `GET` request to `/expenses/<id>/delete` returns 405
- [ ] Each transaction row in the profile table shows a "Delete" button next to "Edit"
- [ ] Clicking "Delete" shows a browser confirmation prompt; cancelling keeps the expense and does not navigate
- [ ] Confirming the prompt deletes the expense and returns to `/profile`
- [ ] The "Edit" link still works and the Actions column header still renders
- [ ] Deleting an expense updates the summary totals and category breakdown on `/profile`
- [ ] No inline `<script>` or `onclick` attributes appear in the rendered HTML
