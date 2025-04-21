import pytest

# Пример данных тренера
trainer_data = {
    "first_name": "Alice",
    "last_name": "Smith",
    "date_of_birth": "1985-08-15",
    "email": "alice.smith@example.com",
    "phone": "9876543210",
    "salary": 2000.0,
    "is_fixed_salary": True
}


def test_create_trainer(client, auth_headers):
    response = client.post("/trainers/", json=trainer_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["first_name"] == trainer_data["first_name"]


def test_get_trainers(client, auth_headers):
    # Создаем тренера
    client.post("/trainers/", json=trainer_data, headers=auth_headers)

    # Получаем список тренеров
    response = client.get("/trainers/", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()["trainers"]) > 0


def test_get_trainer_by_id(client, auth_headers):
    # Создаем тренера
    created_trainer = client.post("/trainers/", json=trainer_data, headers=auth_headers).json()
    trainer_id = created_trainer["id"]

    # Получаем тренера по ID
    response = client.get(f"/trainers/{trainer_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == trainer_id


def test_update_trainer(client, auth_headers):
    # Создаем тренера
    created_trainer = client.post("/trainers/", json=trainer_data, headers=auth_headers).json()
    trainer_id = created_trainer["id"]

    # Обновляем тренера
    updated_data = {"first_name": "Bob"}
    response = client.patch(f"/trainers/{trainer_id}", json=updated_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["first_name"] == "Bob"

