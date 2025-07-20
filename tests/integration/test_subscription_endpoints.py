import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import InvoiceStatus


class TestSubscriptionEndpoints:
    """Тесты для эндпоинтов подписок"""
    
    def test_create_subscription_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_admin: dict
    ):
        """Тест создания подписки через API"""
        subscription_data = {
            "name": "Test API Subscription",
            "price": 150.0,
            "number_of_sessions": 12,
            "validity_days": 45,
            "is_active": True
        }
        
        response = client.post("/subscriptions/", json=subscription_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == subscription_data["name"]
        assert data["price"] == subscription_data["price"]
        assert data["number_of_sessions"] == subscription_data["number_of_sessions"]
        assert data["validity_days"] == subscription_data["validity_days"]
        assert data["is_active"] == subscription_data["is_active"]
    
    def test_create_subscription_unauthorized(
        self,
        client: TestClient
    ):
        """Тест создания подписки без авторизации"""
        subscription_data = {
            "name": "Test API Subscription",
            "price": 150.0,
            "number_of_sessions": 12,
            "validity_days": 45,
            "is_active": True
        }
        
        response = client.post("/subscriptions/", json=subscription_data)
        
        assert response.status_code == 401
    
    def test_create_subscription_forbidden(
        self,
        client: TestClient,
        test_trainer: dict
    ):
        """Тест создания подписки тренером (запрещено)"""
        # Создаём токен для тренера
        from app.auth.jwt_handler import create_access_token
        trainer_token = create_access_token({
            "sub": test_trainer.email,
            "id": test_trainer.id,
            "role": "TRAINER"
        })
        trainer_headers = {"Authorization": f"Bearer {trainer_token}"}
        
        subscription_data = {
            "name": "Test API Subscription",
            "price": 150.0,
            "number_of_sessions": 12,
            "validity_days": 45,
            "is_active": True
        }
        
        response = client.post("/subscriptions/", json=subscription_data, headers=trainer_headers)
        
        assert response.status_code == 403
    
    def test_get_subscriptions_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_subscription
    ):
        """Тест получения списка подписок"""
        response = client.get("/subscriptions/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 1
    
    def test_get_subscription_by_id_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_subscription
    ):
        """Тест получения подписки по ID"""
        response = client.get(f"/subscriptions/{test_subscription.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_subscription.id
        assert data["name"] == test_subscription.name
    
    def test_get_subscription_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Тест получения несуществующей подписки"""
        response = client.get("/subscriptions/99999", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_update_subscription_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_subscription
    ):
        """Тест обновления подписки"""
        update_data = {
            "name": "Updated Subscription Name",
            "price": 200.0
        }
        
        response = client.patch(f"/subscriptions/{test_subscription.id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["price"] == update_data["price"]
    
    def test_update_subscription_not_found_endpoint(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Тест обновления несуществующей подписки"""
        update_data = {
            "name": "Updated Subscription Name",
            "price": 200.0
        }
        
        response = client.patch("/subscriptions/99999", json=update_data, headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_update_subscription_forbidden_endpoint(
        self,
        client: TestClient,
        test_trainer: dict,
        test_subscription
    ):
        """Тест обновления подписки тренером (запрещено)"""
        # Создаём токен для тренера
        from app.auth.jwt_handler import create_access_token
        trainer_token = create_access_token({
            "sub": test_trainer.email,
            "id": test_trainer.id,
            "role": "TRAINER"
        })
        trainer_headers = {"Authorization": f"Bearer {trainer_token}"}
        
        update_data = {
            "name": "Updated Subscription Name",
            "price": 200.0
        }
        
        response = client.patch(f"/subscriptions/{test_subscription.id}", json=update_data, headers=trainer_headers)
        
        assert response.status_code == 403
    
    def test_add_subscription_to_student_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_student,
        test_subscription
    ):
        """Тест добавления подписки студенту"""
        subscription_data = {
            "student_id": test_student.id,
            "subscription_id": test_subscription.id,
            "is_auto_renew": False
        }
        
        response = client.post("/subscriptions/student", json=subscription_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["student_id"] == test_student.id
        assert data["subscription_id"] == test_subscription.id
        assert data["is_auto_renew"] == False
    
    def test_add_subscription_to_student_student_not_found_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_subscription
    ):
        """Тест добавления подписки несуществующему студенту"""
        subscription_data = {
            "student_id": 99999,
            "subscription_id": test_subscription.id,
            "is_auto_renew": False
        }
        
        response = client.post("/subscriptions/student", json=subscription_data, headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_add_subscription_to_student_subscription_not_found_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_student
    ):
        """Тест добавления несуществующей подписки"""
        subscription_data = {
            "student_id": test_student.id,
            "subscription_id": 99999,
            "is_auto_renew": False
        }
        
        response = client.post("/subscriptions/student", json=subscription_data, headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_add_subscription_to_inactive_student_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        db_session: Session,
        test_subscription
    ):
        """Тест добавления подписки неактивному студенту"""
        # Create an inactive student
        from app.models import Student, User
        from datetime import date
        
        inactive_client = User(
            first_name="Inactive",
            last_name="Client",
            date_of_birth=date(1990, 1, 1),
            email="inactive.client@example.com",
            phone="1234567890",
            role="CLIENT",
            is_active=False
        )
        db_session.add(inactive_client)
        db_session.commit()
        db_session.refresh(inactive_client)

        inactive_student = Student(
            client_id=inactive_client.id,
            first_name="Inactive",
            last_name="Student",
            date_of_birth=date(2000, 1, 1),
            is_active=False
        )
        db_session.add(inactive_student)
        db_session.commit()
        db_session.refresh(inactive_student)

        subscription_data = {
            "student_id": inactive_student.id,
            "subscription_id": test_subscription.id,
            "is_auto_renew": False
        }
        
        response = client.post("/subscriptions/student", json=subscription_data, headers=auth_headers)
        
        assert response.status_code == 400
        assert "Cannot add subscription to inactive student" in response.json()["detail"]
    
    def test_get_student_subscriptions_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_student,
        test_student_subscription
    ):
        """Тест получения подписок студента"""
        response = client.get(f"/subscriptions/student/{test_student.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
    
    def test_update_auto_renewal_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_student_subscription
    ):
        """Тест обновления автопродления"""
        update_data = {
            "is_auto_renew": True
        }
        
        response = client.patch(f"/subscriptions/student/{test_student_subscription.id}/auto-renewal", 
                              json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_auto_renew"] == True
    
    def test_update_auto_renewal_subscription_not_found_endpoint(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Тест обновления автопродления несуществующей подписки"""
        update_data = {
            "is_auto_renew": True
        }
        
        response = client.patch("/subscriptions/student/99999/auto-renewal", 
                              json=update_data, headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_freeze_subscription_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_student_subscription
    ):
        """Тест заморозки подписки"""
        freeze_data = {
            "freeze_start_date": datetime.now(timezone.utc).isoformat(),
            "freeze_duration_days": 7
        }
        
        response = client.post(f"/subscriptions/student/{test_student_subscription.id}/freeze", 
                             json=freeze_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["freeze_start_date"] is not None
        assert data["freeze_end_date"] is not None
        assert data["status"] == "frozen"
    
    def test_freeze_subscription_not_found_endpoint(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Тест заморозки несуществующей подписки"""
        freeze_data = {
            "freeze_start_date": datetime.now(timezone.utc).isoformat(),
            "freeze_duration_days": 7
        }
        
        response = client.post("/subscriptions/student/99999/freeze", 
                             json=freeze_data, headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_unfreeze_subscription_endpoint(
        self,
        client: TestClient,
        auth_headers: dict,
        test_frozen_subscription
    ):
        """Тест разморозки подписки"""
        response = client.post(f"/subscriptions/student/{test_frozen_subscription.id}/unfreeze", 
                             headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["freeze_start_date"] is None
        assert data["freeze_end_date"] is None
        assert data["status"] == "active" 
    
    def test_unfreeze_subscription_not_found_endpoint(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Тест разморозки несуществующей подписки"""
        response = client.post("/subscriptions/student/99999/unfreeze", 
                             headers=auth_headers)
        
        assert response.status_code == 404 