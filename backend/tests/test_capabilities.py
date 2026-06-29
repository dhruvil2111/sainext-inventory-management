import io
import pytest


@pytest.fixture()
def owner(client, auth):
    return auth(client, "owner")


def test_audit_logs_and_meta(client, owner, auth):
    # generate an audit entry
    client.post("/api/warehouses", headers=owner, json={"name": "Audit WH", "code": "WH-AUD"})
    r = client.get("/api/audit-logs", headers=owner)
    assert r.status_code == 200 and r.json()["total"] >= 1
    meta = client.get("/api/audit-logs/meta", headers=owner).json()
    assert "modules" in meta and "actions" in meta
    # non-admin (salesman) blocked
    assert client.get("/api/audit-logs", headers=auth(client, "salesman")).status_code == 403


def test_product_import_valid_and_errors(client, owner):
    csv_data = (
        "pattern_no,product_code,name,product_type,unit,price,status\n"
        "IM-1,IMP-001,Imported A,ROLL,SQM,500,CONTINUED\n"
        ",IMP-002,Missing pattern,ROLL,SQM,100,CONTINUED\n"   # invalid: no pattern
        "IM-3,IMP-003,Imported C,BOX,BOX,300,CONTINUED\n"
    )
    files = {"file": ("p.csv", io.BytesIO(csv_data.encode()), "text/csv")}
    r = client.post("/api/products/import", headers=owner, files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["created"] == 2 and body["failed"] == 1
    assert body["errors"][0]["row"] == 3


def test_product_import_template(client, owner):
    r = client.get("/api/products/import-template", headers=owner)
    assert r.status_code == 200 and "product_code" in r.text


def test_stock_import(client, owner):
    # product + warehouse exist from seed (55440H/PF-102, WH-A)
    csv_data = (
        "product_code,warehouse_code,quantity,unit,item_type,batch_no,inward_date\n"
        "55440H/PF-102,WH-A,25,SQM,ROLL,IMPBATCH,2025-01-15\n"
        "NOPE,WH-A,10,SQM,ROLL,,\n"      # invalid product
    )
    files = {"file": ("s.csv", io.BytesIO(csv_data.encode()), "text/csv")}
    r = client.post("/api/stock/import", headers=owner, files=files)
    assert r.status_code == 200
    assert r.json()["created"] == 1 and r.json()["failed"] == 1


def test_dashboard_analytics(client, owner):
    a = client.get("/api/dashboard/analytics", headers=owner).json()
    assert "movement" in a and "orders_by_status" in a and "top_dues" in a


def test_notifications(client, owner, auth):
    n = client.get("/api/notifications", headers=owner).json()
    assert "count" in n and isinstance(n["items"], list)
    # dispatch user sees a restricted set (no accounts dues item)
    nd = client.get("/api/notifications", headers=auth(client, "dispatch")).json()
    assert all(i["type"] != "dues" for i in nd["items"])
