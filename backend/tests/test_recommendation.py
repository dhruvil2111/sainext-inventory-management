import pytest


@pytest.fixture()
def owner(client, auth):
    return auth(client, "owner")


def _prod(client, owner, code):
    return client.post("/api/products", headers=owner, json={
        "pattern_no": code, "product_code": code, "name": code,
        "product_type": "ROLL", "unit": "SQM", "standard_roll_qty": 60,
        "price": 100}).json()["id"]


def _in(client, owner, pid, wh, qty, batch, bdate, roll, itype="ROLL"):
    return client.post("/api/stock/inward", headers=owner, json={
        "product_id": pid, "warehouse_id": wh, "quantity": qty, "unit": "SQM",
        "item_type": itype, "batch_no": batch, "batch_date": bdate, "roll_no": roll})


def _reco(client, owner, pid, qty, wh=None):
    return client.post("/api/stock/recommendation", headers=owner,
                       json={"product_id": pid, "required_qty": qty, "warehouse_id": wh}).json()


def test_case1_nearest_above_min_wastage(client, owner):
    pid = _prod(client, owner, "R-C1")
    _in(client, owner, pid, 1, 39, "24CA", "2024-03-25", "L1", "LOOSE")
    _in(client, owner, pid, 1, 48, "24CA", "2024-08-03", "L2", "LOOSE")
    _in(client, owner, pid, 1, 60, "25CB", "2025-03-25", "R1", "ROLL")
    top = _reco(client, owner, pid, 38)["options"][0]
    assert len(top["picks"]) == 1
    assert top["picks"][0]["source_qty"] == 39   # nearest above, not 48 / 60
    assert top["total_wastage"] == 1.0
    assert top["picks"][0]["remaining_qty"] == 1.0  # partial cut leaves loose remainder


def test_case2_full_roll_plus_min_waste_partial(client, owner):
    pid = _prod(client, owner, "R-C2")
    _in(client, owner, pid, 1, 60, "B1", "2024-01-01", "FR")
    _in(client, owner, pid, 1, 38, "B1", "2024-02-01", "L38", "LOOSE")
    _in(client, owner, pid, 1, 52, "B1", "2024-03-01", "L52", "LOOSE")
    top = _reco(client, owner, pid, 89)["options"][0]
    assert top["total_allocated"] == 89
    assert top["fulfilled"] is True
    assert top["total_wastage"] == 9.0           # 60 full + cut 29 from the 38 (leftover 9)
    full = [p for p in top["picks"] if p["is_full_roll"]]
    cut = [p for p in top["picks"] if not p["is_full_roll"]]
    assert any(p["source_qty"] == 60 for p in full)
    assert cut[0]["source_qty"] == 38 and cut[0]["alloc_qty"] == 29


def test_old_stock_first(client, owner):
    pid = _prod(client, owner, "R-OLD")
    _in(client, owner, pid, 1, 50, "NEW", "2025-05-01", "RN")
    _in(client, owner, pid, 1, 50, "OLD", "2023-01-01", "RO")
    top = _reco(client, owner, pid, 40)["options"][0]
    assert top["picks"][0]["batch_no"] == "OLD"


def test_same_batch_preference(client, owner):
    pid = _prod(client, owner, "R-SB")
    # batch A can fulfil 70 on its own (40+40); batch B also has stock
    _in(client, owner, pid, 1, 40, "A", "2024-01-01", "A1")
    _in(client, owner, pid, 1, 40, "A", "2024-01-02", "A2")
    _in(client, owner, pid, 1, 40, "B", "2023-12-01", "B1")
    res = _reco(client, owner, pid, 70)
    # at least one option keeps everything within a single batch
    assert any(o["same_batch"] for o in res["options"])


def test_cannot_fulfill_flag(client, owner):
    pid = _prod(client, owner, "R-NF")
    _in(client, owner, pid, 1, 10, "X", "2024-01-01", "X1")
    res = _reco(client, owner, pid, 999)
    assert res["can_fulfill"] is False
    # any returned option is marked not fulfilled
    assert all(o["fulfilled"] is False for o in res["options"]) or res["options"] == []


def test_requires_positive_qty(client, owner):
    pid = _prod(client, owner, "R-Z")
    r = client.post("/api/stock/recommendation", headers=owner,
                    json={"product_id": pid, "required_qty": 0})
    assert r.status_code == 422
