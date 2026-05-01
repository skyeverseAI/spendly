# conftest.py — shared fixtures for the Spendly test suite
#
# IMPORTANT: database/db.py hard-codes DB_PATH from __file__ rather than
# reading a Flask config key.  We must monkey-patch database.db.DB_PATH to a
# temporary file before any get_db() / init_db() call so tests never touch the
# real spendly.db on disk.
#
# app.py also calls init_db() + seed_db() at module level inside an
# app_context.  Because Python caches imported modules the app object is only
# constructed once per process; the module-level side-effects have already run
# by the time our fixture executes.  We handle this by:
#   1. Patching DB_PATH to a fresh temp file.
#   2. Calling init_db() again inside the fixture so the temp DB has the schema.
#   3. NOT calling seed_db() — each test inserts only the data it needs.

import os
import pytest
import database.db as db_module
from app import app as flask_app
from database.db import init_db
from werkzeug.security import generate_password_hash


@pytest.fixture()
def app(tmp_path):
    """
    Yield a configured Flask test application backed by an isolated
    temporary SQLite database.  The database is freshly initialised (schema
    only, no seed data) for every test.
    """
    tmp_db = str(tmp_path / "test_spendly.db")

    # Patch the module-level DB_PATH so every get_db() call uses our temp file.
    original_db_path = db_module.DB_PATH
    db_module.DB_PATH = tmp_db

    flask_app.config.update({"TESTING": True, "SECRET_KEY": "test-secret"})

    with flask_app.app_context():
        init_db()   # create tables in the temp DB; no seed data

    yield flask_app

    # Teardown: restore DB_PATH so other test sessions are unaffected.
    db_module.DB_PATH = original_db_path


@pytest.fixture()
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Shared DB helpers
# ---------------------------------------------------------------------------

def insert_user(app, name="Test User", email="test@example.com",
                password="password123"):
    """Insert a user and return their id."""
    from database.db import get_db
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        db.commit()
        user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.close()
    return user_id


def insert_expense(app, user_id, amount, category, date, description=""):
    """Insert a single expense row and return its id."""
    from database.db import get_db
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description)"
            " VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description),
        )
        db.commit()
        expense_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.close()
    return expense_id
