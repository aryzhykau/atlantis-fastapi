import pytest
from fastapi.testclient import TestClient
from app.models.user import User

class TestFinancialEndpoints:
    """Тесты для эндпоинтов платежей"""
    
    def test_register_payment_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_client: User,
        test_admin: User
    ):
        """Тест регистрации платежа через API"""
        payment_data = {
            "client_id": test_client.id,
            "amount": 100.0,
            "description": "Test API payment"
        }
        
        response = client.post("/payments/", json=payment_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["client_id"] == test_client.id
        assert data["amount"] == 100.0
        assert data["description"] == "Test API payment"
        assert data["registered_by_id"] == test_admin.id
        assert data["cancelled_at"] is None
    
    def test_register_payment_unauthorized(
        self,
        client: TestClient,
        test_client: User
    ):
        """Тест регистрации платежа без авторизации"""
        payment_data = {
            "client_id": test_client.id,
            "amount": 100.0,
            "description": "Test API payment"
        }
        
        response = client.post("/payments/", json=payment_data)
        
        assert response.status_code == 401
    
    def test_register_payment_forbidden(
        self,
        client: TestClient,
        test_client: User,
        test_trainer: User
    ):
        """Тест регистрации платежа тренером (разрешено)"""
        # Создаём токен для тренера
        from app.auth.jwt_handler import create_access_token
        trainer_token = create_access_token({
            "sub": test_trainer.email,
            "id": test_trainer.id,
            "role": "TRAINER"
        })
        trainer_headers = {"Authorization": f"Bearer {trainer_token}"}
        
        payment_data = {
            "client_id": test_client.id,
            "amount": 100.0,
            "description": "Test API payment"
        }
        
        response = client.post("/payments/", json=payment_data, headers=trainer_headers)
        
        assert response.status_code == 200
    
    def test_register_payment_invalid_data(
        self,
        client: TestClient,
        auth_headers: dict,
        test_client: User
    ):
        """Тест регистрации платежа с неверными данными"""
        # Отрицательная сумма
        payment_data = {
            "client_id": test_client.id,
            "amount": -100.0,
            "description": "Invalid payment"
        }
        
        response = client.post("/payments/", json=payment_data, headers=auth_headers)
    
        assert response.status_code == 422
        
        # Нулевая сумма
        payment_data["amount"] = 0.0
        response = client.post("/payments/", json=payment_data, headers=auth_headers)
        
        assert response.status_code == 422
        
        # Слишком длинное описание
        payment_data["amount"] = 100.0
        payment_data["description"] = "A" * 501  # Больше 500 символов
        response = client.post("/payments/", json=payment_data, headers=auth_headers)
        
        assert response.status_code == 422
    
    def test_register_payment_client_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Тест регистрации платежа для несуществующего клиента"""
        payment_data = {
            "client_id": 99999,
            "amount": 100.0,
            "description": "Test API payment"
        }
        
        response = client.post("/payments/", json=payment_data, headers=auth_headers)
        
        assert response.status_code == 400
    
    def test_cancel_payment_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_client: User,
        test_admin: User
    ):
        """Тест отмены платежа через API"""
        # Сначала создаем платеж
        payment_data = {
            "client_id": test_client.id,
            "amount": 100.0,
            "description": "Payment to cancel"
        }
        
        create_response = client.post("/payments/", json=payment_data, headers=auth_headers)
        assert create_response.status_code == 200
        payment_id = create_response.json()["id"]
        
        # Отменяем платеж
        response = client.delete(f"/payments/{payment_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == payment_id
        assert data["cancelled_at"] is not None
        assert data["cancelled_by_id"] == test_admin.id
    
    def test_cancel_payment_unauthorized(
        self,
        client: TestClient,
        auth_headers: dict,
        test_client: User,
        test_admin: User
    ):
        """Тест отмены платежа без авторизации"""
        # Сначала создаем платеж
        payment_data = {
            "client_id": test_client.id,
            "amount": 100.0,
            "description": "Payment to cancel"
        }
        
        create_response = client.post("/payments/", json=payment_data, headers=auth_headers)
        assert create_response.status_code == 200
        payment_id = create_response.json()["id"]
        
        # Отменяем платеж без авторизации
        response = client.delete(f"/payments/{payment_id}", headers=None)
        
        assert response.status_code == 401
    
    def test_cancel_payment_forbidden(
        self,
        client: TestClient,
        test_client: User,
        test_trainer: User
    ):
        """Тест отмены платежа тренером (запрещено)"""
        # Создаём токен для тренера
        from app.auth.jwt_handler import create_access_token
        trainer_token = create_access_token({
            "sub": test_trainer.email,
            "id": test_trainer.id,
            "role": "TRAINER"
        })
        trainer_headers = {"Authorization": f"Bearer {trainer_token}"}
        
        # Сначала создаем платеж
        payment_data = {
            "client_id": test_client.id,
            "amount": 100.0,
            "description": "Payment to cancel"
        }
        
        create_response = client.post("/payments/", json=payment_data, headers=trainer_headers)
        assert create_response.status_code == 200
        payment_id = create_response.json()["id"]
        
        # Отменяем платеж тренером (должно быть запрещено)
        response = client.delete(f"/payments/{payment_id}", headers=trainer_headers)
        
        assert response.status_code == 403
    
    def test_cancel_payment_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Тест отмены несуществующего платежа"""
        response = client.delete("/payments/99999", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_get_payment_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_client: User
    ):
        """Тест получения платежа по ID"""
        # Сначала создаем платеж
        payment_data = {
            "client_id": test_client.id,
            "amount": 100.0,
            "description": "Test payment"
        }
        
        create_response = client.post("/payments/", json=payment_data, headers=auth_headers)
        assert create_response.status_code == 200
        payment_id = create_response.json()["id"]
        
        # Получаем платеж по ID
        response = client.get(f"/payments/{payment_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == payment_id
        assert data["client_id"] == test_client.id
        assert data["amount"] == 100.0
    
    def test_get_payment_not_found_endpoint(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Тест получения несуществующего платежа"""
        response = client.get("/payments/99999", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_get_payments_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_client: User
    ):
        """Тест получения списка платежей"""
        # Создаем несколько платежей
        payment_data = {
            "client_id": test_client.id,
            "amount": 100.0,
            "description": "Test payment 1"
        }

        client.post("/payments/", json=payment_data, headers=auth_headers)

        payment_data["amount"] = 200.0
        payment_data["description"] = "Test payment 2"
        client.post("/payments/", json=payment_data, headers=auth_headers)

        # Получаем список платежей
        response = client.get("/payments/filtered", headers=auth_headers)
        if response.status_code != 200:
            print("RESPONSE BODY:", response.text)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
    
    def test_get_payments_with_filters_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_client: User
    ):
        """Тест получения списка платежей с фильтрами"""
        # Создаем платеж
        payment_data = {
            "client_id": test_client.id,
            "amount": 100.0,
            "description": "Test payment"
        }
        
        client.post("/payments/", json=payment_data, headers=auth_headers)
        
        # Получаем платежи с фильтром
        response = client.get("/payments/filtered?registered_by_me=true&period=week", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
    
    def test_get_payment_history_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_client: User
    ):
        """Тест получения истории платежей"""
        # Создаем платеж
        payment_data = {
            "client_id": test_client.id,
            "amount": 100.0,
            "description": "Test payment"
        }
        
        client.post("/payments/", json=payment_data, headers=auth_headers)
        
        # Получаем историю платежей
        response = client.get("/payments/history", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    def test_get_payment_history_client_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Тест получения истории платежей для несуществующего клиента"""
        response = client.get("/payments/history?client_id=99999", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
    
    def test_get_client_balance_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_client: User
    ):
        """Тест получения баланса клиента"""
        # Создаем платеж для пополнения баланса
        payment_data = {
            "client_id": test_client.id,
            "amount": 150.0,
            "description": "Balance test"
        }
        
        client.post("/payments/", json=payment_data, headers=auth_headers)
        
        # Получаем баланс клиента
        response = client.get(f"/payments/client/{test_client.id}/balance", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["client_id"] == test_client.id
        assert data["balance"] >= 150.0
    
    def test_get_client_balance_client_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Тест получения баланса несуществующего клиента"""
        response = client.get("/payments/client/99999/balance", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_register_payment_with_invoice_processing_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_client: User,
        test_invoice
    ):
        """Тест регистрации платежа с автоматической обработкой инвойсов"""
        # Устанавливаем баланс клиента
        test_client.balance = 200.0
        
        # Создаем платеж
        payment_data = {
            "client_id": test_client.id,
            "amount": 150.0,
            "description": "Payment with invoice processing"
        }
        
        response = client.post("/payments/", json=payment_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["client_id"] == test_client.id
        assert data["amount"] == 150.0