import pytest

subscription_only_training_type_correct = {
    "name": "Subscription only",
    "price": None,
    "is_subscription_only": True,
    "color": "#000000",
    "is_active": True,
    "max_participants": 10
}

subscription_only_training_type_incorrect = {
    "name": "Subscription only",
    "price": 30,
    "is_subscription_only": True,
    "color": "#000000",
    "is_active": True,
    "max_participants": 10
}

price_only_training_type_correct = {
    "name": "Price Only",
    "price": 30,
    "is_subscription_only": False,
    "color": "#000000",
    "is_active": True,
    "max_participants": 12
}

price_only_training_type_incorrect = {
    "name": "Price only",
    "price": None,
    "is_subscription_only": False,
    "color": "#000000",
    "is_active": True,
    "max_participants": 10 
}

# Фикстура для данных без явного указания max_participants (для проверки дефолтного значения)
training_type_default_max_participants = {
    "name": "Default Max Participants",
    "price": 25,
    "is_subscription_only": False,
    "color": "#112233",
    "is_active": True
    # max_participants не указан, ожидаем значение по умолчанию 4
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
    # Тест с явно указанным max_participants
    response = client.post("/training_types/", json=subscription_only_training_type_correct, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == subscription_only_training_type_correct["name"]
    assert data["is_active"] == subscription_only_training_type_correct["is_active"]
    assert data["max_participants"] == subscription_only_training_type_correct["max_participants"]

    response = client.post("/training_types/", json=price_only_training_type_correct, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == price_only_training_type_correct["name"]
    assert data["is_active"] == price_only_training_type_correct["is_active"]
    assert data["max_participants"] == price_only_training_type_correct["max_participants"]
    
    # Тест с использованием значения по умолчанию для max_participants
    response_default = client.post("/training_types/", json=training_type_default_max_participants, headers=auth_headers)
    assert response_default.status_code == 200
    data_default = response_default.json()
    assert data_default["name"] == training_type_default_max_participants["name"]
    assert data_default["max_participants"] == 4 # Проверяем значение по умолчанию

    response = client.post("/training_types/", json=subscription_only_training_type_incorrect, headers=auth_headers)
    assert response.status_code == 422

    response = client.post("/training_types/", json=price_only_training_type_incorrect, headers=auth_headers)
    assert response.status_code == 422

def test_get_training_types(client, auth_headers):
    # Создаем несколько типов тренировок для теста
    tt1_data = {**subscription_only_training_type_correct, "name": "Yoga Advanced"}
    tt2_data = {**price_only_training_type_correct, "name": "Crossfit Basic"}
    
    client.post("/training_types/", json=tt1_data, headers=auth_headers)
    client.post("/training_types/", json=tt2_data, headers=auth_headers)
    
    response = client.get("/training_types/", headers=auth_headers)
    assert response.status_code == 200
    training_types_list = response.json()["training_types"]
    assert len(training_types_list) >= 2 # Проверяем, что есть как минимум 2 созданных
    
    # Проверяем, что max_participants присутствует в ответе
    for tt in training_types_list:
        assert "max_participants" in tt
        if tt["name"] == tt1_data["name"]:
            assert tt["max_participants"] == tt1_data["max_participants"]
        elif tt["name"] == tt2_data["name"]:
            assert tt["max_participants"] == tt2_data["max_participants"]

def test_get_training_type_by_id(client, auth_headers):
    create_response = client.post("/training_types/", json=price_only_training_type_correct, headers=auth_headers)
    assert create_response.status_code == 200
    training_type_id = create_response.json()["id"]
    
    response = client.get(f"/training_types/{training_type_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == training_type_id
    assert data["name"] == price_only_training_type_correct["name"]
    assert data["max_participants"] == price_only_training_type_correct["max_participants"]

def test_update_training_type(client, auth_headers):
    create_response = client.post("/training_types/", json=subscription_only_training_type_correct, headers=auth_headers)
    assert create_response.status_code == 200
    training_type_id = create_response.json()["id"]
    
    update_data = {"name": "New Super Name", "max_participants": 5}
    response = client.patch(f"/training_types/{training_type_id}", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["max_participants"] == update_data["max_participants"]

    # Проверка, что другие поля не изменились, если не были переданы в update_data
    assert data["color"] == subscription_only_training_type_correct["color"]

@pytest.mark.parametrize("invalid_max_participants", [0, -1, -10])
def test_invalid_max_participants(client, auth_headers, invalid_max_participants):
    """Тест валидации max_participants (должно быть >= 1)"""
    data = {**price_only_training_type_correct, "max_participants": invalid_max_participants}
    response = client.post("/training_types/", json=data, headers=auth_headers)
    assert response.status_code == 422

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


