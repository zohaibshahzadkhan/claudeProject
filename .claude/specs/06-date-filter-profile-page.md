# Spec: Date Filter for Profile Page

## Overview
Step 6 lets a logged-in user narrow the profile page to a date range. A
start date and end date are supplied as query parameters on `GET /profile`.
When present, they limit every data section on the page — summary stats,
recent transactions and category breakdown — to expenses dated within that
range (inclusive). With no parameters the page shows all-time data, exactly as
it does after Step 5. This matters at this point in the roadmap because the
profile page now shows real data, and users with a long expense history need
a way to focus on a period such as a single month without leaving the page.

## Depends on
- Step 1: Database setup (`expenses.date` column exists)
- Step 2: Registration (users exist)
- Step 3: Login / Logout (`session["user_id"]` is set; `/profile` is protected)
- Step 4: Profile page UI (template and four sections exist)
- Step 5: Backend connection (stats, transactions and breakdown are read from the database)

## Routes
No new routes. The existing `GET /profile` route accepts two optional query
parameters:
- `start_date` — `YYYY-MM-DD`, optional, inclusive lower bound
- `end_date` — `YYYY-MM-DD`, optional, inclusive upper bound

Access: logged-in only (unchanged).

Validation in the `profile()` view:
- A value that is not a valid `YYYY-MM-DD` date → `abort(400)`
- `start_date` later than `end_date` → `abort(400)`
- Only one of the two supplied → open-ended on the other side

## Database changes
No database changes. `expenses.date` is already stored as ISO `YYYY-MM-DD`
text, so string comparison in SQL is correct for range filtering.

## Templates
- **Create:** none
- **Modify:** `templates/profile.html`
  - Add a filter form above the stats row: two `<input type="date">` fields
    (`start_date`, `end_date`), an "Apply" submit button using method `GET`
    to `url_for('profile')`, and a "Clear" link back to `url_for('profile')`.
  - Pre-fill the inputs with the currently active values.
  - Show the active range as a short label (e.g. "1 Jan 2026 – 31 Jan 2026"
    or "All time") so the user can see what is filtered.
  - Empty-state messages should read "No transactions in this period" and
    "No expenses in this period" when a filter is active.

## Files to change
- `app.py` — read and validate `start_date` / `end_date` from `request.args`
  in `profile()`; pass them to the helpers and to the template
- `database/db.py` — add optional `start_date=None, end_date=None` parameters
  to `get_summary_stats`, `get_recent_transactions` and `get_category_breakdown`;
  add the date conditions to their SQL when provided
- `templates/profile.html` — filter form, active-range label, empty-state text
- `static/css/profile.css` — styles for the filter form (using existing CSS variables only)

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()` only
- Parameterised queries only — add date bounds as `?` placeholders; build the
  SQL condition text from fixed strings only, never from user input
- Date parsing uses `datetime.strptime(value, "%Y-%m-%d")`; do not pass raw
  query strings into SQL
- Route functions stay thin: parse and validate in `app.py`, all SQL in `database/db.py`
- Use `abort()` for the 400 responses — never return a bare error string
- Query helpers in `database/db.py` must still call `get_db()` internally and
  close the connection before returning
- Helper defaults (`None`) must return all-time results, so existing callers
  and the Step 5 tests keep passing unchanged
- Use CSS variables — never hardcode hex values
- No inline styles; put filter styles in `static/css/profile.css`
- All templates extend `base.html`
- Use `url_for()` for every link and form action
- Currency must always display as ₹ — never £ or $
- `pct` values in the category breakdown must still sum to 100 for the filtered set

## Definition of done
- [ ] Visiting `/profile` with no query parameters shows all-time data, identical to the Step 5 result for the seed user (₹287.43, 8 transactions)
- [ ] Visiting `/profile?start_date=2026-01-01&end_date=2026-01-31` (adjusting to the seed month) shows only expenses dated within that range in the stats, transaction list and category breakdown
- [ ] Start and end dates are both inclusive: an expense dated exactly on either boundary is included
- [ ] Setting only `start_date` shows expenses from that date onward; setting only `end_date` shows expenses up to and including that date
- [ ] A range with no expenses shows ₹0.00 total, 0 transactions, "No transactions in this period" and "No expenses in this period"
- [ ] `/profile?start_date=not-a-date` returns HTTP 400
- [ ] `/profile?start_date=2026-02-01&end_date=2026-01-01` returns HTTP 400
- [ ] Submitting the filter form with dates fills the URL with the parameters and the inputs keep the chosen values
- [ ] The "Clear" link returns to `/profile` and shows all-time data
- [ ] The active-range label reads "All time" when no filter is set and shows the dates when one is
- [ ] The category percentages on a filtered view still sum to 100 %
- [ ] Visiting `/profile` without being logged in still redirects to `/login`
- [ ] No hardcoded hex colours are added to `profile.css` or `profile.html`
- [ ] All amounts still display with the ₹ symbol