# Spec: Login and Logout

## Overview

Make the existing `/login` page actually sign users in, and make `/logout` actually sign them out. Today `GET /login` renders `login.html`, but submitting the form does nothing because the route has no POST handler, and `GET /logout` is a placeholder string. This step adds a session-based login: verify the email and password against the `users` table using werkzeug's password hash check, store the signed-in user's id in the Flask session, and clear that session on logout.

This is the step that makes accounts usable. Registration (step 2) lets people create accounts, and this step lets them prove who they are. Every later feature that depends on "the current user" (profile, expenses) relies on the session set up here.

## Depends on

- **Step 1 — Database Setup** must be complete. This feature uses `get_db()`, the `users` table and `get_user_by_email()` from `database/db.py`.
- **Step 2 — Registration** must be complete. Login verifies passwords that registration hashed with `generate_password_hash`, and tests need users created through `/register`.

## Routes

- `GET /login` — renders the login form (already implemented; unchanged except for error display) — public
- `POST /login` — validates the submitted email and password, verifies them, stores the user id in the session, and redirects to `/profile` on success. On failure, re-renders the form with a generic error and status 400 — public
- `GET /logout` — clears the session and redirects to `/` — logged-in (a logged-out visitor who hits it is also redirected to `/`, so it is effectively safe for everyone)

## Database changes

No database changes. The `users` table already has `id`, `email` (UNIQUE) and `password_hash`, as defined in `database/db.py`.

No new helpers are needed for the write path. The only read needed is `get_user_by_email(email)`, which already exists from step 2 and returns the row (or `None`) using a parameterised query.

## Templates

- **Create:** none
- **Modify:**
  - `templates/login.html` — change the form `action` from the hardcoded `"/login"` to `{{ url_for('login') }}`. Add the same `{% if error %}` block used in `register.html` so the error message is visible. Preserve the submitted `email` on re-render with `value="{{ email or '' }}"`. Do not re-populate the password.
  - `templates/base.html` — in the nav, when the session has a signed-in user, show a **Log out** link (`url_for('logout')`) in place of the **Sign in** and **Get started** links. When signed out, the nav stays as it is today. Use `session` from Flask in the template condition (`{% if session.get('user_id') %}`).

## Files to change

- `app.py`
  - Add `from flask import session` to the existing Flask import line.
  - Set a secret key so sessions can be signed: `app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")`. Add `import os`. Read the value from the environment; the fallback is for local development only.
  - Change the `/login` route to `methods=["GET", "POST"]`. In the POST branch: read `email` (strip and lowercase) and `password`; if either is empty, re-render with an error; look up the user with `get_user_by_email`; check the password with `check_password_hash(user["password_hash"], password)`; on success, call `session.clear()`, then set `session["user_id"]` and `session["user_name"]`, and redirect to `url_for("profile")`. On any failure, return the same generic error (see Rules) with status 400.
  - Replace the `/logout` placeholder with a real handler: call `session.clear()` and redirect to `url_for("landing")`.
  - Add `check_password_hash` to the werkzeug import line.
- `database/db.py` — no changes. (Do not add login logic here beyond what already exists; the password check stays in the route, consistent with how step 2 handles hashing.)
- `static/css/style.css` — add styles for the nav **Log out** link only if it needs a distinct class. Reuse the existing nav link styles where possible. Use CSS variables only.
- `CLAUDE.md` — in the "Implemented vs stub routes" table, change `GET /logout` from "Stub — Step 3" to "Implemented — Step 3".

## Files to create

None.

## New dependencies

No new dependencies. `flask.session` and `werkzeug.security.check_password_hash` are already available through `requirements.txt`.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only. The lookup must go through `get_user_by_email`, which already uses `?` placeholders. Never build SQL with f-strings.
- Passwords hashed with werkzeug. Verify with `check_password_hash`. Never store or compare plain-text passwords. Never log the password.
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `url_for()` for every internal link, including the form action and nav links. Never hardcode URLs.
- Use `abort()` for HTTP errors if one is needed. Login failures re-render `login.html` with `error` and status 400, matching the registration pattern.
- The login error must be generic: `"Invalid email or password."` Do not reveal whether the email exists.
- Login must call `session.clear()` before setting session values, to prevent session fixation.
- Route functions stay thin: read the form, call the helper, check the password, set the session, render or redirect. No SQL in the route.
- Do not implement any other stub route (`/profile`, `/expenses/*`). `/login` redirects to `/profile`, which is still a placeholder string until step 4; that is expected.
- Do not change the port (5001).
- Do not add a "remember me" option, password reset, or rate limiting in this step.

## Definition of done

- [ ] `python app.py` starts without errors on port 5001.
- [ ] Submitting `/login` with an empty email or password re-renders the login page with an error and HTTP status 400.
- [ ] Submitting `/login` with an email that does not exist shows `Invalid email or password.` and returns status 400.
- [ ] Submitting `/login` with a valid email and the wrong password shows the same `Invalid email or password.` message.
- [ ] Logging in with a valid registered account (created through `/register`) redirects to `/profile`.
- [ ] After a successful login, the nav shows **Log out** and no longer shows **Sign in** or **Get started**.
- [ ] After a failed login, the email field keeps the typed value, and the password field is empty.
- [ ] Email is matched case-insensitively: logging in with the registered email in upper case works.
- [ ] Visiting `/logout` while signed in redirects to `/`, and the nav shows **Sign in** and **Get started** again.
- [ ] Visiting `/logout` while signed out also redirects to `/` without an error.
- [ ] After logout, navigating directly to `/profile` is not affected by the session (the session no longer contains `user_id`), confirmed by inspecting the cookie or nav state.
- [ ] The password is stored only as a hash in `spendly.db` (`password_hash` column starts with a werkzeug hash prefix such as `scrypt:` or `pbkdf2:`), not as plain text.
- [ ] No SQL string in `app.py` or `database/db.py` for this step is built with an f-string.
- [ ] The login and logout pages and nav render correctly at phone width with no horizontal scroll.
- [ ] `pytest` passes for any tests added for this step, and no existing tests fail.
