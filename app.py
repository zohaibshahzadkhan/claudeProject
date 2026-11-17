import os
import sqlite3

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import create_user, get_db, get_user_by_email, init_db, seed_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

INVALID_LOGIN_MSG = "Invalid email or password."

DUPLICATE_EMAIL_MSG = "An account with this email already exists."
NAME_MAX_LENGTH = 100
EMAIL_MAX_LENGTH = 254
PASSWORD_MIN_LENGTH = 8

# Hardcoded profile-page data (Step 4). Replaced by database queries in Step 5.
PROFILE_USER = {
    "name": "Demo User",
    "email": "demo@spendly.com",
    "initials": "DU",
    "member_since": "January 2026",
}

PROFILE_STATS = {
    "total_spent": 9210.00,
    "transaction_count": 7,
    "top_category": "Shopping",
    "avg_per_transaction": 1315.71,
}

PROFILE_TRANSACTIONS = [
    {"date": "2026-11-15", "description": "Lunch with colleagues", "category": "Food", "amount": 420.00},
    {"date": "2026-11-14", "description": "Metro card recharge", "category": "Transport", "amount": 500.00},
    {"date": "2026-11-12", "description": "Electricity bill", "category": "Bills", "amount": 1850.00},
    {"date": "2026-11-10", "description": "Pharmacy", "category": "Health", "amount": 310.00},
    {"date": "2026-11-08", "description": "Movie tickets", "category": "Entertainment", "amount": 650.00},
    {"date": "2026-11-05", "description": "Weekly groceries", "category": "Food", "amount": 2280.00},
    {"date": "2026-11-03", "description": "Running shoes", "category": "Shopping", "amount": 3200.00},
]

PROFILE_CATEGORIES = [
    {"name": "Shopping", "total": 3200.00},
    {"name": "Food", "total": 2700.00},
    {"name": "Bills", "total": 1850.00},
    {"name": "Entertainment", "total": 650.00},
    {"name": "Transport", "total": 500.00},
    {"name": "Health", "total": 310.00},
]


def validate_registration(name, email, password, confirm_password):
    """Return an error message for invalid registration input, or None if valid."""
    if not name or not email or not password or not confirm_password:
        return "Name, email, password and password confirmation are all required."
    if len(name) > NAME_MAX_LENGTH:
        return f"Name must be {NAME_MAX_LENGTH} characters or fewer."
    if len(email) > EMAIL_MAX_LENGTH:
        return f"Email must be {EMAIL_MAX_LENGTH} characters or fewer."
    at_index = email.find("@")
    if at_index < 1 or "." not in email[at_index + 1:]:
        return "Please enter a valid email address."
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
    if password != confirm_password:
        return "Passwords do not match."
    return None


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

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    error = validate_registration(name, email, password, confirm_password)
    if error is None and get_user_by_email(email) is not None:
        error = DUPLICATE_EMAIL_MSG

    if error is None:
        try:
            create_user(name, email, generate_password_hash(password))
        except sqlite3.IntegrityError:
            # Another request inserted this email between the lookup and the insert.
            error = DUPLICATE_EMAIL_MSG
        else:
            return redirect(url_for("login"))

    return render_template("register.html", error=error, name=name, email=email), 400


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    user = get_user_by_email(email) if email and password else None
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error=INVALID_LOGIN_MSG, email=email), 400

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template(
        "profile.html",
        user=PROFILE_USER,
        stats=PROFILE_STATS,
        transactions=PROFILE_TRANSACTIONS,
        categories=PROFILE_CATEGORIES,
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
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
