import math
import os
import sqlite3
from datetime import date, datetime

from flask import Flask, abort, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import (
    create_user,
    delete_expense as delete_expense_row,
    get_category_breakdown,
    get_db,
    get_expense_by_id,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_email,
    get_user_by_id,
    init_db,
    insert_expense,
    seed_db,
    update_expense,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024  # bound the size of any request body

INVALID_LOGIN_MSG = "Invalid email or password."

DUPLICATE_EMAIL_MSG = "An account with this email already exists."
NAME_MAX_LENGTH = 100
EMAIL_MAX_LENGTH = 254
PASSWORD_MIN_LENGTH = 8

# Must match the category names seeded in database/db.py.
EXPENSE_CATEGORIES = (
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
)
DESCRIPTION_MAX_LENGTH = 200
AMOUNT_MAX = 10_000_000


def validate_registration(name, email, password, confirm_password):
    """Return an error message for invalid registration input, or None if valid."""
    if not name or not email or not password or not confirm_password:
        return "Name, email, password and password confirmation are all required."
    if len(name) > NAME_MAX_LENGTH:
        return f"Name must be {NAME_MAX_LENGTH} characters or fewer."
    if len(email) > EMAIL_MAX_LENGTH:
        return f"Email must be {EMAIL_MAX_LENGTH} characters or fewer."
    at_index = email.find("@")
    if at_index < 1 or "." not in email[at_index + 1 :]:
        return "Please enter a valid email address."
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
    if password != confirm_password:
        return "Passwords do not match."
    return None


def validate_expense(amount_raw, category, date_raw, description_raw):
    """Return (error, cleaned). error is a message or None; cleaned holds typed values when valid."""
    amount_raw = amount_raw.strip()
    date_raw = date_raw.strip()
    try:
        amount = float(amount_raw)
    except ValueError:
        return "Please enter a valid amount.", None
    if not math.isfinite(amount):
        return "Please enter a valid amount.", None
    amount = round(amount, 2)
    if amount <= 0:
        return "Amount must be greater than 0.", None
    if amount > AMOUNT_MAX:
        return f"Amount must be {AMOUNT_MAX:,} or less.", None
    if category not in EXPENSE_CATEGORIES:
        return "Please choose a valid category.", None
    try:
        parsed = datetime.strptime(date_raw, "%Y-%m-%d")
    except ValueError:
        return "Please enter a valid date.", None
    # strptime accepts non-padded values such as 2026-1-5; keep only canonical YYYY-MM-DD.
    if parsed.strftime("%Y-%m-%d") != date_raw:
        return "Please enter a valid date.", None
    description = description_raw.strip() or None
    if description and len(description) > DESCRIPTION_MAX_LENGTH:
        return (
            f"Description must be {DESCRIPTION_MAX_LENGTH} characters or fewer.",
            None,
        )
    return None, {
        "amount": amount,
        "category": category,
        "date": date_raw,
        "description": description,
    }


def render_expense_form(form=None, error=None):
    """Render the add-expense form with the shared categories, default date and limits."""
    return render_template(
        "add_expense.html",
        categories=EXPENSE_CATEGORIES,
        today=date.today().isoformat(),
        max_description=DESCRIPTION_MAX_LENGTH,
        form=form or {},
        error=error,
    )


def render_edit_form(expense, form=None, error=None):
    """Render the edit-expense form. form holds submitted values on a failed POST, else expense is shown."""
    return render_template(
        "edit_expense.html",
        expense=expense,
        categories=EXPENSE_CATEGORIES,
        max_description=DESCRIPTION_MAX_LENGTH,
        form=form,
        error=error,
    )


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


def parse_date_arg(name):
    """Return the query arg as a strict YYYY-MM-DD string, None if blank, or abort(400)."""
    raw = request.args.get(name, "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        abort(400)
    # strptime accepts non-padded values such as 2026-1-5; reject anything not in canonical form.
    if parsed.strftime("%Y-%m-%d") != raw:
        abort(400)
    return raw


def build_range_label(start_date, end_date):
    """Human-readable description of the active date range."""
    if start_date and end_date:
        return f"{start_date} to {end_date}"
    if start_date:
        return f"From {start_date}"
    if end_date:
        return f"Until {end_date}"
    return "All time"


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    start_date = parse_date_arg("start_date")
    end_date = parse_date_arg("end_date")
    if start_date and end_date and start_date > end_date:
        abort(400)

    date_range = {"start_date": start_date, "end_date": end_date}
    return render_template(
        "profile.html",
        user=user,
        stats=get_summary_stats(user_id, **date_range),
        transactions=get_recent_transactions(user_id, **date_range),
        categories=get_category_breakdown(user_id, **date_range),
        start_date=start_date,
        end_date=end_date,
        filter_active=bool(start_date or end_date),
        range_label=build_range_label(start_date, end_date),
    )


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_expense_form()

    form = {
        "amount": request.form.get("amount", ""),
        "category": request.form.get("category", ""),
        "date": request.form.get("date", ""),
        "description": request.form.get("description", ""),
    }
    error, cleaned = validate_expense(
        form["amount"], form["category"], form["date"], form["description"]
    )
    if error:
        return render_expense_form(form, error)

    insert_expense(
        session["user_id"],
        cleaned["amount"],
        cleaned["category"],
        cleaned["date"],
        cleaned["description"],
    )
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, session["user_id"])
    if expense is None:
        abort(404)

    if request.method == "GET":
        return render_edit_form(expense)

    form = {
        "amount": request.form.get("amount", ""),
        "category": request.form.get("category", ""),
        "date": request.form.get("date", ""),
        "description": request.form.get("description", ""),
    }
    error, cleaned = validate_expense(
        form["amount"], form["category"], form["date"], form["description"]
    )
    if error:
        return render_edit_form(expense, form, error)

    updated = update_expense(
        id,
        session["user_id"],
        cleaned["amount"],
        cleaned["category"],
        cleaned["date"],
        cleaned["description"],
    )
    if not updated:
        abort(404)
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    deleted = delete_expense_row(id, session["user_id"])
    if not deleted:
        abort(404)
    return redirect(url_for("profile"))


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=5001)
