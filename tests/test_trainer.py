import pytest
from datetime import date, timedelta

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


@pytest.mark.parametrize("invalid_phone", [
    "123",  # слишком короткий
    "12345678901234567890",  # слишком длинный
    "abc12345678",  # содержит буквы
    "123-456-7890",  # содержит недопустимые символы
    "",  # пустой
])
def test_invalid_phone(client, auth_headers, invalid_phone):
    """Тест валидации номера телефона"""
    invalid_data = {**trainer_data, "phone": invalid_phone}
    response = client.post("/trainers/", json=invalid_data, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.parametrize("invalid_name", [
    "",  # пустое имя
    "123",  # только цифры
    "John123",  # буквы и цифры
    "John@Doe",  # специальные символы
    "A" * 51,  # слишком длинное
])
def test_invalid_names(client, auth_headers, invalid_name):
    """Тест валидации имени и фамилии"""
    # Проверяем first_name
    invalid_data = {**trainer_data, "first_name": invalid_name}
    response = client.post("/trainers/", json=invalid_data, headers=auth_headers)
    assert response.status_code == 422

    # Проверяем last_name
    invalid_data = {**trainer_data, "last_name": invalid_name}
    response = client.post("/trainers/", json=invalid_data, headers=auth_headers)
    assert response.status_code == 422


def test_invalid_birth_dates(client, auth_headers):
    """Тест валидации даты рождения"""
    today = date.today()
    
    # Дата в будущем
    future_date = (today + timedelta(days=1)).isoformat()
    invalid_data = {**trainer_data, "date_of_birth": future_date}
    response = client.post("/trainers/", json=invalid_data, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.parametrize("invalid_salary", [
    -1000,  # отрицательная зарплата
    -0.01,  # отрицательная зарплата
])
def test_invalid_salary(client, auth_headers, invalid_salary):
    """Тест валидации зарплаты"""
    invalid_data = {**trainer_data, "salary": invalid_salary}
    response = client.post("/trainers/", json=invalid_data, headers=auth_headers)
    assert response.status_code == 422


def test_fixed_salary_validation(client, auth_headers):
    """Тест валидации фиксированной зарплаты"""
    # Проверяем, что нельзя установить фиксированную зарплату в 0
    invalid_data = {**trainer_data, "salary": 0, "is_fixed_salary": True}
    response = client.post("/trainers/", json=invalid_data, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.parametrize("invalid_email", [
    "not_an_email",  # неверный формат
    "@domain.com",  # отсутствует локальная часть
    "user@",  # отсутствует домен
    "user@domain",  # отсутствует TLD
    "",  # пустой email
])
def test_invalid_email(client, auth_headers, invalid_email):
    """Тест валидации email"""
    invalid_data = {**trainer_data, "email": invalid_email}
    response = client.post("/trainers/", json=invalid_data, headers=auth_headers)
    assert response.status_code == 422


def test_trainer_deactivation(client, auth_headers):
    """Тест деактивации тренера"""
    # Создаем тренера
    created_trainer = client.post("/trainers/", json=trainer_data, headers=auth_headers).json()
    trainer_id = created_trainer["id"]

    # Деактивируем тренера
    deactivate_data = {"is_active": False}
    response = client.patch(f"/trainers/{trainer_id}", json=deactivate_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert response.json()["deactivation_date"] is not None

    # Активируем тренера обратно
    activate_data = {"is_active": True}
    response = client.patch(f"/trainers/{trainer_id}", json=activate_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is True
    assert response.json()["deactivation_date"] is None

