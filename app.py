import os
import sqlite3

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import (
    create_user,
    get_category_breakdown,
    get_db,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_email,
    get_user_by_id,
    init_db,
    seed_db,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

INVALID_LOGIN_MSG = "Invalid email or password."

DUPLICATE_EMAIL_MSG = "An account with this email already exists."
NAME_MAX_LENGTH = 100
EMAIL_MAX_LENGTH = 254
PASSWORD_MIN_LENGTH = 8

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
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    return render_template(
        "profile.html",
        user=user,
        stats=get_summary_stats(user_id),
        transactions=get_recent_transactions(user_id),
        categories=get_category_breakdown(user_id),
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
