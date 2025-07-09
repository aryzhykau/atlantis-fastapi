import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models import (
    Student,
    Subscription,
    StudentSubscription,
    Invoice,
    InvoiceType,
    InvoiceStatus,
    User,
    UserRole
)

logger = logging.getLogger(__name__)


class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db

    def validate_admin(self, user_id: int) -> None:
        """Проверка, что пользователь является админом или тренером"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or user.role is not UserRole.ADMIN:
            raise HTTPException(
                status_code=403,
                detail="Only admins can manage subscriptions"
            )

    def get_subscription(self, subscription_id: int) -> Optional[Subscription]:
        """Получение абонемента по ID"""
        return self.db.query(Subscription).filter(Subscription.id == subscription_id).first()

    def get_student_subscription(self, student_subscription_id: int) -> Optional[StudentSubscription]:
        """Получение подписки студента по ID"""
        return self.db.query(StudentSubscription).filter(StudentSubscription.id == student_subscription_id).first()

    def get_active_student_subscriptions(self, student_id: int) -> List[StudentSubscription]:
        """Получение активных подписок студента"""
        today = datetime.utcnow()
        return (
            self.db.query(StudentSubscription)
            .filter(
                and_(
                    StudentSubscription.student_id == student_id,
                    StudentSubscription.start_date <= today,
                    StudentSubscription.end_date >= today,
                    ~StudentSubscription.status.in_(["expired", "frozen"])
                )
            )
            .all()
        )

    def add_subscription_to_student(
        self,
        student_id: int,
        subscription_id: int,
        is_auto_renew: bool,
        created_by_id: int
    ) -> StudentSubscription:
        """Добавление абонемента студенту"""
        # Проверяем права
        self.validate_admin(created_by_id)

        # Получаем студента и абонемент
        student = self.db.query(Student).filter(Student.id == student_id).first()
        subscription = self.get_subscription(subscription_id)

        if not student or not subscription:
            raise HTTPException(status_code=404, detail="Student or subscription not found")

        # Ищем предыдущий абонемент студента
        previous_subscription = (
            self.db.query(StudentSubscription)
            .filter(
                StudentSubscription.student_id == student_id,
                StudentSubscription.end_date <= datetime.utcnow()
            )
            .order_by(StudentSubscription.end_date.desc())
            .first()
        )

        # Определяем количество переносимых тренировок
        transferred_sessions = 0
        if previous_subscription and previous_subscription.sessions_left > 0:
            # Переносим не более 3 тренировок
            transferred_sessions = min(previous_subscription.sessions_left, 3)
            # Обнуляем оставшиеся тренировки в старом абонементе
            previous_subscription.sessions_left = 0
            previous_subscription.transferred_sessions = 0

        # Создаем подписку студента
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=subscription.validity_days)

        student_subscription = StudentSubscription(
            student_id=student_id,
            subscription_id=subscription_id,
            start_date=start_date,
            end_date=end_date,
            is_auto_renew=is_auto_renew,
            sessions_left=subscription.number_of_sessions + transferred_sessions,
            transferred_sessions=transferred_sessions
        )
        self.db.add(student_subscription)
        client = self.db.query(User).filter(User.id == student.client_id).first()
        invoice_status = InvoiceStatus.UNPAID
        current_balance = client.balance or 0.0
        if current_balance >= subscription.price:
            client.balance = current_balance - subscription.price
            self.db.flush()
            self.db.refresh(client)
            invoice_status = InvoiceStatus.PAID


        # Создаем инвойс для оплаты абонемента
        invoice = Invoice(
            client_id=student.client_id,
            student_id=student_id,
            subscription_id=subscription_id,
            type=InvoiceType.SUBSCRIPTION,
            amount=subscription.price,
            description=f"Subscription: {subscription.name}",
            status=invoice_status,
            is_auto_renewal=False
        )
        self.db.add(invoice)
        self.db.flush()
        
        student.active_subscription_id = subscription_id
        self.db.add(student)
        self.db.commit()
        self.db.refresh(student_subscription)

        return student_subscription

    def update_auto_renewal(
        self,
        student_subscription_id: int,
        is_auto_renew: bool,
        updated_by_id: int
    ) -> StudentSubscription:
        """Обновление статуса автопродления"""
        # Проверяем права
        self.validate_admin(updated_by_id)

        subscription = self.get_student_subscription(student_subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        subscription.is_auto_renew = is_auto_renew
        self.db.commit()
        self.db.refresh(subscription)

        return subscription

    def freeze_subscription(
        self,
        student_subscription_id: int,
        freeze_start_date: datetime,
        freeze_duration_days: int,
        updated_by_id: int
    ) -> StudentSubscription:
        """Заморозка абонемента"""
        # Проверяем права
        self.validate_admin(updated_by_id)

        subscription = self.get_student_subscription(student_subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Проверяем, что абонемент активен
        if subscription.status != "active":
            raise HTTPException(status_code=400, detail="Can only freeze active subscriptions")

        # Устанавливаем даты заморозки
        subscription.freeze_start_date = freeze_start_date
        subscription.freeze_end_date = freeze_start_date + timedelta(days=freeze_duration_days)

        # Пересчитываем дату окончания
        subscription.end_date = subscription.computed_end_date

        self.db.commit()
        self.db.refresh(subscription)

        logger.info(f"Subscription after freeze: {subscription.status}")
        logger.info(f"Subscription after freeze: {subscription.freeze_start_date}")
        logger.info(f"Subscription after freeze: {subscription.freeze_end_date}")
      
        return subscription

    def unfreeze_subscription(
        self,
        student_subscription_id: int,
        updated_by_id: int
    ) -> StudentSubscription:
        """Разморозка абонемента"""
        # Проверяем права
        self.validate_admin(updated_by_id)

        subscription = self.get_student_subscription(student_subscription_id)
        logger.info(f"Subscription: {subscription.status}")
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Проверяем, что абонемент заморожен
        if (not subscription.freeze_start_date and not subscription.freeze_end_date):
            raise HTTPException(status_code=400, detail="Subscription is not frozen")
        
        # Приводим даты из БД к UTC, если они существуют
        freeze_end_date_utc = subscription.freeze_end_date.replace(tzinfo=timezone.utc) if subscription.freeze_end_date else None
        freeze_start_date_utc = subscription.freeze_start_date.replace(tzinfo=timezone.utc) if subscription.freeze_start_date else None
        current_time_utc = datetime.now(timezone.utc)

        if not freeze_end_date_utc or not freeze_start_date_utc: # Дополнительная проверка на None, хотя логика выше должна это покрывать
             raise HTTPException(status_code=400, detail="Frozen dates are missing unexpectedly")

        freeze_remaining_days = min((freeze_end_date_utc - current_time_utc).days, (freeze_end_date_utc - freeze_start_date_utc).days)
        if freeze_remaining_days > 0:
            subscription.end_date = subscription.end_date - timedelta(days=freeze_remaining_days)
       
        # Убираем заморозку
        subscription.freeze_start_date = None
        subscription.freeze_end_date = None

        self.db.commit()
        self.db.refresh(subscription)

        return subscription

    def process_auto_renewals(self, admin_id: int) -> List[StudentSubscription]:
        """
        Проверяет абонементы с включенным автопродлением, которые заканчиваются сегодня,
        и создает новые абонементы на следующий период.
        """
        from app.services.invoice import InvoiceService
        invoice_service = InvoiceService(self.db)
        
        # Получаем все активные абонементы с автопродлением, которые заканчиваются сегодня
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        subscriptions_to_renew = (
            self.db.query(StudentSubscription)
            .filter(
                and_(
                    StudentSubscription.is_auto_renew == True,
                    StudentSubscription.end_date >= today_start,
                    StudentSubscription.end_date < today_end,
                    StudentSubscription.status == "active",
                    StudentSubscription.auto_renewal_invoice_id.is_(None)
                )
            )
            .all()
        )

        renewed_subscriptions = []
        for subscription in subscriptions_to_renew:
            # Создаем инвойс для автопродления
            auto_renewal_invoice = invoice_service.create_auto_renewal_invoice(
                student_subscription=subscription
            )
            
            # Создаем новый абонемент, который начнется сразу после окончания текущего
            new_subscription = StudentSubscription(
                student_id=subscription.student_id,
                subscription_id=subscription.subscription_id,
                start_date=subscription.end_date,  # Начинается сразу после окончания текущего
                end_date=subscription.end_date + timedelta(days=subscription.subscription.validity_days),
                is_auto_renew=True,
                sessions_left=subscription.subscription.number_of_sessions + min(subscription.sessions_left, 3),  # Сразу добавляем перенесенные тренировки
                transferred_sessions=min(subscription.sessions_left, 3)  # Фиксируем количество перенесенных тренировок
            )
            self.db.add(new_subscription)
            
            # Связываем текущий абонемент с инвойсом автопродления
            subscription.auto_renewal_invoice_id = auto_renewal_invoice.id
            
            renewed_subscriptions.append(new_subscription)

        self.db.commit()
        for subscription in renewed_subscriptions:
            self.db.refresh(subscription)

        return renewed_subscriptions

    def auto_unfreeze_expired_subscriptions(self, admin_id: int) -> List[StudentSubscription]:
        """
        Автоматически размораживает абонементы, у которых период заморозки уже закончился.
        Вызывается по расписанию или вручную администратором.
        """
        current_time = datetime.now(timezone.utc)
        
        # Находим все абонементы с истёкшей заморозкой
        expired_frozen_subscriptions = (
            self.db.query(StudentSubscription)
            .filter(
                and_(
                    StudentSubscription.freeze_end_date.isnot(None),
                    StudentSubscription.freeze_end_date < current_time
                )
            )
            .all()
        )
        
        unfrozen_subscriptions = []
        for subscription in expired_frozen_subscriptions:
            logger.info(f"Auto-unfreezing subscription {subscription.id} for student {subscription.student_id}")
            
            # Сбрасываем поля заморозки
            subscription.freeze_start_date = None
            subscription.freeze_end_date = None
            
            unfrozen_subscriptions.append(subscription)
        
        if unfrozen_subscriptions:
            self.db.commit()
            for subscription in unfrozen_subscriptions:
                self.db.refresh(subscription)
            
            logger.info(f"Auto-unfroze {len(unfrozen_subscriptions)} subscriptions")
        
        return unfrozen_subscriptions 