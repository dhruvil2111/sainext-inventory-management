import pytest


@pytest.fixture()
def owner(client, auth):
    return auth(client, "owner")


def test_dealers_list_and_create(client, owner):
    before = client.get("/api/dealers", headers=owner).json()["total"]
    r = client.post("/api/dealers", headers=owner, json={
        "firm_name": "QA Dealer", "credit_period_days": 20, "rating": 4.1})
    assert r.status_code == 201
    after = client.get("/api/dealers", headers=owner).json()["total"]
    assert after == before + 1


def test_salesman_dealer_scoping(client, auth):
    owner = auth(client, "owner")
    # all seeded dealers assigned to the salesman -> salesman sees them; total <= owner total
    owner_total = client.get("/api/dealers", headers=owner).json()["total"]
    sales_total = client.get("/api/dealers", headers=auth(client, "salesman")).json()["total"]
    assert sales_total <= owner_total


def test_dealer_dashboard(client, owner):
    did = client.get("/api/dealers", headers=owner).json()["items"][0]["id"]
    d = client.get(f"/api/dealers/{did}/dashboard", headers=owner).json()
    assert "outstanding" in d and "payment_history" in d


def test_salesman_dashboard_target(client, auth):
    d = client.get("/api/salesman/dashboard", headers=auth(client, "salesman")).json()
    assert d["monthly_target"] == 100000.0
    assert "target_achieved" in d and "dealers" in d


def test_accounts_dashboard_and_payment(client, auth):
    owner = auth(client, "owner")
    acc = auth(client, "accounts")
    dash = client.get("/api/accounts/dashboard", headers=acc).json()
    assert dash["total_outstanding"] > 0
    did = client.get("/api/dealers", headers=owner).json()["items"][0]["id"]
    p = client.post("/api/dealers/payments", headers=acc,
                    json={"dealer_id": did, "amount": 5000, "type": "PAYMENT"})
    assert p.status_code == 201


def test_reports_all_types(client, owner):
    for rep in ["stock", "ledger", "orders", "blocks", "dispatch", "payments"]:
        r = client.get(f"/api/reports/{rep}", headers=owner)
        assert r.status_code == 200
        assert "columns" in r.json() and "rows" in r.json()
    assert client.get("/api/reports/nope", headers=owner).status_code == 404


def test_report_exports(client, owner):
    csv_r = client.get("/api/reports/stock/export?format=csv", headers=owner)
    assert csv_r.status_code == 200 and "csv" in csv_r.headers["content-type"]
    xlsx_r = client.get("/api/reports/payments/export?format=xlsx", headers=owner)
    assert xlsx_r.status_code == 200 and len(xlsx_r.content) > 500


def test_phase7_rbac(client, auth):
    # salesman cannot see accounts dashboard
    assert client.get("/api/accounts/dashboard", headers=auth(client, "salesman")).status_code == 403
    # dispatch cannot export reports (no Reports:export)
    assert client.get("/api/reports/stock/export?format=csv",
                      headers=auth(client, "dispatch")).status_code == 403
