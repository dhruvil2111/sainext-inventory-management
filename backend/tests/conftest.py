"""Pytest fixtures. Runs the app against an isolated SQLite database so the
suite needs no Postgres. DATABASE_URL must be set before importing app modules.
"""
import os
import tempfile
import warnings

warnings.filterwarnings("ignore")

# Point the app at a throwaway sqlite file BEFORE importing any app module.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-32xx"
os.environ["SEED_ON_STARTUP"] = "false"
os.environ["ENV"] = "test"            # disables rate limiting during tests

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.seed import run_seed


@pytest.fixture(scope="session", autouse=True)
def _seed():
    run_seed()
    yield
    try:
        os.remove(_db_path)
    except OSError:
        pass


@pytest.fixture()
def client():
    return TestClient(app)


def _token(client, email, password):
    r = client.post("/api/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture()
def auth():
    """Returns a helper -> auth header dict for a given role's demo account."""
    creds = {
        "owner": ("owner@sainext.app", "Owner@123"),
        "admin": ("admin@sainext.app", "Admin@123"),
        "manager": ("manager@sainext.app", "Manager@123"),
        "salesman": ("salesman@sainext.app", "Sales@123"),
        "dispatch": ("dispatch@sainext.app", "Dispatch@123"),
        "accounts": ("accounts@sainext.app", "Accounts@123"),
    }

    def _make(client, role="owner"):
        email, pw = creds[role]
        return {"Authorization": f"Bearer {_token(client, email, pw)}"}

    return _make
