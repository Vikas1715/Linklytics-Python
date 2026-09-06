"""
test_api.py
-----------
A handful of basic tests covering the main flows described in the project
requirements:
    1. Registration
    2. Login
    3. URL shortening
    4. Invalid URL
    5. Redirect for a valid short code

NOTE ON DATABASE: to keep these tests simple and runnable without needing
a real MySQL server, we point the app at a temporary SQLite file instead
of MySQL just for this test session. The application code itself doesn't
change at all - SQLAlchemy lets us swap the database engine underneath it.
This is a deliberate simplification for testing only; the real app always
uses MySQL (see database.py / .env).

Run with (from the backend/ folder, with the venv active):
    pytest
"""

import os
import sys

# Make sure "import main", "import models" etc. (backend/*.py) work when
# pytest is run from the project root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Point the app at a throwaway SQLite file BEFORE importing the app,
# so nothing ever touches the real MySQL database during tests.
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_linklytics.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ.setdefault("JWT_SECRET", "test_secret")
os.environ.setdefault("BASE_URL", "http://localhost:8000")

from database import Base, get_db  # noqa: E402
import main  # noqa: E402

test_engine = create_engine(
    os.environ["DATABASE_URL"], connect_args={"check_same_thread": False}
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


main.app.dependency_overrides[get_db] = override_get_db

client = TestClient(main.app)


@pytest.fixture(autouse=True, scope="module")
def setup_and_teardown_database():
    """Creates fresh tables before the tests run, and deletes the SQLite
    file afterwards so re-running the tests always starts clean."""
    Base.metadata.create_all(bind=test_engine)
    yield
    test_engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def test_1_register_new_user():
    response = client.post(
        "/api/auth/register",
        json={"username": "testuser", "email": "testuser@example.com", "password": "pass123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["username"] == "testuser"
    assert "access_token" in data


def test_1b_register_duplicate_username_fails():
    response = client.post(
        "/api/auth/register",
        json={"username": "testuser", "email": "different@example.com", "password": "pass123"},
    )
    assert response.status_code == 409


def test_2_login_success():
    response = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "pass123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_2b_login_wrong_password_fails():
    response = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "wrong_password"},
    )
    assert response.status_code == 401


def get_auth_token():
    response = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "pass123"},
    )
    return response.json()["access_token"]


def test_3_shorten_url_success():
    token = get_auth_token()
    response = client.post(
        "/api/url/shorten",
        json={"original_url": "https://www.example.com/some/page"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["short_code"]
    assert data["click_count"] == 0


def test_4_shorten_invalid_url_fails():
    token = get_auth_token()
    response = client.post(
        "/api/url/shorten",
        json={"original_url": "not-a-valid-url"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


def test_5_redirect_valid_short_code():
    token = get_auth_token()
    shorten_response = client.post(
        "/api/url/shorten",
        json={"original_url": "https://www.python.org"},
        headers={"Authorization": f"Bearer {token}"},
    )
    short_code = shorten_response.json()["short_code"]

    # follow_redirects=False so we can inspect the redirect itself
    redirect_response = client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_response.status_code == 302
    assert redirect_response.headers["location"] == "https://www.python.org"


def test_5b_redirect_unknown_code_returns_404():
    response = client.get("/this-code-does-not-exist")
    assert response.status_code == 404
