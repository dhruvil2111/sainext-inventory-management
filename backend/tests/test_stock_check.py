import pytest


@pytest.fixture()
def owner(client, auth):
    return auth(client, "owner")


def _mk(client, owner, code, wh, qty, batch=None, bdate=None, item_type="ROLL"):
    pid = client.post("/api/products", headers=owner, json={
        "pattern_no": code, "product_code": code, "name": f"N {code}",
        "product_type": item_type, "unit": "SQM", "price": 300}).json()["id"]
    client.post("/api/stock/inward", headers=owner, json={
        "product_id": pid, "warehouse_id": wh, "quantity": qty, "unit": "SQM",
        "item_type": item_type, "batch_no": batch, "batch_date": bdate})
    return pid


def test_check_requires_search_term(client, owner):
    assert client.get("/api/stock/check", headers=owner).status_code == 422


def test_check_warehouse_status_colors(client, owner):
    code = "CHK-1"
    pid = _mk(client, owner, code, 1, 60, batch="B1", bdate="2024-01-01")
    client.post("/api/stock/inward", headers=owner, json={
        "product_id": pid, "warehouse_id": 2, "quantity": 30, "unit": "SQM",
        "item_type": "ROLL", "batch_no": "B2", "batch_date": "2025-01-01"})
    r = client.get(f"/api/stock/check?q={code}&required_qty=50", headers=owner).json()
    res = r["results"][0]
    assert res["total_available"] == 90
    assert res["total_saleable"] == 90
    assert res["status"] == "green" and res["can_fulfill"] is True
    by_wh = {w["warehouse_id"]: w for w in res["warehouses"]}
    assert by_wh[1]["status"] == "green"   # 60 >= 50
    assert by_wh[2]["status"] == "yellow"  # 30 < 50 (partial)


def test_check_red_when_required_exceeds(client, owner):
    code = "CHK-2"
    _mk(client, owner, code, 1, 10)
    r = client.get(f"/api/stock/check?q={code}&required_qty=999", headers=owner).json()
    res = r["results"][0]
    assert res["can_fulfill"] is False and res["status"] == "yellow"  # 10 available, partial


def test_check_batch_old_stock_order(client, owner):
    code = "CHK-3"
    pid = _mk(client, owner, code, 1, 20, batch="NEW", bdate="2025-05-01")
    client.post("/api/stock/inward", headers=owner, json={
        "product_id": pid, "warehouse_id": 1, "quantity": 20, "unit": "SQM",
        "item_type": "ROLL", "batch_no": "OLD", "batch_date": "2023-01-01"})
    res = client.get(f"/api/stock/check?q={code}", headers=owner).json()["results"][0]
    # batches sorted old-stock-first by batch_date
    assert res["batches"][0]["batch_no"] == "OLD"


def test_check_price_and_batch_gating(client, auth):
    owner = auth(client, "owner")
    code = "CHK-4"
    _mk(client, owner, code, 1, 5)

    # Salesman: can see price + batch detail
    js = client.get(f"/api/stock/check?q={code}", headers=auth(client, "salesman")).json()
    assert js["can_view_price"] and js["can_view_batch_details"]
    assert js["results"][0]["product"]["price"] is not None
    assert "items" in js["results"][0]

    # Dispatch: Stock Check:view only -> no price, no batch detail
    jd = client.get(f"/api/stock/check?q={code}", headers=auth(client, "dispatch")).json()
    assert jd["can_view_price"] is False and jd["can_view_batch_details"] is False
    assert jd["results"][0]["product"]["price"] is None
    assert "items" not in jd["results"][0]
