import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _parse_date_filter(args):
    raw_from = args.get("from", "").strip()
    raw_to   = args.get("to",   "").strip()
    if raw_from and raw_to:
        try:
            dt_from = datetime.strptime(raw_from, "%Y-%m-%d")
            dt_to   = datetime.strptime(raw_to,   "%Y-%m-%d")
            if dt_from <= dt_to:
                return raw_from, raw_to, True
        except ValueError:
            pass
    return None, None, False


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name     = request.form.get("name",            "").strip()
    email    = request.form.get("email",           "").strip().lower()
    password = request.form.get("password",        "").strip()
    confirm  = request.form.get("confirm_password","").strip()

    if not name or not email or not password or not confirm:
        return render_template("register.html", error="All fields are required.", name=name, email=email)
    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.", name=name, email=email)
    if password != confirm:
        return render_template("register.html", error="Passwords do not match.", name=name, email=email)

    try:
        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return render_template("register.html", error="An account with that email already exists.", name=name, email=email)
    finally:
        db.close()

    flash("Registration successful. Please log in.")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("login.html")

    email    = request.form.get("email",    "").strip().lower()
    password = request.form.get("password", "").strip()

    if not email or not password:
        return render_template("login.html", error="All fields are required.", email=email)

    db = get_db()
    try:
        user = db.execute(
            "SELECT id, name, password_hash FROM users WHERE email = ?",
            (email,)
        ).fetchone()
    finally:
        db.close()

    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.", email=email)

    session["user_id"]   = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("landing"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    date_from, date_to, is_filtered = _parse_date_filter(request.args)

    if is_filtered:
        filter_clause  = " AND date BETWEEN ? AND ?"
        expense_params = (session["user_id"], date_from, date_to)
    else:
        filter_clause  = ""
        expense_params = (session["user_id"],)

    db = get_db()
    try:
        user = db.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?",
            (session["user_id"],)
        ).fetchone()

        if user is None:
            session.clear()
            return redirect(url_for("landing"))

        total_spend = db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM expenses"
            " WHERE user_id = ?" + filter_clause,
            expense_params
        ).fetchone()[0]

        category_spends = db.execute(
            "SELECT category, SUM(amount) as total FROM expenses"
            " WHERE user_id = ?" + filter_clause +
            " GROUP BY category ORDER BY total DESC",
            expense_params
        ).fetchall()

        top_3 = db.execute(
            "SELECT amount, category, description, date FROM expenses"
            " WHERE user_id = ?" + filter_clause +
            " ORDER BY amount DESC LIMIT 3",
            expense_params
        ).fetchall()
    finally:
        db.close()

    joined = datetime.strptime(user["created_at"], "%Y-%m-%d %H:%M:%S").strftime("%B %d, %Y")
    return render_template(
        "profile.html",
        user=user,
        joined=joined,
        total_spend=total_spend,
        category_spends=category_spends,
        top_3=top_3,
        date_from=date_from,
        date_to=date_to,
        is_filtered=is_filtered,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", port=5001)
