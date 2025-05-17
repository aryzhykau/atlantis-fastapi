import pytest

subscription_only_training_type_correct = {
    "name": "Subscription only",
    "price": None,
    "is_subscription_only": True,
    "color": "#000000",
    "is_active": True
}

subscription_only_training_type_incorrect = {
    "name": "Subscription only",
    "price": 30,
    "is_subscription_only": True,
    "color": "#000000",
    "is_active": True
}

price_only_training_type_correct = {
    "name": "Price Only",
    "price": 30,
    "is_subscription_only": False,
    "color": "#000000",
    "is_active": True
}

price_only_training_type_incorrect = {
    "name": "Price only",
    "price": None,
    "is_subscription_only": False,
    "color": "#000000",
    "is_active": True
}

@pytest.mark.parametrize("invalid_name", [
    "",  # пустая строка
    "A",  # слишком короткое
    "A" * 51,  # слишком длинное
    "   ",  # только пробелы
])
def test_invalid_name(client, auth_headers, invalid_name):
    """Тест валидации названия типа тренировки"""
    data = {**price_only_training_type_correct, "name": invalid_name}
    response = client.post("/training_types/", json=data, headers=auth_headers)
    assert response.status_code == 422

@pytest.mark.parametrize("invalid_color", [
    "000000",  # без #
    "#00000",  # слишком короткий
    "#0000000",  # слишком длинный
    "#GGGGGG",  # неверные символы
    "#12345",  # неверная длина
    "invalid",  # неверный формат
])
def test_invalid_color(client, auth_headers, invalid_color):
    """Тест валидации цвета"""
    data = {**price_only_training_type_correct, "color": invalid_color}
    response = client.post("/training_types/", json=data, headers=auth_headers)
    assert response.status_code == 422

@pytest.mark.parametrize("invalid_price", [
    -1,  # отрицательная цена
    -0.01,  # отрицательная цена
    -1000,  # отрицательная цена
])
def test_invalid_price(client, auth_headers, invalid_price):
    """Тест валидации цены"""
    data = {**price_only_training_type_correct, "price": invalid_price}
    response = client.post("/training_types/", json=data, headers=auth_headers)
    assert response.status_code == 422

def test_create_training_type(client, auth_headers):
    response = client.post("/training_types/", json=subscription_only_training_type_correct, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == subscription_only_training_type_correct["name"]
    assert response.json()["is_active"] == subscription_only_training_type_correct["is_active"]

    response = client.post("/training_types/", json=price_only_training_type_correct, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == price_only_training_type_correct["name"]
    assert response.json()["is_active"] == price_only_training_type_correct["is_active"]

    response = client.post("/training_types/", json=subscription_only_training_type_incorrect, headers=auth_headers)
    assert response.status_code == 422

    response = client.post("/training_types/", json=price_only_training_type_incorrect, headers=auth_headers)
    assert response.status_code == 422

def test_get_training_types(client, auth_headers):
    client.post("/training_types/", json=subscription_only_training_type_correct, headers=auth_headers)
    client.post("/training_types/", json=price_only_training_type_correct, headers=auth_headers)
    response = client.get("/training_types/", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()["training_types"]) == 2

def test_get_training_type_by_id(client, auth_headers):
    client.post("/training_types/", json=subscription_only_training_type_correct, headers=auth_headers)
    client.post("/training_types/", json=price_only_training_type_correct, headers=auth_headers)
    response = client.get("/training_types/1", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == 1

def test_update_training_type(client, auth_headers):
    client.post("/training_types/", json=subscription_only_training_type_correct, headers=auth_headers)
    client.post("/training_types/", json=price_only_training_type_correct, headers=auth_headers)
    response = client.patch("/training_types/1", json={"name": "New name"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "New name"

def test_deactivate_training_type(client, auth_headers):
    # Создаем тип тренировки
    response = client.post("/training_types/", json=price_only_training_type_correct, headers=auth_headers)
    assert response.status_code == 200
    training_type_id = response.json()["id"]
    
    # Деактивируем тип тренировки
    update_data = {"is_active": False}
    response = client.patch(f"/training_types/{training_type_id}", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # Активируем тип тренировки обратно
    update_data = {"is_active": True}
    response = client.patch(f"/training_types/{training_type_id}", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is True


