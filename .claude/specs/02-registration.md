# Spec: Registration

## Overview

Make the existing `/register` page actually create accounts. Today `GET /register` renders `register.html`, but submitting the form does nothing because the route has no POST handler. This step adds the POST handling: validate the name, email and password, hash the password with werkzeug, insert the user into the `users` table through a `database/db.py` helper, and show a clear error on invalid or duplicate input.

This is the first feature that writes user data, so it is the point where the step 1 data layer gets used for real. It is needed before login (step 3 in the roadmap) can verify anyone, because there must be users to sign in as.

## Depends on

- **Step 1 — Database Setup** must be complete. This feature uses `get_db()`, the `users` table, and the unique `email` constraint from `database/db.py`.

## Routes

- `GET /register` — renders the registration form (already implemented; unchanged) — public
- `POST /register` — validates the submitted form, creates the user, redirects to `/login` on success, re-renders the form with an error on failure — public

## Database changes

No database changes. The `users` table already has `name`, `email` (UNIQUE, NOT NULL), `password_hash` (NOT NULL) and `created_at` (default `datetime('now')`), as defined in `database/db.py`.

Add one helper to `database/db.py`:

- `create_user(name, email, password_hash)` — inserts a row into `users` using a parameterised query and returns the new user id. Raises `sqlite3.IntegrityError` if the email already exists; the route catches it.

Add one lookup helper so the route can check for duplicates with a clear message instead of relying only on the exception:

- `get_user_by_email(email)` — returns the matching row or `None`, using a parameterised query.

## Templates

- **Create:** none
- **Modify:**
  - `templates/register.html` — change the form `action` from the hardcoded `"/register"` to `{{ url_for('register') }}` to follow the rule against hardcoded URLs. Keep the existing `{% if error %}` block, which already displays the `error` variable. Preserve the submitted `name` and `email` values on re-render so the user does not retype them (`value="{{ name or '' }}"` and `value="{{ email or '' }}"`). Do not echo the password back.
  - Add a **Confirm password** field (`<input type="password" id="confirm_password" name="confirm_password" required>`) directly below the password field, with its own `<label for="confirm_password">`. It is never re-populated on re-render.

## Files to change

- `app.py` — add `methods=["GET", "POST"]` to the `/register` route. In the POST branch, read the form fields (including `confirm_password`), call the validation and database helpers, and either redirect to `login` or re-render `register.html` with `error`. Add the imports needed for `request`, `redirect`, `url_for`, `generate_password_hash` and `sqlite3`.
- `database/db.py` — add `create_user()` and `get_user_by_email()`.
- `templates/register.html` — form action, value preservation, and the confirm-password field, as described above.

## Files to create

- None

## New dependencies

No new dependencies. `werkzeug.security` is already available through Flask and is pinned in `requirements.txt`.

## Rules for implementation

- Validation rules, applied in the route before any database call:
  - `name`, `email`, `password` and `confirm_password` are all required; strip surrounding whitespace from `name` and `email`.
  - `email` must contain `@` and a domain part with a dot. Keep this check simple; full RFC validation is out of scope.
  - `password` must be at least 8 characters, matching the placeholder text in `register.html`.
  - `confirm_password` must exactly equal `password` (no stripping). On mismatch, the error is "Passwords do not match."
  - Lowercase the email before storing and before the duplicate check, so `A@x.com` and `a@x.com` are treated as the same account.
- On validation failure, re-render `register.html` with HTTP status 400 and a single `error` message. Do not use bare string returns.
- On a duplicate email, re-render `register.html` with status 400 and the message "An account with this email already exists." Do not reveal anything beyond that.
- Passwords are hashed with `werkzeug.security.generate_password_hash`. Plain-text passwords are never stored, logged or passed to the template.
- No SQLAlchemy or ORMs.
- Parameterised queries only (`?` placeholders). No f-strings or `.format()` in SQL.
- Keep DB logic in `database/db.py`. The route fetches input, validates, calls helpers, and renders or redirects. It does not contain SQL.
- Use `abort()` for HTTP errors if any are needed. Do not return raw error strings.
- Use CSS variables from `static/css/style.css` for any styling. Do not hardcode hex values. Do not add inline `<style>` tags.
- All templates extend `base.html`. Use `url_for()` for every internal link.
- Do not change the placeholder routes (`/logout`, `/profile`, `/expenses/...`). Do not implement login logic in this step.
- Do not change the app port (5001).

## Definition of done

- [ ] `GET /register` still renders the form with status 200.
- [ ] Submitting a valid name, email and password redirects to `/login`, and the new user appears in the `users` table with an email in lowercase.
- [ ] The stored `password_hash` starts with a werkzeug scheme prefix (for example `scrypt:` or `pbkdf2:`) and does not equal the plain-text password.
- [ ] Submitting an email that already exists (in any letter case) re-renders the form with status 400 and the "already exists" message, and the table gains no new row.
- [ ] Submitting a password shorter than 8 characters re-renders the form with status 400 and an error message, and no row is inserted.
- [ ] Submitting with any of name, email, password or confirm password blank re-renders the form with status 400 and an error message.
- [ ] The register form shows a "Confirm password" field below the password field.
- [ ] Submitting mismatched password and confirm password re-renders the form with status 400 and "Passwords do not match.", and no row is inserted.
- [ ] After a failed submit, the name and email fields keep their values, and both password fields are empty.
- [ ] The form posts to `/register`, and its `action` is generated by `url_for()` in the rendered HTML.
- [ ] The register page still extends `base.html` and shows the shared navbar and footer.
- [ ] `/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit` and `/expenses/<id>/delete` still return their placeholder responses.
- [ ] The app starts with `python app.py` on port 5001 with no errors.
- [ ] Every SQL statement added in this step uses `?` placeholders.