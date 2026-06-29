import pytest


@pytest.fixture()
def owner(client, auth):
    return auth(client, "owner")


def _setup(client, owner, code, qty=100):
    pid = client.post("/api/products", headers=owner, json={
        "pattern_no": code, "product_code": code, "name": code,
        "product_type": "ROLL", "unit": "SQM", "price": 100}).json()["id"]
    sid = client.post("/api/stock/inward", headers=owner, json={
        "product_id": pid, "warehouse_id": 1, "quantity": qty, "unit": "SQM",
        "item_type": "ROLL", "roll_no": "R1"}).json()["id"]
    return pid, sid


def _saleable(client, owner, code):
    return client.get(f"/api/stock/check?q={code}", headers=owner).json()["results"][0]["total_saleable"]


def test_pending_block_does_not_reduce_saleable(client, owner):
    pid, sid = _setup(client, owner, "BLK-A")
    assert _saleable(client, owner, "BLK-A") == 100
    client.post("/api/blocks", headers=owner, json={
        "product_id": pid, "items": [{"stock_item_id": sid, "qty": 30}], "submit": True})
    assert _saleable(client, owner, "BLK-A") == 100  # pending must not reduce


def test_approved_block_reduces_saleable_and_release_restores(client, owner):
    pid, sid = _setup(client, owner, "BLK-B")
    b = client.post("/api/blocks", headers=owner, json={
        "product_id": pid, "items": [{"stock_item_id": sid, "qty": 40}], "submit": True}).json()
    client.post(f"/api/blocks/{b['id']}/approve", headers=owner)
    assert _saleable(client, owner, "BLK-B") == 60
    client.post(f"/api/blocks/{b['id']}/release", headers=owner)
    assert _saleable(client, owner, "BLK-B") == 100


def test_cannot_overblock_beyond_saleable(client, owner):
    pid, sid = _setup(client, owner, "BLK-C", qty=50)
    b = client.post("/api/blocks", headers=owner, json={
        "product_id": pid, "items": [{"stock_item_id": sid, "qty": 40}], "submit": True}).json()
    client.post(f"/api/blocks/{b['id']}/approve", headers=owner)
    # only 10 saleable now; blocking 20 must fail
    r = client.post("/api/blocks", headers=owner, json={
        "product_id": pid, "items": [{"stock_item_id": sid, "qty": 20}], "submit": True})
    assert r.status_code == 400


def test_convert_to_order_commits_without_double_count(client, owner):
    pid, sid = _setup(client, owner, "BLK-D")
    b = client.post("/api/blocks", headers=owner, json={
        "product_id": pid, "items": [{"stock_item_id": sid, "qty": 40}], "submit": True}).json()
    client.post(f"/api/blocks/{b['id']}/approve", headers=owner)
    assert _saleable(client, owner, "BLK-D") == 60
    r = client.post(f"/api/blocks/{b['id']}/convert-to-order", headers=owner)
    assert r.status_code == 200 and r.json()["order_no"].startswith("ORD-")
    # available reduced to 60 (committed), saleable still 60 (no double count)
    items = client.get(f"/api/stock/items?product_id={pid}", headers=owner).json()["items"]
    assert items[0]["available_qty"] == 60
    assert _saleable(client, owner, "BLK-D") == 60
    assert client.get(f"/api/blocks/{b['id']}", headers=owner).json()["status"] == "CONVERTED"


def test_auto_allocate_block_from_recommendation(client, owner):
    pid, sid = _setup(client, owner, "BLK-E")
    b = client.post("/api/blocks", headers=owner, json={
        "product_id": pid, "auto_allocate": True, "required_qty": 25, "submit": True})
    assert b.status_code == 201
    assert b.json()["required_qty"] == 25


def test_block_rbac(client, auth):
    owner = auth(client, "owner")
    pid, sid = _setup(client, owner, "BLK-F")
    # salesman can create + block_stock
    b = client.post("/api/blocks", headers=auth(client, "salesman"), json={
        "product_id": pid, "items": [{"stock_item_id": sid, "qty": 5}], "submit": True})
    assert b.status_code == 201
    # but cannot approve
    r = client.post(f"/api/blocks/{b.json()['id']}/approve", headers=auth(client, "salesman"))
    assert r.status_code == 403


def test_worker_expiry_flips_status_without_inflating_stock(client, auth):
    from datetime import datetime, timezone, timedelta
    owner = auth(client, "owner")
    pid, sid = _setup(client, owner, "BLK-G")
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    b = client.post("/api/blocks", headers=owner, json={
        "product_id": pid, "items": [{"stock_item_id": sid, "qty": 30}],
        "hold_until": past, "submit": True}).json()
    client.post(f"/api/blocks/{b['id']}/approve", headers=owner)
    assert _saleable(client, owner, "BLK-G") == 70
    # run the worker once
    from app.workers.expire_blocks import release_expired_once
    release_expired_once()
    # block expired -> saleable restored, available unchanged (still 100)
    assert client.get(f"/api/blocks/{b['id']}", headers=owner).json()["status"] == "EXPIRED"
    items = client.get(f"/api/stock/items?product_id={pid}", headers=owner).json()["items"]
    assert items[0]["available_qty"] == 100
    assert _saleable(client, owner, "BLK-G") == 100
