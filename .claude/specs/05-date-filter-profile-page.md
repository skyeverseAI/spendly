# Spec: Date Filter for Profile Page

## Overview

This step enhances the existing `/profile` route with an optional date range
filter so users can scope their spending stats to a specific period. The filter
is applied via `from` and `to` query parameters (ISO date strings). When both
parameters are present and valid, all three spending queries — total spend,
category breakdown, and top 3 expenses — are constrained to that date window.
When the parameters are absent or invalid, the page falls back to all-time data,
preserving the existing behaviour. A compact filter form with two date inputs and
three preset buttons (This Month, Last 30 Days, All Time) is added to the top
of the spending section in `profile.html`. No new routes, tables, or pip
packages are required.

## Depends on

- Step 1 — Database Setup (`expenses` table with a `date TEXT` column)
- Step 3 — Login and Logout (session must be set before `/profile` is reachable)
- Step 4 — Profile Page (the route and template this step extends)

## Routes

No new routes. The existing route is extended:

- `GET /profile?from=YYYY-MM-DD&to=YYYY-MM-DD` — same session guard and data
  fetch as before, but all expense queries are filtered to the given date range —
  logged-in

## Database changes

No schema changes. The three existing expense queries gain an optional
`AND date BETWEEN ? AND ?` clause when filter params are present:

```sql
-- Total spend (filtered)
SELECT COALESCE(SUM(amount), 0) FROM expenses
WHERE user_id = ? AND date BETWEEN ? AND ?

-- Category breakdown (filtered)
SELECT category, SUM(amount) as total FROM expenses
WHERE user_id = ? AND date BETWEEN ? AND ?
GROUP BY category ORDER BY total DESC

-- Top 3 by amount (filtered)
SELECT amount, category, description, date FROM expenses
WHERE user_id = ? AND date BETWEEN ? AND ?
ORDER BY amount DESC LIMIT 3
```

## Templates

- **Modify:** `templates/profile.html` — add a filter bar above the spending
  stats section containing two date inputs (`from`, `to`), three preset buttons
  (This Month, Last 30 Days, All Time), and a submit button. Preset buttons
  populate the date inputs via JavaScript and submit the form. When a filter is
  active, display the active date range as a pill/badge above the stats. When no
  filter is active, show "All Time" as the active state on the preset buttons.

## Files to change

- `app.py` — update the `/profile` route to:
  1. Read `from` and `to` from `request.args`
  2. Validate both are present and parseable as `YYYY-MM-DD`; if invalid, ignore
     and fall back to all-time (do not flash an error)
  3. Pass the validated date range to the three expense queries
  4. Pass `date_from`, `date_to`, and `is_filtered` (bool) to the template

- `templates/profile.html` — add the filter bar and active-filter badge

- `static/css/style.css` — add styles for the filter bar, date inputs, preset
  buttons, and active-filter badge (scoped under `.filter-*`)

## Files to create

No new files.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3`
- Parameterised queries only (`?` placeholders, never f-strings in SQL)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Validate `from` and `to` in Python using `datetime.strptime(value, "%Y-%m-%d")`
  inside a `try/except ValueError` — never trust raw query string values in SQL
- If only one of `from` / `to` is provided, treat the filter as absent and show
  all-time data
- If `from` is later than `to`, treat the filter as absent
- The three expense queries must use the same `date_from` / `date_to` values so
  stats stay consistent with each other
- Preset buttons use vanilla JS only — no external libraries
- The filter form submits via `GET` (not POST) so filtered URLs are bookmarkable
- "This Month" preset = first day of the current calendar month to today
- "Last 30 Days" preset = today minus 29 days to today
- "All Time" preset = clears both inputs and resubmits (or navigates to `/profile`)
- `is_filtered=True` only when both params are valid and present

## Definition of done

- [ ] `GET /profile` with no query params renders all-time data (existing behaviour unchanged)
- [ ] `GET /profile?from=2026-04-01&to=2026-04-30` shows stats for April 2026 only
- [ ] Total spend reflects only expenses within the date range when filtered
- [ ] Category breakdown chart reflects only expenses within the date range when filtered
- [ ] Top 3 expenses reflect only expenses within the date range when filtered
- [ ] An active-filter badge is visible when a date range is applied
- [ ] No badge is shown when viewing all-time data
- [ ] "This Month" preset populates the correct from/to dates and submits
- [ ] "Last 30 Days" preset populates the correct from/to dates and submits
- [ ] "All Time" preset clears the filter and returns to unfiltered profile
- [ ] Invalid date strings in query params (e.g. `?from=abc&to=xyz`) fall back to all-time silently
- [ ] Single param only (e.g. `?from=2026-04-01` with no `to`) falls back to all-time
- [ ] `from` later than `to` falls back to all-time
- [ ] App runs without errors (`python app.py`)
