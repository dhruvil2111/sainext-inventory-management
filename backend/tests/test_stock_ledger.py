import pytest


@pytest.fixture()
def owner(client, auth):
    return auth(client, "owner")


def _new_product(client, owner, code):
    r = client.post("/api/products", headers=owner, json={
        "pattern_no": code, "product_code": code, "name": f"T {code}",
        "product_type": "ROLL", "unit": "SQM", "price": 100})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_inward_posts_ledger(client, owner):
    pid = _new_product(client, owner, "T-INW")
    r = client.post("/api/stock/inward", headers=owner, json={
        "product_id": pid, "warehouse_id": 1, "quantity": 50, "unit": "SQM",
        "item_type": "ROLL", "batch_no": "TB", "roll_no": "1"})
    assert r.status_code == 201 and r.json()["available_qty"] == 50
    led = client.get(f"/api/stock/ledger?product_id={pid}", headers=owner).json()
    assert led["total"] == 1
    e = led["items"][0]
    assert e["txn_type"] == "INWARD" and e["before_qty"] == 0 and e["after_qty"] == 50


def test_adjustment_and_negative_guard(client, owner):
    pid = _new_product(client, owner, "T-ADJ")
    item = client.post("/api/stock/inward", headers=owner, json={
        "product_id": pid, "warehouse_id": 1, "quantity": 20, "unit": "SQM"}).json()
    sid = item["id"]
    # -5 ok
    assert client.post("/api/stock/adjustment", headers=owner,
                       json={"stock_item_id": sid, "delta": -5}).json()["available_qty"] == 15
    # over-adjust blocked
    assert client.post("/api/stock/adjustment", headers=owner,
                       json={"stock_item_id": sid, "delta": -100}).status_code == 400


def test_admin_negative_override(client, auth):
    owner = auth(client, "owner")
    pid = _new_product(client, owner, "T-NEG")
    sid = client.post("/api/stock/inward", headers=owner, json={
        "product_id": pid, "warehouse_id": 1, "quantity": 10, "unit": "SQM"}).json()["id"]
    # admin may force negative with explicit flag
    r = client.post("/api/stock/adjustment", headers=auth(client, "admin"),
                    json={"stock_item_id": sid, "delta": -15, "allow_negative": True})
    assert r.status_code == 200 and r.json()["available_qty"] == -5


def test_transfer_conserves_total(client, owner):
    pid = _new_product(client, owner, "T-TRF")
    sid = client.post("/api/stock/inward", headers=owner, json={
        "product_id": pid, "warehouse_id": 1, "quantity": 60, "unit": "SQM"}).json()["id"]
    r = client.post("/api/stock/transfer", headers=owner,
                    json={"stock_item_id": sid, "to_warehouse_id": 2, "quantity": 25})
    assert r.status_code == 200
    items = client.get(f"/api/stock/items?product_id={pid}", headers=owner).json()["items"]
    by_wh = {i["warehouse_id"]: i["available_qty"] for i in items}
    assert by_wh[1] == 35 and by_wh[2] == 25
    assert sum(i["available_qty"] for i in items) == 60  # conserved
    # same-warehouse transfer rejected
    assert client.post("/api/stock/transfer", headers=owner,
                       json={"stock_item_id": sid, "to_warehouse_id": 1, "quantity": 1}).status_code == 400


def test_damage_reduces_and_guards(client, owner):
    pid = _new_product(client, owner, "T-DMG")
    sid = client.post("/api/stock/inward", headers=owner, json={
        "product_id": pid, "warehouse_id": 1, "quantity": 8, "unit": "SQM"}).json()["id"]
    assert client.post("/api/stock/damage", headers=owner,
                       json={"stock_item_id": sid, "quantity": 3}).json()["available_qty"] == 5
    assert client.post("/api/stock/damage", headers=owner,
                       json={"stock_item_id": sid, "quantity": 99}).status_code == 400


def test_duplicate_product_code_rejected(client, owner):
    _new_product(client, owner, "T-DUP")
    r = client.post("/api/products", headers=owner, json={
        "pattern_no": "x", "product_code": "T-DUP", "name": "dup"})
    assert r.status_code == 409


def test_categories_create_and_list(client, owner):
    r = client.post("/api/products/categories", headers=owner,
                    json={"name": "Test Cat", "description": "d"})
    assert r.status_code == 201
    cats = client.get("/api/products/categories", headers=owner).json()
    assert any(c["name"] == "Test Cat" for c in cats)
