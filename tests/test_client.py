import pytest

from tests.conftest import auth_headers

# Пример данных клиента
client_data = {
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1990-01-01",
    "email": "john.doe@example.com",
    "phone": "123546723",
    "whatsapp_number": "156876538",
    "balance": 0
}


def test_create_client(client, auth_headers):

    response = client.post("/clients/", json=client_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["first_name"] == client_data["first_name"]



def test_get_clients(client, create_test_client, auth_headers,):

    # Получаем список клиентов
    response = client.get("/clients/", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_get_client_by_id(client, auth_headers, create_test_client):
    # Создаем клиента

    client_id = create_test_client.id

    # Получаем клиента по ID
    response = client.get(f"/clients/{client_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == client_id
#

def test_update_client(client, auth_headers, create_test_client):
    # Создаем клиента

    client_id = create_test_client.id

    # Обновляем клиента
    updated_data = {"first_name": "Jane"}
    response = client.patch(f"/clients/{client_id}", json=updated_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["first_name"] == "Jane"
