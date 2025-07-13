import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.services.subscription import SubscriptionService
from app.models import StudentSubscription


class TestSubscriptionServiceUnit:
    """Unit-тесты для сервиса подписок с моками"""
    
    @pytest.fixture
    def mock_db(self):
        """Мок для базы данных"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_subscription(self):
        """Мок для замороженной подписки"""
        subscription = Mock(spec=StudentSubscription)
        subscription.id = 1
        subscription.student_id = 1
        subscription.subscription_id = 1
        subscription.start_date = datetime.now(timezone.utc) - timedelta(days=30)
        subscription.end_date = datetime.now(timezone.utc) + timedelta(days=10)
        subscription.is_auto_renew = False
        subscription.freeze_start_date = datetime.now(timezone.utc) - timedelta(days=10)
        subscription.freeze_end_date = datetime.now(timezone.utc) - timedelta(days=1)  # Истекший срок
        subscription.sessions_left = 5
        subscription.transferred_sessions = 0
        subscription.auto_renewal_invoice_id = None
        return subscription
    
    @pytest.fixture
    def mock_unfrozen_subscription(self):
        """Мок для размороженной подписки"""
        subscription = Mock(spec=StudentSubscription)
        subscription.id = 1
        subscription.student_id = 1
        subscription.subscription_id = 1
        subscription.start_date = datetime.now(timezone.utc) - timedelta(days=30)
        subscription.end_date = datetime.now(timezone.utc) + timedelta(days=10)
        subscription.is_auto_renew = False
        subscription.freeze_start_date = None
        subscription.freeze_end_date = None
        subscription.sessions_left = 5
        subscription.transferred_sessions = 0
        subscription.auto_renewal_invoice_id = None
        return subscription
    
    @patch('app.services.subscription.get_frozen_subscriptions')
    @patch('app.services.subscription.unfreeze_subscription')
    def test_auto_unfreeze_expired_subscriptions_success(
        self,
        mock_unfreeze_subscription,
        mock_get_frozen_subscriptions,
        mock_db,
        mock_subscription,
        mock_unfrozen_subscription
    ):
        """Тест успешной автоматической разморозки подписок"""
        # Настройка моков
        mock_get_frozen_subscriptions.return_value = [mock_subscription]
        mock_unfreeze_subscription.return_value = mock_unfrozen_subscription
        
        # Создаем сервис
        service = SubscriptionService(mock_db)
        
        # Вызываем метод
        result = service.auto_unfreeze_expired_subscriptions()
        
        # Проверяем, что методы были вызваны
        mock_get_frozen_subscriptions.assert_called_once_with(mock_db)
        mock_unfreeze_subscription.assert_called_once_with(mock_db, mock_subscription.id)
        mock_db.commit.assert_called_once()
        
        # Проверяем результат
        assert len(result) == 1
        assert result[0] == mock_unfrozen_subscription
    
    @patch('app.services.subscription.get_frozen_subscriptions')
    @patch('app.services.subscription.unfreeze_subscription')
    def test_auto_unfreeze_expired_subscriptions_no_frozen(
        self,
        mock_unfreeze_subscription,
        mock_get_frozen_subscriptions,
        mock_db
    ):
        """Тест автоматической разморозки когда нет замороженных подписок"""
        # Настройка моков
        mock_get_frozen_subscriptions.return_value = []
        
        # Создаем сервис
        service = SubscriptionService(mock_db)
        
        # Вызываем метод
        result = service.auto_unfreeze_expired_subscriptions()
        
        # Проверяем, что методы были вызваны
        mock_get_frozen_subscriptions.assert_called_once_with(mock_db)
        mock_unfreeze_subscription.assert_not_called()
        mock_db.commit.assert_not_called()
        
        # Проверяем результат
        assert len(result) == 0
    
    @patch('app.services.subscription.get_frozen_subscriptions')
    @patch('app.services.subscription.unfreeze_subscription')
    def test_auto_unfreeze_expired_subscriptions_with_error(
        self,
        mock_unfreeze_subscription,
        mock_get_frozen_subscriptions,
        mock_db,
        mock_subscription
    ):
        """Тест автоматической разморозки с ошибкой при разморозке"""
        # Настройка моков
        mock_get_frozen_subscriptions.return_value = [mock_subscription]
        mock_unfreeze_subscription.side_effect = Exception("Database error")
        
        # Создаем сервис
        service = SubscriptionService(mock_db)
        
        # Вызываем метод
        result = service.auto_unfreeze_expired_subscriptions()
        
        # Проверяем, что методы были вызваны
        mock_get_frozen_subscriptions.assert_called_once_with(mock_db)
        mock_unfreeze_subscription.assert_called_once_with(mock_db, mock_subscription.id)
        mock_db.rollback.assert_called_once()
        
        # Проверяем результат - должен быть пустой список при ошибке
        assert len(result) == 0
    
    @patch('app.services.subscription.get_frozen_subscriptions')
    @patch('app.services.subscription.unfreeze_subscription')
    def test_auto_unfreeze_expired_subscriptions_multiple_subscriptions(
        self,
        mock_unfreeze_subscription,
        mock_get_frozen_subscriptions,
        mock_db,
        mock_subscription,
        mock_unfrozen_subscription
    ):
        """Тест автоматической разморозки нескольких подписок"""
        # Создаем вторую подписку
        mock_subscription2 = Mock(spec=StudentSubscription)
        mock_subscription2.id = 2
        mock_subscription2.student_id = 2
        mock_subscription2.freeze_start_date = datetime.now(timezone.utc) - timedelta(days=5)
        mock_subscription2.freeze_end_date = datetime.now(timezone.utc) - timedelta(days=1)
        
        mock_unfrozen_subscription2 = Mock(spec=StudentSubscription)
        mock_unfrozen_subscription2.id = 2
        mock_unfrozen_subscription2.student_id = 2
        mock_unfrozen_subscription2.freeze_start_date = None
        mock_unfrozen_subscription2.freeze_end_date = None
        
        # Настройка моков
        mock_get_frozen_subscriptions.return_value = [mock_subscription, mock_subscription2]
        mock_unfreeze_subscription.side_effect = [mock_unfrozen_subscription, mock_unfrozen_subscription2]
        
        # Создаем сервис
        service = SubscriptionService(mock_db)
        
        # Вызываем метод
        result = service.auto_unfreeze_expired_subscriptions()
        
        # Проверяем, что методы были вызваны для обеих подписок
        assert mock_get_frozen_subscriptions.call_count == 1
        assert mock_unfreeze_subscription.call_count == 2
        assert mock_db.commit.call_count == 2
        
        # Проверяем результат
        assert len(result) == 2
        assert result[0] == mock_unfrozen_subscription
        assert result[1] == mock_unfrozen_subscription2
    
    @patch('app.services.subscription.get_today_auto_renewal_subscriptions')
    @patch('app.services.subscription.student_crud.get_student_by_id')
    @patch('app.services.subscription.SubscriptionService.get_subscription')
    def test_process_auto_renewals_with_inactive_student(
        self,
        mock_get_subscription,
        mock_get_student_by_id,
        mock_get_today_auto_renewal_subscriptions,
        mock_db
    ):
        """Тест автопродления с неактивным студентом"""
        # Создаем мок подписки
        mock_subscription = Mock(spec=StudentSubscription)
        mock_subscription.id = 1
        mock_subscription.student_id = 1
        mock_subscription.subscription_id = 1
        mock_subscription.end_date = datetime.now(timezone.utc)
        mock_subscription.sessions_left = 5
        
        # Создаем мок неактивного студента
        mock_inactive_student = Mock()
        mock_inactive_student.id = 1
        mock_inactive_student.is_active = False
        mock_inactive_student.client_id = 1
        
        # Создаем мок шаблона подписки
        mock_subscription_template = Mock()
        mock_subscription_template.id = 1
        mock_subscription_template.is_active = True
        mock_subscription_template.validity_days = 30
        mock_subscription_template.number_of_sessions = 8
        mock_subscription_template.price = 100.0
        mock_subscription_template.name = "Test Subscription"
        
        # Настройка моков
        mock_get_today_auto_renewal_subscriptions.return_value = [mock_subscription]
        mock_get_student_by_id.return_value = mock_inactive_student
        mock_get_subscription.return_value = mock_subscription_template
        
        # Создаем сервис
        service = SubscriptionService(mock_db)
        
        # Вызываем метод
        result = service.process_auto_renewals()
        
        # Проверяем, что методы были вызваны
        mock_get_today_auto_renewal_subscriptions.assert_called_once_with(mock_db)
        mock_get_student_by_id.assert_called_once_with(mock_db, 1)
        
        # Проверяем результат - не должно быть продлений для неактивного студента
        assert len(result) == 0
    
    @patch('app.services.subscription.get_today_auto_renewal_subscriptions')
    @patch('app.services.subscription.student_crud.get_student_by_id')
    @patch('app.services.subscription.SubscriptionService.get_subscription')
    def test_process_auto_renewals_with_inactive_subscription_template(
        self,
        mock_get_subscription,
        mock_get_student_by_id,
        mock_get_today_auto_renewal_subscriptions,
        mock_db
    ):
        """Тест автопродления с неактивным шаблоном подписки"""
        # Создаем мок подписки
        mock_subscription = Mock(spec=StudentSubscription)
        mock_subscription.id = 1
        mock_subscription.student_id = 1
        mock_subscription.subscription_id = 1
        mock_subscription.end_date = datetime.now(timezone.utc)
        mock_subscription.sessions_left = 5
        
        # Создаем мок активного студента
        mock_active_student = Mock()
        mock_active_student.id = 1
        mock_active_student.is_active = True
        mock_active_student.client_id = 1
        
        # Создаем мок неактивного шаблона подписки
        mock_inactive_subscription_template = Mock()
        mock_inactive_subscription_template.id = 1
        mock_inactive_subscription_template.is_active = False  # Неактивный шаблон
        
        # Настройка моков
        mock_get_today_auto_renewal_subscriptions.return_value = [mock_subscription]
        mock_get_student_by_id.return_value = mock_active_student
        mock_get_subscription.return_value = mock_inactive_subscription_template
        
        # Создаем сервис
        service = SubscriptionService(mock_db)
        
        # Вызываем метод
        result = service.process_auto_renewals()
        
        # Проверяем, что методы были вызваны
        mock_get_today_auto_renewal_subscriptions.assert_called_once_with(mock_db)
        mock_get_student_by_id.assert_called_once_with(mock_db, 1)
        mock_get_subscription.assert_called_once_with(1)
        
        # Проверяем результат - не должно быть продлений для неактивного шаблона
        assert len(result) == 0
    
    @patch('app.services.subscription.get_today_auto_renewal_subscriptions')
    @patch('app.services.subscription.student_crud.get_student_by_id')
    @patch('app.services.subscription.SubscriptionService.get_subscription')
    @patch('app.services.subscription.create_student_subscription')
    @patch('app.services.subscription.transfer_sessions')
    @patch('app.services.subscription.create_and_pay_invoice')
    @patch('app.services.subscription.update_subscription_auto_renewal_invoice')
    def test_process_auto_renewals_success(
        self,
        mock_update_subscription_auto_renewal_invoice,
        mock_create_and_pay_invoice,
        mock_transfer_sessions,
        mock_create_student_subscription,
        mock_get_subscription,
        mock_get_student_by_id,
        mock_get_today_auto_renewal_subscriptions,
        mock_db
    ):
        """Тест успешного автопродления подписки"""
        # Создаем мок подписки для автопродления
        mock_subscription = Mock(spec=StudentSubscription)
        mock_subscription.id = 1
        mock_subscription.student_id = 1
        mock_subscription.subscription_id = 1
        mock_subscription.start_date = datetime.now(timezone.utc) - timedelta(days=25)
        mock_subscription.end_date = datetime.now(timezone.utc)
        mock_subscription.is_auto_renew = True
        mock_subscription.freeze_start_date = None
        mock_subscription.freeze_end_date = None
        mock_subscription.sessions_left = 5
        mock_subscription.transferred_sessions = 0
        mock_subscription.auto_renewal_invoice_id = None
        
        # Создаем мок активного студента
        mock_active_student = Mock()
        mock_active_student.id = 1
        mock_active_student.is_active = True
        mock_active_student.client_id = 1
        
        # Создаем мок активного шаблона подписки
        mock_subscription_template = Mock()
        mock_subscription_template.id = 1
        mock_subscription_template.is_active = True
        mock_subscription_template.validity_days = 30
        mock_subscription_template.number_of_sessions = 8
        mock_subscription_template.price = 100.0
        mock_subscription_template.name = "Test Subscription"
        
        # Создаем мок новой подписки
        mock_new_subscription = Mock(spec=StudentSubscription)
        mock_new_subscription.id = 2
        mock_new_subscription.student_id = 1
        mock_new_subscription.subscription_id = 1
        mock_new_subscription.start_date = datetime.now(timezone.utc)
        mock_new_subscription.end_date = datetime.now(timezone.utc) + timedelta(days=30)
        mock_new_subscription.is_auto_renew = True
        mock_new_subscription.freeze_start_date = None
        mock_new_subscription.freeze_end_date = None
        mock_new_subscription.sessions_left = 11  # 8 + 3 transferred
        mock_new_subscription.transferred_sessions = 3
        mock_new_subscription.auto_renewal_invoice_id = None
        
        # Создаем мок инвойса
        mock_invoice = Mock()
        mock_invoice.id = 1
        mock_invoice.amount = 100.0
        mock_invoice.status = "paid"
        
        # Настройка моков
        mock_get_today_auto_renewal_subscriptions.return_value = [mock_subscription]
        mock_get_student_by_id.return_value = mock_active_student
        mock_get_subscription.return_value = mock_subscription_template
        mock_create_student_subscription.return_value = mock_new_subscription
        mock_transfer_sessions.return_value = 3  # Количество перенесённых занятий
        mock_create_and_pay_invoice.return_value = mock_invoice
        mock_update_subscription_auto_renewal_invoice.return_value = mock_subscription
        
        # Создаем сервис
        service = SubscriptionService(mock_db)
        
        # Вызываем метод
        result = service.process_auto_renewals()
        
        # Проверяем, что методы были вызваны с правильными параметрами
        mock_get_today_auto_renewal_subscriptions.assert_called_once_with(mock_db)
        mock_get_student_by_id.assert_called_once_with(mock_db, 1)
        mock_get_subscription.assert_called_once_with(1)
        
        # Проверяем создание новой подписки
        mock_create_student_subscription.assert_called_once()
        call_args = mock_create_student_subscription.call_args[0][1]  # StudentSubscriptionCreate
        assert call_args.student_id == 1
        assert call_args.subscription_id == 1
        assert call_args.is_auto_renew is True
        assert call_args.sessions_left == 8  # Базовое количество сессий из шаблона
        assert call_args.transferred_sessions == 0  # Перенос происходит после создания
        
        # Проверяем перенос занятий
        mock_transfer_sessions.assert_called_once()
        transfer_call_args = mock_transfer_sessions.call_args[0]
        assert transfer_call_args[0] == mock_db  # db
        assert transfer_call_args[1] == mock_subscription  # old_subscription
        assert transfer_call_args[2] == mock_new_subscription  # new_subscription
        assert transfer_call_args[3] == 3  # max_sessions
        
        # Проверяем создание инвойса
        mock_create_and_pay_invoice.assert_called_once()
        invoice_call_args = mock_create_and_pay_invoice.call_args[0][1]  # InvoiceCreate
        assert invoice_call_args.client_id == 1
        assert invoice_call_args.student_id == 1
        assert invoice_call_args.subscription_id == 1
        assert invoice_call_args.amount == 100.0
        assert invoice_call_args.is_auto_renewal is True
        
        # Проверяем связывание с инвойсом
        mock_update_subscription_auto_renewal_invoice.assert_called_once_with(
            mock_db,
            1,  # subscription.id
            1   # mock_invoice.id
        )
        
        # Проверяем коммит
        mock_db.commit.assert_called_once()
        
        # Проверяем результат
        assert len(result) == 1
        assert result[0] == mock_new_subscription 