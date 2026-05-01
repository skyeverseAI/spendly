# Spec: Profile Page

## Overview

This step replaces the `/profile` stub with a real, session-guarded page that
displays the logged-in user's account details — their name, email address, and
the date they joined Spendly — along with a spending overview: total amount
spent, a category breakdown doughnut chart, and the top 3 expenses by amount.
It is the first authenticated-only page in the app and establishes the pattern
for login-gating routes: check `session["user_id"]`, redirect to `/login` if
absent, otherwise fetch the user row and expense data and render the template.
No editing or password-change functionality is in scope for this step.

## Depends on

- Step 1 — Database Setup (`get_db()` and the `users` and `expenses` tables)
- Step 3 — Login and Logout (session must be set before the profile page is reachable)

## Routes

- `GET /profile` — fetch and display the logged-in user's details and spending
  overview; redirect to `/login` if no session — logged-in

## Database changes

No database changes. Three read queries against existing tables:

```sql
-- User info
SELECT id, name, email, created_at FROM users WHERE id = ?

-- Total spend
SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE user_id = ?

-- Category breakdown
SELECT category, SUM(amount) as total FROM expenses
WHERE user_id = ? GROUP BY category ORDER BY total DESC

-- Top 3 by amount
SELECT amount, category, description, date FROM expenses
WHERE user_id = ? ORDER BY amount DESC LIMIT 3
```

## Templates

- **Create:** `templates/profile.html` — full profile page extending `base.html`
- **Modify:** none

## Files to change

- `app.py` — replace the `/profile` stub with a real route handler; run all
  four queries inside a single `try/finally` DB block
- `static/css/style.css` — add profile page styles (scoped under `.profile-*`)
- `templates/base.html` — make `nav-username` a link pointing to `/profile`

## Files to create

- `templates/profile.html`

## New dependencies

- **Chart.js 4** — loaded via CDN (`cdn.jsdelivr.net`) in `{% block scripts %}`
  only on the profile page. No pip package needed.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3`
- Parameterised queries only (`?` placeholders, never f-strings in SQL)
- Passwords hashed with werkzeug (no changes to passwords in this step)
- Use CSS variables — never hardcode hex values (chart colours are the only
  exception — they must match the existing mock-bar palette)
- All templates extend `base.html`
- Guard the route with `if "user_id" not in session: return redirect(url_for("login"))`
- All four queries run inside a single `get_db()` / `finally db.close()` block
- If the user row is not found, clear the session and redirect to landing
- Pass only `user`, `joined`, `total_spend`, `category_spends`, `top_3` to the
  template — never expose `password_hash`
- Format `created_at` in Python with `datetime.strptime` before passing to template
- Chart.js loaded conditionally — only when `category_spends` is non-empty
- Category dot colours in the legend are set via inline JS to match the chart

## Definition of done

- [ ] `GET /profile` with no session redirects to `/login`
- [ ] `GET /profile` with a valid session renders the profile page
- [ ] Profile page displays the user's name
- [ ] Profile page displays the user's email address
- [ ] Profile page displays the "Member since" date (formatted, not raw ISO string)
- [ ] Profile page displays total amount spent (₹ formatted to 2 decimal places)
- [ ] Category doughnut chart renders with correct segments and tooltip amounts
- [ ] Category legend shows each category name and its total spend
- [ ] Top 3 spends shown with rank, description, category · date meta, and amount
- [ ] Navbar "Hello, name" is a clickable link pointing to `/profile`
- [ ] Visiting `/profile` after logout redirects to `/login`
- [ ] App runs without errors (`python app.py`)
