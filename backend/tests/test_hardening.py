import pytest


@pytest.fixture()
def owner(client, auth):
    return auth(client, "owner")


def _login(client, email="owner@sainext.app", pw="Owner@123"):
    return client.post("/api/auth/login", data={"username": email, "password": pw}).json()


def test_login_returns_access_and_refresh(client):
    tok = _login(client)
    assert tok["access_token"] and tok["refresh_token"]
    assert tok["token_type"] == "bearer"


def test_refresh_issues_new_tokens(client):
    tok = _login(client)
    r = client.post("/api/auth/refresh", json={"refresh_token": tok["refresh_token"]})
    assert r.status_code == 200
    new = r.json()
    assert new["access_token"] and new["refresh_token"]
    # new access works on a protected route
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {new['access_token']}"})
    assert me.status_code == 200


def test_refresh_token_cannot_authenticate(client):
    tok = _login(client)
    # using a refresh token as a bearer access token must be rejected
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok['refresh_token']}"})
    assert r.status_code == 401


def test_logout_revokes_refresh(client):
    tok = _login(client)
    access = {"Authorization": f"Bearer {tok['access_token']}"}
    out = client.post("/api/auth/logout", headers=access, json={"refresh_token": tok["refresh_token"]})
    assert out.status_code == 200
    # the revoked refresh token can no longer mint new tokens
    r = client.post("/api/auth/refresh", json={"refresh_token": tok["refresh_token"]})
    assert r.status_code == 401


def test_refresh_rotation_invalidates_old(client):
    tok = _login(client)
    first = client.post("/api/auth/refresh", json={"refresh_token": tok["refresh_token"]})
    assert first.status_code == 200
    # the original refresh token was rotated (revoked) on use
    again = client.post("/api/auth/refresh", json={"refresh_token": tok["refresh_token"]})
    assert again.status_code == 401


def test_password_min_length_enforced(client, owner):
    roles = client.get("/api/roles", headers=owner).json()
    rid = roles[0]["id"]
    r = client.post("/api/users", headers=owner, json={
        "name": "Weak", "email": "weak@sainext.app", "role_id": rid, "password": "123"})
    assert r.status_code == 422  # min_length=6


def test_security_headers_present(client):
    r = client.get("/api/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "Referrer-Policy" in r.headers
