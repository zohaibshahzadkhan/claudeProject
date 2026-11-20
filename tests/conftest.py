import sys
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database.db as db  # noqa: E402
from app import app as flask_app  # noqa: E402


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Point the app at a throwaway SQLite file seeded with the demo user and expenses."""
    path = tmp_path / "test_spendly.db"
    monkeypatch.setattr(db, "DB_PATH", path)
    db.init_db()
    db.seed_db()
    return path


@pytest.fixture
def client(test_db):
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as test_client:
        yield test_client


@pytest.fixture
def seed_user_id(test_db):
    return db.get_user_by_email("demo@spendly.com")["id"]


@pytest.fixture
def auth_client(client, seed_user_id):
    """A test client with the seeded demo user logged in via the session."""
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id
        sess["user_name"] = "Demo User"
    return client


@pytest.fixture
def empty_user_id(test_db):
    """A registered user with no expenses."""
    return db.create_user(
        "New Person", "new@example.com", generate_password_hash("password123")
    )
