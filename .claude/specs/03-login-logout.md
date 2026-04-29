# Spec: Login and Logout

## Overview

This step implements session-based authentication for Spendly. A `POST /login`
handler verifies the user's email and password against the database, then stores
their identity in Flask's signed session cookie. The `/logout` route clears that
session and sends the user back to the landing page. The navbar in `base.html`
is updated to show the signed-in user's name and a logout link instead of the
"Sign in / Get started" buttons whenever a session is active.

## Depends on

- Step 1 — Database Setup (`get_db()` and the `users` table with `password_hash`)
- Step 2 — Registration (at least one user must exist to test login)

## Routes

- `GET /login` — render the login form; redirect to landing if session already
  active — public
- `POST /login` — verify credentials, create session, redirect to landing — public
- `GET /logout` — clear session, redirect to landing — logged-in (no hard guard
  needed at this step)

## Database changes

No database changes. Reads from the existing `users` table only:

```sql
SELECT id, name, password_hash FROM users WHERE email = ?
```

## Templates

- **Modify:** `templates/login.html` — preserve the submitted email value on
  validation error (`value="{{ email or '' }}"` on the email input)
- **Modify:** `templates/base.html` — make the nav-links block conditional:
  - When `session.user_id` is set: show the user's name (non-clickable or linked
    to `/profile`) and a "Sign out" link pointing to `/logout`
  - Otherwise: show the current "Sign in" and "Get started" links unchanged

## Files to change

- `app.py` — add POST handler to `/login`, implement `/logout`
- `templates/login.html` — email value preservation
- `templates/base.html` — conditional navbar

## Files to create

None.

## New dependencies

No new dependencies. Uses:
- `werkzeug.security.check_password_hash` (already installed)
- `flask.session` (built-in)

## Future improvements (out of scope for this step)

- Support a `next` query parameter so users land back on the page that triggered
  login (e.g. `/login?next=/expenses/add`)
- CSRF protection, rate limiting, account lockout

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3`
- Parameterised queries only (`?` placeholders, never f-strings or `%` in SQL)
- Passwords verified with `check_password_hash` — never compared in plaintext
- Store only `user_id` (int) and `user_name` (str) in the session — no sensitive data
- Normalize the submitted email with `.strip().lower()` before querying
- Always return a generic `"Invalid email or password."` error for failed logins —
  never reveal whether the email exists or not
- Session presence checked as `"user_id" in session` everywhere (routes and templates)
- In Jinja templates use `session.get("user_id")` / `session.get("user_name")` —
  not dot-attribute access — to avoid silent `None` bugs
- `get_db()` returns a fresh `sqlite3` connection (not bound to Flask `g`), so the
  connection must be closed in a `finally` block — consistent with Step 2 pattern
- Errors surfaced as inline template variables (`error=`); no `flash()` on login —
  flash is reserved for cross-page messages (e.g. registration success)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Do not import or use `flask_login` or any auth extension

## Definition of done

- [ ] `GET /login` renders the form when not logged in
- [ ] `GET /login` redirects to landing when a session is already active
- [ ] Submitting valid credentials:
  - Creates a Flask session (`session["user_id"]` and `session["user_name"]` set)
  - Redirects to the landing page
- [ ] Submitting an unknown email → generic inline error shown, email field preserved
- [ ] Submitting the correct email but wrong password → same generic inline error shown, email field preserved
- [ ] Missing email or password → inline error shown
- [ ] Navbar shows "Hello, \<name\>" and "Sign out" link when logged in
- [ ] Navbar shows "Sign in" and "Get started" when logged out
- [ ] `GET /logout` clears the session and redirects to landing
- [ ] Visiting `/logout` without a session redirects to landing without errors
- [ ] App runs without errors (`python app.py`)
