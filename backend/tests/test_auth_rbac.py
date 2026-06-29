def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_login_and_me(client, auth):
    h = auth(client, "owner")
    me = client.get("/api/auth/me", headers=h).json()
    assert me["role_name"] == "Owner"
    assert len(me["permissions"]) > 30  # owner sees all


def test_wrong_password_rejected(client):
    r = client.post("/api/auth/login", data={"username": "owner@sainext.app", "password": "nope"})
    assert r.status_code == 401


def test_salesman_blocked_from_users(client, auth):
    # Salesman lacks Users:view -> backend must enforce (403), not just hide UI.
    r = client.get("/api/users", headers=auth(client, "salesman"))
    assert r.status_code == 403


def test_salesman_cannot_inward(client, auth):
    r = client.post("/api/stock/inward", headers=auth(client, "salesman"),
                    json={"product_id": 1, "warehouse_id": 1, "quantity": 1, "unit": "SQM"})
    assert r.status_code == 403


def test_role_permission_update_and_delete(client, auth):
    h = auth(client, "owner")
    roles = client.get("/api/roles", headers=h).json()
    mgr = next(r for r in roles if r["name"] == "Manager")
    new_codes = list(set(mgr["permission_codes"]) | {"Dispatch:edit"})
    r = client.put(f"/api/roles/{mgr['id']}/permissions", headers=h,
                   json={"permission_codes": new_codes})
    assert r.status_code == 200 and "Dispatch:edit" in r.json()["permission_codes"]
    # system roles cannot be deleted
    assert client.delete(f"/api/roles/{mgr['id']}", headers=h).status_code == 400


def test_per_user_overrides(client, auth):
    h = auth(client, "owner")
    # find the salesman user id
    users = client.get("/api/users", headers=h).json()["items"]
    sales = next(u for u in users if u["email"] == "salesman@sainext.app")
    # grant Users:view via override, deny Orders:create
    r = client.put(f"/api/users/{sales['id']}/overrides", headers=h,
                   json={"allow": ["Users:view"], "deny": ["Orders:create"]})
    assert r.status_code == 200
    perms = r.json()
    assert "Users:view" in perms["effective"]
    assert "Orders:create" not in perms["effective"]
    # now the salesman token should be allowed to list users
    assert client.get("/api/users", headers=auth(client, "salesman")).status_code == 200
    # clean up overrides so other tests are unaffected
    client.put(f"/api/users/{sales['id']}/overrides", headers=h, json={"allow": [], "deny": []})
