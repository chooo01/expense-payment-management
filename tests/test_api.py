"""Tests for the REST API: token auth, endpoints and the OpenAPI document."""
from __future__ import annotations


# --- Authentication ---------------------------------------------------------
def test_api_requires_authentication(client):
    # Without a Bearer token the API returns a 401 JSON body, not a redirect.
    res = client.get("/api/expenses")
    assert res.status_code == 401
    assert res.is_json
    assert "error" in res.get_json()


def test_create_token_success(client, admin_user):
    res = client.post("/api/tokens", json={"username": "admin", "password": "Admin123*"})
    assert res.status_code == 200
    body = res.get_json()
    assert body["token"]
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] == 3600


def test_create_token_bad_credentials(client, admin_user):
    res = client.post("/api/tokens", json={"username": "admin", "password": "wrong"})
    assert res.status_code == 401
    assert res.is_json
    assert "error" in res.get_json()


def test_token_grants_access(client, api_headers, admin_user):
    res = client.get("/api/expenses", headers=api_headers)
    assert res.status_code == 200


# --- Endpoints --------------------------------------------------------------
def test_dashboard_endpoint_shape(client, api_headers):
    res = client.get("/api/dashboard", headers=api_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert set(data.keys()) == {"kpis", "charts", "bank_accounts"}
    assert "available_balance" in data["kpis"]
    assert "expenses_by_month" in data["charts"]


def test_expenses_endpoint_lists_created_expense(client, api_headers, services, admin_user):
    services["expense"].create_expense(
        description="API expense", amount="1234.56", created_by=admin_user.id
    )
    res = client.get("/api/expenses", headers=api_headers)
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["count"] == 1
    assert payload["data"][0]["amount"] == 1234.56
    assert payload["data"][0]["status"] == "PENDING"


def test_expense_status_filter_validation(client, api_headers):
    # Invalid enum value -> APIFairy/marshmallow validation error (400).
    res = client.get("/api/expenses?status=BOGUS", headers=api_headers)
    assert res.status_code == 400


def test_get_single_expense_404(client, api_headers):
    res = client.get("/api/expenses/999", headers=api_headers)
    assert res.status_code == 404
    assert res.is_json


# --- OpenAPI / Swagger ------------------------------------------------------
def test_openapi_spec_served(client):
    res = client.get("/openapi.json")
    assert res.status_code == 200
    spec = res.get_json()
    assert spec["openapi"].startswith("3.")
    assert "/api/expenses" in spec["paths"]
    assert "/api/tokens" in spec["paths"]
    # Reusable components + Bearer security scheme are present.
    assert "Expense" in spec["components"]["schemas"]
    assert "token_auth" in spec["components"]["securitySchemes"]


def test_docs_page_served(client):
    res = client.get("/docs")
    assert res.status_code == 200


def test_openapi_includes_post_operations(client):
    spec = client.get("/openapi.json").get_json()
    paths = spec["paths"]
    assert "post" in paths["/api/expenses"]
    assert "post" in paths["/api/expenses/{expense_id}/approve"]
    assert "post" in paths["/api/payments"]
    assert "post" in paths["/api/payments/{payment_id}/pay"]
    assert "post" in paths["/api/bank-accounts"]
    # request body documented for the create endpoint
    assert "requestBody" in paths["/api/expenses"]["post"]


# --- Write endpoints (POST) -------------------------------------------------
def test_create_and_approve_expense_via_api(client, api_headers):
    r = client.post("/api/expenses", headers=api_headers, json={"description": "Laptop", "amount": 1500})
    assert r.status_code == 201
    exp = r.get_json()
    assert exp["status"] == "PENDING"
    assert exp["folio"].startswith("EXP-")

    r2 = client.post(f"/api/expenses/{exp['id']}/approve", headers=api_headers)
    assert r2.status_code == 200
    assert r2.get_json()["status"] == "APPROVED"


def test_create_expense_validation_error(client, api_headers):
    # Missing amount + empty description -> body validation error (400).
    r = client.post("/api/expenses", headers=api_headers, json={"description": ""})
    assert r.status_code == 400


def test_generate_payment_via_api(client, api_headers, bank_account):
    exp = client.post(
        "/api/expenses", headers=api_headers, json={"description": "X", "amount": 1000}
    ).get_json()
    client.post(f"/api/expenses/{exp['id']}/approve", headers=api_headers)
    r = client.post(
        "/api/payments",
        headers=api_headers,
        json={"expense_id": exp["id"], "bank_account_id": bank_account.id, "amount": 1000},
    )
    assert r.status_code == 201
    assert r.get_json()["status"] == "PENDING"


def test_generate_payment_on_unapproved_expense_conflicts(client, api_headers, bank_account):
    exp = client.post(
        "/api/expenses", headers=api_headers, json={"description": "X", "amount": 1000}
    ).get_json()  # still PENDING
    r = client.post(
        "/api/payments",
        headers=api_headers,
        json={"expense_id": exp["id"], "bank_account_id": bank_account.id, "amount": 1000},
    )
    assert r.status_code == 409


def test_create_bank_account_via_api(client, api_headers):
    r = client.post(
        "/api/bank-accounts",
        headers=api_headers,
        json={"account_name": "Nueva", "bank_name": "Banco", "account_number": "5551112223", "initial_balance": 5000},
    )
    assert r.status_code == 201
    assert r.get_json()["current_balance"] == 5000.0


def test_healthz(client):
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"
