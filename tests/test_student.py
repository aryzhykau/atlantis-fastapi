import pytest

student = {
  "first_name": "string",
  "last_name": "string",
  "date_of_birth": "2025-04-21",
  "client_id": 2,
}

def test_create_student(client, auth_headers, create_test_client): 
    response = client.post("/students/", json=student, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["first_name"] == "string"
    

def test_deactivate_student(client, auth_headers, create_test_client):
    """Тест деактивации отдельного студента."""
    # Создаем студента
    student_data = {
        "first_name": "Test",
        "last_name": "Student",
        "date_of_birth": "2015-01-01",
        "client_id": create_test_client.id
    }
    create_response = client.post("/students/", json=student_data, headers=auth_headers)
    student_id = create_response.json()["id"]
    
    # Деактивируем студента
    response = client.patch(f"/students/{student_id}/status", 
                          json={"is_active": False}, 
                          headers=auth_headers)
    
    assert response.status_code == 200
    assert response.json()["is_active"] == False
    assert response.json()["deactivation_date"] is not None
    assert response.json()["client_status"] == True  # Клиент остается активным


def test_reactivate_student_with_active_client(client, auth_headers, create_test_client):
    """Тест реактивации студента с активным клиентом."""
    # Создаем и деактивируем студента
    student_data = {
        "first_name": "Test",
        "last_name": "Student",
        "date_of_birth": "2015-01-01",
        "client_id": create_test_client.id
    }
    create_response = client.post("/students/", json=student_data, headers=auth_headers)
    student_id = create_response.json()["id"]
    
    client.patch(f"/students/{student_id}/status", 
                json={"is_active": False}, 
                headers=auth_headers)
    
    # Реактивируем студента
    response = client.patch(f"/students/{student_id}/status", 
                          json={"is_active": True}, 
                          headers=auth_headers)
    
    assert response.status_code == 200
    assert response.json()["is_active"] == True
    assert response.json()["deactivation_date"] is None
    assert response.json()["client_status"] == True


def test_reactivate_student_with_inactive_client(client, auth_headers, create_test_client):
    """Тест реактивации студента с неактивным клиентом."""
    # Создаем студента
    student_data = {
        "first_name": "Test",
        "last_name": "Student",
        "date_of_birth": "2015-01-01",
        "client_id": create_test_client.id
    }
    create_response = client.post("/students/", json=student_data, headers=auth_headers)
    student_id = create_response.json()["id"]
    
    # Сначала деактивируем студента
    client.patch(f"/students/{student_id}/status", 
                json={"is_active": False}, 
                headers=auth_headers)
    
    # Деактивируем клиента
    client.patch(f"/clients/{create_test_client.id}/status", 
                json={"is_active": False}, 
                headers=auth_headers)
    
    # Пытаемся реактивировать студента
    response = client.patch(f"/students/{student_id}/status", 
                          json={"is_active": True}, 
                          headers=auth_headers)
    
    assert response.status_code == 400  # Ожидаем ошибку
    assert "родительский клиент неактивен" in response.json()["detail"]


def test_deactivate_nonexistent_student(client, auth_headers):
    """Тест деактивации несуществующего студента."""
    response = client.patch("/students/99999/status", 
                          json={"is_active": False}, 
                          headers=auth_headers)
    assert response.status_code == 404


def test_deactivate_student_without_auth(client, create_test_client):
    """Тест деактивации студента без авторизации."""
    # Создаем студента
    student_data = {
        "first_name": "Test",
        "last_name": "Student",
        "date_of_birth": "2015-01-01",
        "client_id": create_test_client.id
    }
    create_response = client.post("/students/", 
                                json=student_data, 
                                headers={"Authorization": "Bearer dev_token"})
    student_id = create_response.json()["id"]
    
    response = client.patch(f"/students/{student_id}/status", 
                          json={"is_active": False})
    assert response.status_code == 401
    
