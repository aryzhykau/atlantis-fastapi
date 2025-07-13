import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.subscription import StudentSubscription


class TestSubscriptionCRUD:
    """Unit-тесты для CRUD операций с подписками"""
    
    def test_get_today_auto_renewal_subscriptions(
        self,
        db_session: Session,
        test_auto_renewal_subscription
    ):
        """Тест получения подписок с автопродлением, которые заканчиваются сегодня"""
        from app.crud.subscription import get_today_auto_renewal_subscriptions
        
        # Получаем подписки с автопродлением, которые заканчиваются сегодня
        auto_renewal_subs = get_today_auto_renewal_subscriptions(db_session)
        
        assert len(auto_renewal_subs) == 1
        assert auto_renewal_subs[0].id == test_auto_renewal_subscription.id
        assert auto_renewal_subs[0].is_auto_renew is True
        # Проверяем, что подписка заканчивается сегодня
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        # Приводим end_date к UTC для сравнения
        end_date_utc = auto_renewal_subs[0].end_date.replace(tzinfo=timezone.utc) if auto_renewal_subs[0].end_date.tzinfo is None else auto_renewal_subs[0].end_date
        assert end_date_utc >= today_start
        assert end_date_utc < today_end
    
    def test_get_frozen_expired_subscriptions(
        self,
        db_session: Session,
        test_expired_frozen_subscription
    ):
        """Тест получения замороженных подписок с истекшим сроком заморозки"""
        from app.crud.subscription import get_frozen_subscriptions
        from datetime import datetime, timezone
        
        # Получаем замороженные подписки с истекшим сроком
        frozen_subs = get_frozen_subscriptions(db_session, datetime.now(timezone.utc))
        
        assert len(frozen_subs) == 1
        assert frozen_subs[0].id == test_expired_frozen_subscription.id
        # Сравниваем с учетом timezone
        current_time = datetime.now(timezone.utc)
        assert frozen_subs[0].freeze_end_date.replace(tzinfo=timezone.utc) <= current_time 
    
    def test_transfer_sessions_with_active_subscription(self, db_session, test_student, test_subscription):
        """Тест переноса занятий из активной подписки"""
        from app.crud.subscription import transfer_sessions
        
        # Создаём старую подписку с 5 занятиями
        old_subscription = StudentSubscription(
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=30),
            sessions_left=5,
            transferred_sessions=0,
            is_auto_renew=False
        )
        db_session.add(old_subscription)
        
        # Создаём новую подписку
        new_subscription = StudentSubscription(
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=30),
            sessions_left=8,
            transferred_sessions=0,
            is_auto_renew=False
        )
        db_session.add(new_subscription)
        db_session.commit()
        
        # Переносим занятия
        transferred = transfer_sessions(db_session, old_subscription, new_subscription, 3)
        
        # Проверяем результат
        assert transferred == 3  # Максимум 3 занятия
        db_session.refresh(old_subscription)
        db_session.refresh(new_subscription)
        assert old_subscription.sessions_left == 0
        assert old_subscription.transferred_sessions == 0
        assert new_subscription.sessions_left == 11  # 8 + 3
        assert new_subscription.transferred_sessions == 3
    
    def test_transfer_sessions_with_less_sessions(self, db_session, test_student, test_subscription):
        """Тест переноса занятий, когда занятий меньше максимума"""
        from app.crud.subscription import transfer_sessions
        
        # Создаём старую подписку с 2 занятиями
        old_subscription = StudentSubscription(
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=30),
            sessions_left=2,
            transferred_sessions=0,
            is_auto_renew=False
        )
        db_session.add(old_subscription)
        
        # Создаём новую подписку
        new_subscription = StudentSubscription(
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=30),
            sessions_left=8,
            transferred_sessions=0,
            is_auto_renew=False
        )
        db_session.add(new_subscription)
        db_session.commit()
        
        # Переносим занятия
        transferred = transfer_sessions(db_session, old_subscription, new_subscription, 3)
        
        # Проверяем результат
        assert transferred == 2  # Все 2 занятия
        db_session.refresh(old_subscription)
        db_session.refresh(new_subscription)
        assert old_subscription.sessions_left == 0
        assert old_subscription.transferred_sessions == 0
        assert new_subscription.sessions_left == 10  # 8 + 2
        assert new_subscription.transferred_sessions == 2
    
    def test_transfer_sessions_no_sessions_left(self, db_session, test_student, test_subscription):
        """Тест переноса занятий, когда нет оставшихся занятий"""
        from app.crud.subscription import transfer_sessions
        
        # Создаём старую подписку без занятий
        old_subscription = StudentSubscription(
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=30),
            sessions_left=0,
            transferred_sessions=0,
            is_auto_renew=False
        )
        db_session.add(old_subscription)
        
        # Создаём новую подписку
        new_subscription = StudentSubscription(
            student_id=test_student.id,
            subscription_id=test_subscription.id,
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=30),
            sessions_left=8,
            transferred_sessions=0,
            is_auto_renew=False
        )
        db_session.add(new_subscription)
        db_session.commit()
        
        # Переносим занятия
        transferred = transfer_sessions(db_session, old_subscription, new_subscription, 3)
        
        # Проверяем результат
        assert transferred == 0
        db_session.refresh(old_subscription)
        db_session.refresh(new_subscription)
        assert old_subscription.sessions_left == 0
        assert old_subscription.transferred_sessions == 0
        assert new_subscription.sessions_left == 8  # Без изменений
        assert new_subscription.transferred_sessions == 0 