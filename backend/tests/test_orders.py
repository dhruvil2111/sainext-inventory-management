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


def _avail(client, owner, pid):
    return client.get(f"/api/stock/items?product_id={pid}", headers=owner).json()["items"][0]["available_qty"]


def test_pending_order_not_committed(client, owner):
    pid, sid = _setup(client, owner, "O-A")
    o = client.post("/api/orders", headers=owner, json={
        "product_id": pid, "allocations": [{"stock_item_id": sid, "qty": 30}], "submit": True}).json()
    assert o["status"] == "PENDING_APPROVAL" and o["stock_committed"] is False
    assert _saleable(client, owner, "O-A") == 100   # pending doesn't reduce


def test_commit_on_approval(client, owner):
    pid, sid = _setup(client, owner, "O-B")
    o = client.post("/api/orders", headers=owner, json={
        "product_id": pid, "allocations": [{"stock_item_id": sid, "qty": 40}], "submit": True}).json()
    client.post(f"/api/orders/{o['id']}/approve", headers=owner)
    assert _avail(client, owner, pid) == 60 and _saleable(client, owner, "O-B") == 60


def test_dispatch_flow_no_double_deduct(client, owner):
    pid, sid = _setup(client, owner, "O-C")
    o = client.post("/api/orders", headers=owner, json={
        "product_id": pid, "allocations": [{"stock_item_id": sid, "qty": 25}], "submit": True}).json()
    client.post(f"/api/orders/{o['id']}/approve", headers=owner)
    assert _avail(client, owner, pid) == 75
    for step in ["in-process", "ready-for-dispatch", "dispatched", "completed"]:
        assert client.post(f"/api/orders/{o['id']}/{step}", headers=owner).status_code == 200
    assert _avail(client, owner, pid) == 75   # never deducted again
    assert client.get(f"/api/orders/{o['id']}", headers=owner).json()["status"] == "COMPLETED"


def test_invalid_transition_blocked(client, owner):
    pid, sid = _setup(client, owner, "O-D")
    o = client.post("/api/orders", headers=owner, json={
        "product_id": pid, "allocations": [{"stock_item_id": sid, "qty": 10}], "submit": True}).json()
    # cannot dispatch a pending order
    assert client.post(f"/api/orders/{o['id']}/dispatched", headers=owner).status_code == 400


def test_cancel_releases_committed_stock(client, owner):
    pid, sid = _setup(client, owner, "O-E")
    o = client.post("/api/orders", headers=owner, json={
        "product_id": pid, "allocations": [{"stock_item_id": sid, "qty": 40}], "submit": True}).json()
    client.post(f"/api/orders/{o['id']}/approve", headers=owner)
    assert _avail(client, owner, pid) == 60
    client.post(f"/api/orders/{o['id']}/cancel", headers=owner)
    assert _avail(client, owner, pid) == 100   # released
    assert client.get(f"/api/orders/{o['id']}", headers=owner).json()["status"] == "CANCELLED"


def test_cannot_approve_beyond_saleable(client, owner):
    pid, sid = _setup(client, owner, "O-F", qty=50)
    # two pending orders for 40 each; first approves, second must fail (only 10 left)
    o1 = client.post("/api/orders", headers=owner, json={
        "product_id": pid, "allocations": [{"stock_item_id": sid, "qty": 40}], "submit": True}).json()
    o2 = client.post("/api/orders", headers=owner, json={
        "product_id": pid, "allocations": [{"stock_item_id": sid, "qty": 40}], "submit": True}).json()
    assert client.post(f"/api/orders/{o1['id']}/approve", headers=owner).status_code == 200
    assert client.post(f"/api/orders/{o2['id']}/approve", headers=owner).status_code == 400


def test_order_rbac_and_dispatch_team(client, auth):
    owner = auth(client, "owner")
    pid, sid = _setup(client, owner, "O-G")
    # salesman can create, not approve
    o = client.post("/api/orders", headers=auth(client, "salesman"), json={
        "product_id": pid, "allocations": [{"stock_item_id": sid, "qty": 10}], "submit": True}).json()
    assert client.post(f"/api/orders/{o['id']}/approve", headers=auth(client, "salesman")).status_code == 403
    client.post(f"/api/orders/{o['id']}/approve", headers=owner)
    # dispatch team can run dispatch transitions (Dispatch:edit)
    assert client.post(f"/api/orders/{o['id']}/in-process", headers=auth(client, "dispatch")).status_code == 200
