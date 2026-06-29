import pytest


@pytest.fixture()
def owner(client, auth):
    return auth(client, "owner")


def test_branding_any_authenticated(client, auth):
    # even a salesman (no Settings perm) can read branding
    r = client.get("/api/settings/branding", headers=auth(client, "salesman"))
    assert r.status_code == 200
    b = r.json()
    assert b["company_name"] and b["brand_accent"].startswith("#")


def test_settings_view_requires_permission(client, auth):
    assert client.get("/api/settings", headers=auth(client, "salesman")).status_code == 403
    assert client.get("/api/settings", headers=auth(client, "owner")).status_code == 200


def test_settings_upsert(client, owner, auth):
    r = client.put("/api/settings", headers=owner, json={"key": "brand_accent", "value": "#ff0000"})
    assert r.status_code == 200
    assert client.get("/api/settings/branding", headers=owner).json()["brand_accent"] == "#ff0000"
    # editing requires Settings:edit -> salesman blocked
    assert client.put("/api/settings", headers=auth(client, "salesman"),
                      json={"key": "company_name", "value": "Hax"}).status_code == 403
    # restore
    client.put("/api/settings", headers=owner, json={"key": "brand_accent", "value": "#f5a623"})


def test_seed_demo_order_exists(client, owner):
    # seed creates at least one demo order
    assert client.get("/api/orders", headers=owner).json()["total"] >= 1
