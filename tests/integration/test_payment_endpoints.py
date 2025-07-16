from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import UserRole
from datetime import datetime, timedelta

def test_create_payment(client: TestClient, auth_headers: dict, test_client, test_admin):
    payment_data = {
        "client_id": test_client.id,
        "amount": 50.0,
        "description": "Test payment from client",
        "registered_by_id": test_admin.id
    }
    response = client.post("/payments/", headers=auth_headers, json=payment_data)
    assert response.status_code == 200
    assert response.json()["client_id"] == test_client.id
    assert response.json()["amount"] == 50.0

def test_get_filtered_payments(client: TestClient, auth_headers: dict, test_payment, test_admin):
    response = client.get("/payments/filtered?period=week", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_payment_history(client: TestClient, auth_headers: dict, test_payment, test_client, test_admin):
    response = client.get(f"/payments/history?client_id={test_client.id}", headers=auth_headers)
    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()

def test_cancel_payment(client: TestClient, auth_headers: dict, test_payment):
    response = client.delete(f"/payments/{test_payment.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == test_payment.id
    assert response.json()["cancelled_at"] is not None

def test_get_payment(client: TestClient, auth_headers: dict, test_payment):
    response = client.get(f"/payments/{test_payment.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == test_payment.id

def test_get_payments(client: TestClient, auth_headers: dict, test_payment):
    response = client.get("/payments/", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1

def test_get_client_payments(client: TestClient, auth_headers: dict, test_client, test_payment):
    response = client.get(f"/payments/client/{test_client.id}", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1

def test_get_client_balance(client: TestClient, auth_headers: dict, test_client):
    response = client.get(f"/payments/client/{test_client.id}/balance", headers=auth_headers)
    assert response.status_code == 200
    assert "balance" in response.json()

def test_create_payment_unauthorized(client: TestClient, test_client, test_admin):
    payment_data = {
        "client_id": test_client.id,
        "amount": 50.0,
        "description": "Test payment from client",
        "registered_by_id": test_admin.id
    }
    response = client.post("/payments/", json=payment_data)
    assert response.status_code == 401

def test_create_payment_invalid_client_id(client: TestClient, auth_headers: dict, test_admin):
    payment_data = {
        "client_id": 99999, # Non-existent client ID
        "amount": 50.0,
        "description": "Test payment for invalid client",
        "registered_by_id": test_admin.id
    }
    response = client.post("/payments/", headers=auth_headers, json=payment_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Client not found"

def test_get_payments_no_payments(client: TestClient, auth_headers: dict):
    response = client.get("/payments/", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []

def test_get_payment_not_found(client: TestClient, auth_headers: dict):
    response = client.get("/payments/99999", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Payment not found"

def test_cancel_payment_not_found(client: TestClient, auth_headers: dict):
    response = client.delete("/payments/99999", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Payment not found"
