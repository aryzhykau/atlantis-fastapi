import pytest
from datetime import datetime, timezone, timedelta, date
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.services.subscription import SubscriptionService
from app.models import Invoice
from app.models.invoice import InvoiceStatus
from app.schemas.subscription import SubscriptionUpdate


class TestSubscriptionServiceIntegration:
    """Интеграционные тесты для сервиса подписок с реальной БД"""
    
    def test_add_subscription_to_student_integration(
        self,
        db_session: Session,
        test_student,
        test_subscription,
        test_admin
    ):
        """Интеграционный тест добавления подписки студенту"""
        service = SubscriptionService(db_session)
        
        # Добавляем подписку студенту
        student_subscription = service.add_subscription_to_student(
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            is_auto_renew=False,
            created_by_id=test_admin.id
        )
        
        # Проверяем, что подписка создана правильно
        assert student_subscription.student_id == test_student.id
        assert student_subscription.subscription_id == test_subscription.id
        assert student_subscription.sessions_left == test_subscription.number_of_sessions
        assert student_subscription.transferred_sessions == 0
        assert not student_subscription.is_auto_renew
        
        # Проверяем, что инвойс создан
        invoice = db_session.query(Invoice).filter(
            Invoice.student_id == test_student.id,
            Invoice.subscription_id == test_subscription.id
        ).first()
        assert invoice is not None
        assert invoice.amount == test_subscription.price
        assert invoice.status == InvoiceStatus.UNPAID  # Исправлено на Enum
    
    def test_freeze_subscription_integration(
        self,
        db_session: Session,
        test_student_subscription,
        test_admin
    ):
        """Интеграционный тест заморозки подписки"""
        service = SubscriptionService(db_session)
        
        # Замораживаем подписку (используем datetime без таймзоны для корректного сравнения)
        freeze_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        frozen_subscription = service.freeze_subscription(
            student_subscription_id=test_student_subscription.id,
            freeze_start_date=freeze_start,
            freeze_duration_days=7,
            updated_by_id=test_admin.id
        )
        
        # Проверяем, что подписка заморожена
        assert frozen_subscription.freeze_start_date is not None
        assert frozen_subscription.freeze_end_date is not None
        assert frozen_subscription.status == "frozen"
        
        # Проверяем в базе данных
        db_session.refresh(frozen_subscription)
        assert frozen_subscription.freeze_start_date == freeze_start
        assert frozen_subscription.freeze_end_date == freeze_start + timedelta(days=7)
    
    def test_unfreeze_subscription_integration(
        self,
        db_session: Session,
        test_frozen_subscription,
        test_admin
    ):
        """Интеграционный тест разморозки подписки"""
        service = SubscriptionService(db_session)
        
        # Размораживаем подписку
        unfrozen_subscription = service.unfreeze_subscription(
            student_subscription_id=test_frozen_subscription.id,
            updated_by_id=test_admin.id
        )
        
        # Проверяем, что подписка разморожена
        assert unfrozen_subscription.freeze_start_date is None
        assert unfrozen_subscription.freeze_end_date is None
        assert unfrozen_subscription.status == "active"
        
        # Проверяем в базе данных
        db_session.refresh(unfrozen_subscription)
        assert unfrozen_subscription.freeze_start_date is None
        assert unfrozen_subscription.freeze_end_date is None
    
    def test_auto_unfreeze_expired_subscriptions_integration(
        self,
        db_session: Session,
        test_expired_frozen_subscription
    ):
        """Интеграционный тест автоматической разморозки подписок"""
        service = SubscriptionService(db_session)
        
        # Проверяем, что подписка заморожена
        assert test_expired_frozen_subscription.freeze_start_date is not None
        assert test_expired_frozen_subscription.freeze_end_date is not None
        # Статус может быть "active" если заморозка уже истекла
        assert test_expired_frozen_subscription.status in ["frozen", "active"]
        
        # Запускаем автоматическую разморозку
        unfrozen_subscriptions = service.auto_unfreeze_expired_subscriptions()
        
        # Проверяем результат
        assert len(unfrozen_subscriptions) == 1
        assert unfrozen_subscriptions[0].id == test_expired_frozen_subscription.id
        
        # Проверяем в базе данных
        db_session.refresh(unfrozen_subscriptions[0])
        assert unfrozen_subscriptions[0].freeze_start_date is None
        assert unfrozen_subscriptions[0].freeze_end_date is None
        assert unfrozen_subscriptions[0].status == "active"
    
    def test_process_auto_renewals_integration(
        self,
        db_session: Session,
        test_auto_renewal_subscription,
        test_student,
        test_subscription,
        test_admin
    ):
        """Интеграционный тест автопродления подписок"""
        service = SubscriptionService(db_session)
        
        # Явно выставляем значения для чистоты теста
        test_auto_renewal_subscription.sessions_left = 5
        test_auto_renewal_subscription.transferred_sessions = 0
        db_session.commit()
        
        # Проверяем, что подписка готова к автопродлению
        assert test_auto_renewal_subscription.is_auto_renew is True
        # Статус может быть "expired" если подписка уже истекла
        assert test_auto_renewal_subscription.status in ["active", "expired"]
        
        # Запускаем автопродление
        renewed_subscriptions = service.process_auto_renewals()
        
        # Проверяем результат
        assert len(renewed_subscriptions) == 1
        new_subscription = renewed_subscriptions[0]
        
        # Проверяем новую подписку
        assert new_subscription.student_id == test_student.id
        assert new_subscription.subscription_id == test_subscription.id
        assert new_subscription.is_auto_renew is True
        # Проверяем, что занятия перенесены (максимум 3)
        expected_sessions = test_subscription.number_of_sessions + min(5, 3)
        assert new_subscription.sessions_left == expected_sessions
        assert new_subscription.transferred_sessions == min(5, 3)
        
        # Проверяем в базе данных
        db_session.refresh(new_subscription)
        assert new_subscription.status == "pending"  # Исправлено на pending
        
        # Проверяем, что старая подписка обновлена
        db_session.refresh(test_auto_renewal_subscription)
        assert test_auto_renewal_subscription.sessions_left == 0
        assert test_auto_renewal_subscription.transferred_sessions == 0
        
        # Проверяем, что создан инвойс для автопродления
        invoice = db_session.query(Invoice).filter(
            Invoice.student_subscription_id == new_subscription.id,
            Invoice.is_auto_renewal == True
        ).first()
        
        # Отладочная информация
        print(f"DEBUG: Ищем инвойс для student_subscription_id={new_subscription.id}")
        all_invoices = db_session.query(Invoice).all()
        print(f"DEBUG: Всего инвойсов в БД: {len(all_invoices)}")
        for inv in all_invoices:
            print(f"DEBUG: Инвойс {inv.id}: student_subscription_id={inv.student_subscription_id}, is_auto_renewal={inv.is_auto_renewal}")
        
        assert invoice is not None
        assert invoice.amount == test_subscription.price
    

    
    def test_add_subscription_to_inactive_student_integration(
        self,
        db_session: Session,
        test_student,
        test_subscription,
        test_admin
    ):
        """Интеграционный тест добавления подписки неактивному студенту"""
        service = SubscriptionService(db_session)
        
        # Деактивируем студента
        test_student.is_active = False
        db_session.commit()
        
        # Пытаемся добавить подписку неактивному студенту
        with pytest.raises(Exception) as exc_info:
            service.add_subscription_to_student(
                student_id=test_student.id,
                subscription_id=test_subscription.id,
                is_auto_renew=False,
                created_by_id=test_admin.id
            )
        
        # Проверяем, что выброшено исключение
        assert "Cannot add subscription to inactive student" in str(exc_info.value)
    
    def test_process_auto_renewals_with_inactive_student_integration(
        self,
        db_session: Session,
        test_auto_renewal_subscription,
        test_student
    ):
        """Интеграционный тест автопродления с неактивным студентом"""
        service = SubscriptionService(db_session)
        
        # Деактивируем студента
        test_student.is_active = False
        db_session.commit()
        
        # Запускаем автопродление
        renewed_subscriptions = service.process_auto_renewals()
        
        # Проверяем, что автопродления не было
        assert len(renewed_subscriptions) == 0 
    
    def test_auto_renewal_with_pending_status_integration(
        self,
        db_session: Session,
        test_auto_renewal_subscription,
        test_student,
        test_subscription,
        test_admin
    ):
        """Интеграционный тест проверки статуса pending для новой подписки"""
        service = SubscriptionService(db_session)
        
        # Запускаем автопродление
        renewed_subscriptions = service.process_auto_renewals()
        
        # Проверяем результат
        assert len(renewed_subscriptions) == 1
        new_subscription = renewed_subscriptions[0]
        
        # Проверяем, что новая подписка имеет статус pending
        assert new_subscription.status == "pending"
        
        # Проверяем, что start_date в будущем (завтра)
        tomorrow = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        # Приводим start_date к UTC для сравнения
        start_date_utc = new_subscription.start_date.replace(tzinfo=timezone.utc) if new_subscription.start_date.tzinfo is None else new_subscription.start_date
        assert start_date_utc >= tomorrow
    
    def test_double_auto_renewal_prevention_integration(
        self,
        db_session: Session,
        test_auto_renewal_subscription,
        test_student,
        test_subscription,
        test_admin
    ):
        """Интеграционный тест предотвращения двойного автопродления"""
        service = SubscriptionService(db_session)
        
        # Первый запуск автопродления
        renewed_subscriptions = service.process_auto_renewals()
        assert len(renewed_subscriptions) == 1
        
        # Второй запуск автопродления - не должно создаваться новых подписок
        renewed_subscriptions_second = service.process_auto_renewals()
        assert len(renewed_subscriptions_second) == 0
    
    def test_auto_renewal_frozen_subscription_integration(
        self,
        db_session: Session,
        test_frozen_subscription,
        test_student,
        test_subscription,
        test_admin
    ):
        """Интеграционный тест автопродления замороженной подписки"""
        service = SubscriptionService(db_session)
        
        # Включаем автопродление для замороженной подписки
        test_frozen_subscription.is_auto_renew = True
        test_frozen_subscription.end_date = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=999999)
        db_session.commit()
        
        # Запускаем автопродление
        renewed_subscriptions = service.process_auto_renewals()
        
        # Проверяем, что автопродление не произошло для замороженной подписки
        assert len(renewed_subscriptions) == 0
    
    def test_manual_subscription_no_transfer_integration(
        self,
        db_session: Session,
        test_student,
        test_subscription,
        test_admin,
        test_student_subscription
    ):
        """Интеграционный тест ручного добавления подписки без переноса занятий"""
        service = SubscriptionService(db_session)
        
        # Устанавливаем занятия в старой подписке
        test_student_subscription.sessions_left = 5
        db_session.commit()
        
        # Добавляем новую подписку вручную
        new_subscription = service.add_subscription_to_student(
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            is_auto_renew=False,
            created_by_id=test_admin.id
        )
        
        # Проверяем, что занятия НЕ перенесены
        assert new_subscription.sessions_left == test_subscription.number_of_sessions
        assert new_subscription.transferred_sessions == 0
        assert new_subscription.status == "active"  # Немедленно активна
        
        # Проверяем, что старая подписка не изменилась
        db_session.refresh(test_student_subscription)
        assert test_student_subscription.sessions_left == 5
    
    def test_disable_auto_renewal_integration(
        self,
        db_session: Session,
        test_auto_renewal_subscription,
        test_admin
    ):
        """Интеграционный тест отключения автопродления"""
        service = SubscriptionService(db_session)
        
        # Отключаем автопродление
        updated_subscription = service.update_auto_renewal(
            student_subscription_id=test_auto_renewal_subscription.id,
            is_auto_renew=False,
            updated_by_id=test_admin.id
        )
        
        # Проверяем, что автопродление отключено
        assert updated_subscription.is_auto_renew is False
        
        # Запускаем автопродление - не должно создаваться новых подписок
        renewed_subscriptions = service.process_auto_renewals()
        assert len(renewed_subscriptions) == 0
    
    def test_auto_renewal_invoice_creation_integration(
        self,
        db_session: Session,
        test_auto_renewal_subscription,
        test_student,
        test_subscription,
        test_admin
    ):
        """Интеграционный тест создания инвойса при автопродлении"""
        service = SubscriptionService(db_session)
        
        # Запускаем автопродление
        renewed_subscriptions = service.process_auto_renewals()
        
        # Проверяем, что создан инвойс для автопродления
        invoice = db_session.query(Invoice).filter(
            Invoice.student_subscription_id == renewed_subscriptions[0].id,
            Invoice.is_auto_renewal == True
        ).first()
        
        assert invoice is not None
        assert invoice.amount == test_subscription.price
        assert invoice.status == InvoiceStatus.UNPAID
        assert invoice.student_id == test_student.id
        assert invoice.subscription_id == test_subscription.id 
    
    def test_get_subscription_by_name_integration(
        self,
        db_session: Session,
        test_subscription
    ):
        """Интеграционный тест получения подписки по названию"""
        service = SubscriptionService(db_session)
        
        # Получаем подписку по названию
        subscription = service.get_subscription_by_name(test_subscription.name)
        assert subscription is not None
        assert subscription.name == test_subscription.name
        
        # Тест с несуществующим названием
        non_existent = service.get_subscription_by_name("Non Existent Subscription")
        assert non_existent is None
    
    def test_get_active_subscriptions_integration(
        self,
        db_session: Session,
        test_subscription
    ):
        """Интеграционный тест получения активных подписок"""
        service = SubscriptionService(db_session)
        
        # Получаем активные подписки
        active_subscriptions = service.get_active_subscriptions()
        assert len(active_subscriptions) >= 1
        assert all(sub.is_active for sub in active_subscriptions)
    
    def test_update_subscription_integration(
        self,
        db_session: Session,
        test_subscription
    ):
        """Интеграционный тест обновления подписки"""
        service = SubscriptionService(db_session)
        
        # Обновляем подписку
        updated_data = SubscriptionUpdate(
            name="Updated Test Subscription",
            price=200.0,
            number_of_sessions=15
        )
        
        updated_subscription = service.update_subscription(test_subscription.id, updated_data)
        assert updated_subscription is not None
        assert updated_subscription.name == "Updated Test Subscription"
        assert updated_subscription.price == 200.0
        assert updated_subscription.number_of_sessions == 15
    
    def test_update_subscription_not_found_integration(
        self,
        db_session: Session
    ):
        """Интеграционный тест обновления несуществующей подписки"""
        service = SubscriptionService(db_session)
        
        updated_data = SubscriptionUpdate(name="Test")
        result = service.update_subscription(99999, updated_data)
        assert result is None
    
    def test_get_student_subscriptions_with_filters_integration(
        self,
        db_session: Session,
        test_student,
        test_student_subscription
    ):
        """Интеграционный тест получения подписок студента с фильтрами"""
        from sqlalchemy import func
        import datetime
        service = SubscriptionService(db_session)

      

        # Получаем все подписки студента
        all_subscriptions = service.get_student_subscriptions(test_student.id, include_expired=True)
        
        

        # Получаем только активные подписки
        active_subscriptions = service.get_student_subscriptions(test_student.id, status="active")
       


        assert len(all_subscriptions) >= 1
        assert len(active_subscriptions) >= 1
        assert all(sub.status == "active" for sub in active_subscriptions)
    
    def test_get_student_subscriptions_by_status_integration(
        self,
        db_session: Session,
        test_student,
        test_student_subscription
    ):
        """Интеграционный тест получения подписок студента по статусу"""
        service = SubscriptionService(db_session)
        
        # Получаем подписки по статусу
        active_subscriptions = service.get_student_subscriptions_by_status(test_student.id, "active")
        assert len(active_subscriptions) >= 1
        assert all(sub.status == "active" for sub in active_subscriptions)
    
    def test_deduct_session_integration(
        self,
        db_session: Session,
        test_student_subscription
    ):
        """Интеграционный тест списания занятия"""
        from app.crud import subscription as subscription_crud
        
        # Устанавливаем количество занятий
        test_student_subscription.sessions_left = 5
        db_session.commit()
        
        # Списываем занятие
        updated_subscription = subscription_crud.deduct_session(db_session, test_student_subscription.id)
        assert updated_subscription is not None
        assert updated_subscription.sessions_left == 4
    
    def test_deduct_session_no_sessions_left_integration(
        self,
        db_session: Session,
        test_student_subscription
    ):
        """Интеграционный тест списания занятия когда нет занятий"""
        from app.crud import subscription as subscription_crud
        
        # Устанавливаем 0 занятий
        test_student_subscription.sessions_left = 0
        db_session.commit()
        
        # Пытаемся списать занятие
        result = subscription_crud.deduct_session(db_session, test_student_subscription.id)
        assert result is None
    
    def test_add_session_integration(
        self,
        db_session: Session,
        test_student_subscription
    ):
        """Интеграционный тест добавления занятия"""
        from app.crud import subscription as subscription_crud
        
        # Устанавливаем количество занятий
        test_student_subscription.sessions_left = 3
        db_session.commit()
        
        # Добавляем занятие
        updated_subscription = subscription_crud.add_session(db_session, test_student_subscription.id)
        assert updated_subscription is not None
        assert updated_subscription.sessions_left == 4
    
    def test_get_expiring_subscriptions_integration(
        self,
        db_session: Session,
        test_student_subscription
    ):
        """Интеграционный тест получения истекающих подписок"""
        from app.crud import subscription as subscription_crud
        
        # Устанавливаем дату окончания через 5 дней
        test_student_subscription.end_date = datetime.now(timezone.utc) + timedelta(days=5)
        db_session.commit()
        
        # Получаем истекающие подписки
        expiring_subscriptions = subscription_crud.get_expiring_subscriptions(db_session, days_before_expiry=7)
        assert len(expiring_subscriptions) >= 1
    
    def test_get_frozen_subscriptions_integration(
        self,
        db_session: Session,
        test_frozen_subscription
    ):
        """Интеграционный тест получения замороженных подписок"""
        from app.crud import subscription as subscription_crud
        
        # Устанавливаем истёкшую дату заморозки
        test_frozen_subscription.freeze_end_date = datetime.now(timezone.utc) - timedelta(days=1)
        db_session.commit()
        
        # Получаем замороженные подписки с истёкшим сроком
        frozen_subscriptions = subscription_crud.get_frozen_subscriptions(db_session)
        assert len(frozen_subscriptions) >= 1
    
    def test_update_subscription_auto_renewal_invoice_integration(
        self,
        db_session: Session,
        test_student_subscription
    ):
        """Интеграционный тест обновления инвойса автопродления"""
        from app.crud import subscription as subscription_crud
        
        # Обновляем инвойс автопродления
        updated_subscription = subscription_crud.update_subscription_auto_renewal_invoice(
            db_session, test_student_subscription.id, 123
        )
        assert updated_subscription is not None
        assert updated_subscription.auto_renewal_invoice_id == 123 
    
    def test_add_subscription_to_student_student_not_found_integration(
        self,
        db_session: Session,
        test_subscription,
        test_admin
    ):
        """Интеграционный тест добавления подписки несуществующему студенту"""
        service = SubscriptionService(db_session)
        
        with pytest.raises(HTTPException) as exc_info:
            service.add_subscription_to_student(
                student_id=99999,
                subscription_id=test_subscription.id,
                is_auto_renew=False,
                created_by_id=test_admin.id
            )
        
        assert exc_info.value.status_code == 404
        assert "Student not found" in str(exc_info.value.detail)
    
    def test_add_subscription_to_student_subscription_not_found_integration(
        self,
        db_session: Session,
        test_student,
        test_admin
    ):
        """Интеграционный тест добавления несуществующей подписки"""
        service = SubscriptionService(db_session)
        
        with pytest.raises(HTTPException) as exc_info:
            service.add_subscription_to_student(
                student_id=test_student.id,
                subscription_id=99999,
                is_auto_renew=False,
                created_by_id=test_admin.id
            )
        
        assert exc_info.value.status_code == 404
        assert "Subscription not found" in str(exc_info.value.detail)
    
    def test_update_auto_renewal_subscription_not_found_integration(
        self,
        db_session: Session,
        test_admin
    ):
        """Интеграционный тест обновления автопродления несуществующей подписки"""
        service = SubscriptionService(db_session)
        
        with pytest.raises(HTTPException) as exc_info:
            service.update_auto_renewal(
                student_subscription_id=99999,
                is_auto_renew=True,
                updated_by_id=test_admin.id
            )
        
        assert exc_info.value.status_code == 404
        assert "Subscription not found" in str(exc_info.value.detail)
    
    def test_freeze_subscription_not_found_integration(
        self,
        db_session: Session,
        test_admin
    ):
        """Интеграционный тест заморозки несуществующей подписки"""
        service = SubscriptionService(db_session)
        
        with pytest.raises(HTTPException) as exc_info:
            service.freeze_subscription(
                student_subscription_id=99999,
                freeze_start_date=datetime.now(timezone.utc),
                freeze_duration_days=7,
                updated_by_id=test_admin.id
            )
        
        assert exc_info.value.status_code == 404
        assert "Subscription not found" in str(exc_info.value.detail)
    
    def test_freeze_inactive_subscription_integration(
        self,
        db_session: Session,
        test_student_subscription,
        test_admin
    ):
        """Интеграционный тест заморозки неактивной подписки"""
        service = SubscriptionService(db_session)
        
        # Делаем подписку неактивной
        test_student_subscription.end_date = datetime.now(timezone.utc) - timedelta(days=1)
        db_session.commit()
        
        with pytest.raises(HTTPException) as exc_info:
            service.freeze_subscription(
                student_subscription_id=test_student_subscription.id,
                freeze_start_date=datetime.now(timezone.utc),
                freeze_duration_days=7,
                updated_by_id=test_admin.id
            )
        
        assert exc_info.value.status_code == 400
        assert "Can only freeze active subscriptions" in str(exc_info.value.detail)
    
    def test_unfreeze_subscription_not_found_integration(
        self,
        db_session: Session,
        test_admin
    ):
        """Интеграционный тест разморозки несуществующей подписки"""
        service = SubscriptionService(db_session)
        
        with pytest.raises(HTTPException) as exc_info:
            service.unfreeze_subscription(
                student_subscription_id=99999,
                updated_by_id=test_admin.id
            )
        
        assert exc_info.value.status_code == 404
        assert "Subscription not found" in str(exc_info.value.detail)
    
    def test_unfreeze_not_frozen_subscription_integration(
        self,
        db_session: Session,
        test_student_subscription,
        test_admin
    ):
        """Интеграционный тест разморозки незамороженной подписки"""
        service = SubscriptionService(db_session)
        
        # Убираем заморозку
        test_student_subscription.freeze_start_date = None
        test_student_subscription.freeze_end_date = None
        db_session.commit()
        
        with pytest.raises(HTTPException) as exc_info:
            service.unfreeze_subscription(
                student_subscription_id=test_student_subscription.id,
                updated_by_id=test_admin.id
            )
        
        assert exc_info.value.status_code == 400
        assert "Subscription is not frozen" in str(exc_info.value.detail) 