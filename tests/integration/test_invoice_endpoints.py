from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import InvoiceStatus, InvoiceType

def test_get_invoice(client: TestClient, auth_headers: dict, test_invoice):
    response = client.get(f"/invoices/{test_invoice.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == test_invoice.id

def test_get_student_invoices(client: TestClient, auth_headers: dict, test_student, test_invoice):
    response = client.get(f"/invoices/student/{test_student.id}", headers=auth_headers)
    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()

def test_get_client_invoices(client: TestClient, auth_headers: dict, test_client, test_invoice):
    response = client.get(f"/invoices/client/{test_client.id}", headers=auth_headers)
    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()

def test_create_subscription_invoice(client: TestClient, auth_headers: dict, test_client, test_subscription, test_student):
    invoice_data = {
        "client_id": test_client.id,
        "student_id": test_student.id,
        "subscription_id": test_subscription.id,
        "amount": 100.0,
        "description": "Test subscription invoice",
        "is_auto_renewal": False
    }
    response = client.post("/invoices/subscription", headers=auth_headers, json=invoice_data)
    assert response.status_code == 200
    assert response.json()["client_id"] == test_client.id
    assert response.json()["status"] == InvoiceStatus.UNPAID.value
    assert response.json()["type"] == InvoiceType.SUBSCRIPTION.value

def test_create_training_invoice(client: TestClient, auth_headers: dict, test_client, test_training, test_student):
    invoice_data = {
        "client_id": test_client.id,
        "student_id": test_student.id,
        "training_id": test_training.id,
        "amount": 50.0,
        "description": "Test training invoice"
    }
    response = client.post("/invoices/training", headers=auth_headers, json=invoice_data)
    assert response.status_code == 200
    assert response.json()["client_id"] == test_client.id
    assert response.json()["status"] == InvoiceStatus.UNPAID.value
    assert response.json()["type"] == InvoiceType.TRAINING.value

def test_cancel_invoice(client: TestClient, auth_headers: dict, test_invoice):
    response = client.post(f"/invoices/{test_invoice.id}/cancel", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == InvoiceStatus.CANCELLED.value

def test_get_invoice_not_found(client: TestClient, auth_headers: dict):
    response = client.get("/invoices/99999", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Invoice not found"

def test_get_student_invoices_no_invoices(client: TestClient, auth_headers: dict, test_student):
    response = client.get(f"/invoices/student/{test_student.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0

def test_get_client_invoices_no_invoices(client: TestClient, auth_headers: dict, test_client):
    response = client.get(f"/invoices/client/{test_client.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0

def test_create_subscription_invoice_invalid_client(client: TestClient, auth_headers: dict, test_subscription, test_student):
    invoice_data = {
        "client_id": 99999,
        "student_id": test_student.id,
        "subscription_id": test_subscription.id,
        "amount": 100.0,
        "description": "Test subscription invoice invalid client",
        "is_auto_renewal": False
    }
    response = client.post("/invoices/subscription", headers=auth_headers, json=invoice_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Client not found"

def test_create_subscription_invoice_invalid_subscription(client: TestClient, auth_headers: dict, test_client, test_student):
    invoice_data = {
        "client_id": test_client.id,
        "student_id": test_student.id,
        "subscription_id": 99999,
        "amount": 100.0,
        "description": "Test subscription invoice invalid subscription",
        "is_auto_renewal": False
    }
    response = client.post("/invoices/subscription", headers=auth_headers, json=invoice_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Subscription not found"

def test_create_training_invoice_invalid_client(client: TestClient, auth_headers: dict, test_training, test_student):
    invoice_data = {
        "client_id": 99999,
        "student_id": test_student.id,
        "training_id": test_training.id,
        "amount": 50.0,
        "description": "Test training invoice invalid client"
    }
    response = client.post("/invoices/training", headers=auth_headers, json=invoice_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Client not found"

def test_create_training_invoice_invalid_training(client: TestClient, auth_headers: dict, test_client, test_student):
    invoice_data = {
        "client_id": test_client.id,
        "student_id": test_student.id,
        "training_id": 99999,
        "amount": 50.0,
        "description": "Test training invoice invalid training"
    }
    response = client.post("/invoices/training", headers=auth_headers, json=invoice_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Training not found"

def test_cancel_invoice_not_found(client: TestClient, auth_headers: dict):
    response = client.post("/invoices/99999/cancel", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Invoice not found"
