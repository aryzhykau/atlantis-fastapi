import pytest





def test_get_me(client, auth_headers):
    # Выполняем запрос на получение текущего пользователя
    response = client.get("/users/me", headers=auth_headers)
    assert response.status_code == 200

    # Проверяем, что возвращены корректные данные
    assert response.json()["email"] == "rorychan0697@gmail.com"
    assert response.json()["role"] == "ADMIN"



