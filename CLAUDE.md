# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the dev server (port 5001)
python app.py

# Or via Flask CLI
flask --app app run --debug --port 5001

# Run tests
pytest

# Install dependencies (uses uv)
uv sync
# or pip
pip install -r requirements.txt
```

## Architecture

This is a Flask web app called **Spendly** — a personal expense tracker. It's structured as a stepped learning project; many routes are stubs marked "coming in Step N".

**Entry point:** `app.py` — defines all Flask routes and runs the server on port 5001.

**Database layer:** `database/db.py` — intended to expose three functions:
- `get_db()` — SQLite connection with `row_factory` and foreign keys enabled
- `init_db()` — creates tables with `CREATE TABLE IF NOT EXISTS`
- `seed_db()` — inserts sample dev data

The file is currently a stub (Step 1 not yet implemented).

**Templates:** Jinja2, all extending `templates/base.html`. Base includes the navbar (Sign in / Get started links) and footer (Terms / Privacy links). Page-specific styles go in `{% block head %}`, scripts in `{% block scripts %}`.

**Static assets:** `static/css/style.css` uses CSS custom properties (`--ink`, `--accent`, `--paper`, etc.) with two font families — DM Serif Display (headings) and DM Sans (body). `static/js/main.js` is a stub.

**Python version:** 3.12 (`.python-version`). Dependencies managed with `uv` (`pyproject.toml` + `uv.lock`); `requirements.txt` is the pip-compatible fallback.

**Testing:** pytest + pytest-flask. No tests exist yet.
