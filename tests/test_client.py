import pytest
from datetime import date

from tests.conftest import auth_headers

# Базовые данные клиента
client_data = {
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1990-01-01",
    "email": "john.doe@example.com",
    "phone": "1234567890",
    "whatsapp_number": "1234567890",
    "balance": 0,
    "is_student": False,
    "students": None
}

# Данные для тестирования создания клиента-студента
client_student_data = {
    **client_data,
    "email": "john.student@example.com",
    "is_student": True
}

# Данные для тестирования создания клиента с дополнительными студентами
client_with_students_data = {
    **client_data,
    "email": "john.with.students@example.com",
    "students": [
        {
            "first_name": "Alice",
            "last_name": "Doe",
            "date_of_birth": "2015-01-01",
            "is_active": True
        },
        {
            "first_name": "Bob",
            "last_name": "Doe",
            "date_of_birth": "2017-01-01",
            "is_active": True
        }
    ]
}

# Данные для тестирования создания клиента-студента с дополнительными студентами
client_student_with_students_data = {
    **client_with_students_data,
    "email": "john.student.with.students@example.com",
    "is_student": True
}


def test_create_simple_client(client, auth_headers):
    """Тест создания простого клиента без студентов."""
    response = client.post("/clients/", json=client_data, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["first_name"] == client_data["first_name"]
    assert response.json()["email"] == client_data["email"]

    # Проверяем, что студенты не были созданы
    response = client.get(f"/clients/{response.json()['id']}/students", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_create_client_as_student(client, auth_headers):
    """Тест создания клиента, который также является студентом."""
    response = client.post("/clients/", json=client_student_data, headers=auth_headers)
    assert response.status_code == 201
    client_id = response.json()["id"]

    # Проверяем, что был создан один студент
    response = client.get(f"/clients/{client_id}/students", headers=auth_headers)
    assert response.status_code == 200
    students = response.json()
    assert len(students) == 1
    assert students[0]["first_name"] == client_student_data["first_name"]
    assert students[0]["last_name"] == client_student_data["last_name"]


def test_create_client_with_students(client, auth_headers):
    """Тест создания клиента с дополнительными студентами."""
    response = client.post("/clients/", json=client_with_students_data, headers=auth_headers)
    assert response.status_code == 201
    client_id = response.json()["id"]

    # Проверяем созданных студентов
    response = client.get(f"/clients/{client_id}/students", headers=auth_headers)
    assert response.status_code == 200
    students = response.json()
    assert len(students) == 2
    assert students[0]["first_name"] == client_with_students_data["students"][0]["first_name"]
    assert students[1]["first_name"] == client_with_students_data["students"][1]["first_name"]


def test_create_client_student_with_students(client, auth_headers):
    """Тест создания клиента-студента с дополнительными студентами."""
    response = client.post("/clients/", json=client_student_with_students_data, headers=auth_headers)
    assert response.status_code == 201
    client_id = response.json()["id"]

    # Проверяем созданных студентов (должно быть 3: сам клиент + 2 дополнительных)
    response = client.get(f"/clients/{client_id}/students", headers=auth_headers)
    assert response.status_code == 200
    students = response.json()
    assert len(students) == 3
    
    # Проверяем, что один из студентов имеет данные клиента
    client_student = next(
        (s for s in students if s["first_name"] == client_student_with_students_data["first_name"]),
        None
    )
    assert client_student is not None

    # Проверяем, что остальные студенты тоже созданы
    additional_students = [
        s for s in students if s["first_name"] in 
        [student["first_name"] for student in client_student_with_students_data["students"]]
    ]
    assert len(additional_students) == 2


def test_get_clients(client, create_test_client, auth_headers):
    """Тест получения списка клиентов."""
    response = client.get("/clients/", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_get_client_by_id(client, auth_headers, create_test_client):
    """Тест получения клиента по ID."""
    client_id = create_test_client.id
    response = client.get(f"/clients/{client_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == client_id


def test_update_client(client, auth_headers, create_test_client):
    """Тест обновления данных клиента."""
    client_id = create_test_client.id
    updated_data = {"first_name": "Jane"}
    response = client.patch(f"/clients/{client_id}", json=updated_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["first_name"] == "Jane"


def test_delete_client(client, auth_headers, create_test_client):
    """Тест удаления клиента."""
    client_id = create_test_client.id
    
    # Удаляем клиента
    response = client.delete(f"/clients/{client_id}", headers=auth_headers)
    assert response.status_code == 200
    
    # Проверяем, что клиент действительно удален
    response = client.get(f"/clients/{client_id}", headers=auth_headers)
    assert response.status_code == 404


def test_get_nonexistent_client(client, auth_headers):
    """Тест получения несуществующего клиента."""
    response = client.get("/clients/99999", headers=auth_headers)
    assert response.status_code == 404
    assert "Клиент не найден" in response.json()["detail"]


def test_create_client_without_auth(client):
    """Тест создания клиента без авторизации."""
    response = client.post("/clients/", json=client_data)
    assert response.status_code == 401


@pytest.mark.parametrize("invalid_data", [
    {**client_data, "email": "invalid-email"},  # Неверный формат email
    {**client_data, "phone": ""},  # Пустой телефон
    {**client_data, "date_of_birth": "invalid-date"},  # Неверный формат даты
])
def test_create_client_with_invalid_data(client, auth_headers, invalid_data):
    """Тест создания клиента с некорректными данными."""
    response = client.post("/clients/", json=invalid_data, headers=auth_headers)
    assert response.status_code == 422  # Ошибка валидации


def test_deactivate_client(client, auth_headers, create_test_client):
    """Тест деактивации клиента."""
    client_id = create_test_client.id
    
    # Создаем двух студентов для клиента
    student_data1 = {
        "first_name": "Test",
        "last_name": "Student1",
        "date_of_birth": "2015-01-01",
        "client_id": client_id
    }
    student_data2 = {
        "first_name": "Test",
        "last_name": "Student2",
        "date_of_birth": "2016-01-01",
        "client_id": client_id
    }
    client.post("/students/", json=student_data1, headers=auth_headers)
    client.post("/students/", json=student_data2, headers=auth_headers)
    
    # Деактивируем клиента
    response = client.patch(f"/clients/{client_id}/status", 
                          json={"is_active": False}, 
                          headers=auth_headers)
    
    assert response.status_code == 200
    assert response.json()["is_active"] == False
    assert response.json()["deactivation_date"] is not None
    assert response.json()["affected_students_count"] == 2

    # Проверяем, что все студенты стали неактивными
    students_response = client.get(f"/clients/{client_id}/students", headers=auth_headers)
    students = students_response.json()
    assert all(not student["is_active"] for student in students)
    assert all(student["deactivation_date"] is not None for student in students)


def test_reactivate_client(client, auth_headers, create_test_client):
    """Тест реактивации клиента."""
    client_id = create_test_client.id
    
    # Сначала деактивируем
    client.patch(f"/clients/{client_id}/status", 
                json={"is_active": False}, 
                headers=auth_headers)
    
    # Теперь реактивируем
    response = client.patch(f"/clients/{client_id}/status", 
                          json={"is_active": True}, 
                          headers=auth_headers)
    
    assert response.status_code == 200
    assert response.json()["is_active"] == True
    assert response.json()["deactivation_date"] is None
    assert response.json()["affected_students_count"] is None


def test_deactivate_nonexistent_client(client, auth_headers):
    """Тест деактивации несуществующего клиента."""
    response = client.patch("/clients/99999/status", 
                          json={"is_active": False}, 
                          headers=auth_headers)
    assert response.status_code == 404


def test_deactivate_client_without_auth(client, create_test_client):
    """Тест деактивации клиента без авторизации."""
    client_id = create_test_client.id
    response = client.patch(f"/clients/{client_id}/status", 
                          json={"is_active": False})
    assert response.status_code == 401
