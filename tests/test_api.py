"""Smoke tests for the REST API and authentication guard."""
from __future__ import annotations


def test_api_requires_authentication(client):
    # Unauthenticated API calls get a 401 JSON body, not a redirect.
    res = client.get("/api/expenses")
    assert res.status_code == 401
    assert res.is_json
    assert "error" in res.get_json()


def test_dashboard_endpoint_shape(auth_client):
    res = auth_client.get("/api/dashboard")
    assert res.status_code == 200
    data = res.get_json()
    assert set(data.keys()) == {"kpis", "charts", "bank_accounts"}
    assert "available_balance" in data["kpis"]
    assert "expenses_by_month" in data["charts"]


def test_expenses_endpoint_lists_created_expense(auth_client, services, admin_user):
    services["expense"].create_expense(
        description="API expense", amount="1234.56", created_by=admin_user.id
    )
    res = auth_client.get("/api/expenses")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["count"] == 1
    assert payload["data"][0]["amount"] == 1234.56


def test_expense_status_filter_validation(auth_client):
    res = auth_client.get("/api/expenses?status=BOGUS")
    assert res.status_code == 422


def test_get_single_expense_404(auth_client):
    res = auth_client.get("/api/expenses/999")
    assert res.status_code == 404
    assert res.is_json


def test_healthz(client):
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"
