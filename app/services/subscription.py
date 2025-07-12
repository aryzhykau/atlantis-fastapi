import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.crud import subscription as crud
from app.crud import student as student_crud
from app.crud import user as user_crud
from app.crud import invoice as invoice_crud
from app.crud.student_subscription import (
    get_active_student_subscription,
    update_student_subscription,
    freeze_subscription,
    unfreeze_subscription,
    get_student_subscriptions,
    update_subscription_auto_renewal_invoice,
    get_frozen_subscriptions,
    create_student_subscription,
    get_student_subscription,
    get_active_student_subscriptions,
    get_student_subscriptions_by_status,
    update_student_active_subscription,
    get_auto_renewal_subscriptions
)
from app.models import (
    Subscription,
    Student,
    StudentSubscription,
    InvoiceStatus,
    InvoiceType
)
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    StudentSubscriptionCreate,
    StudentSubscriptionUpdate
)
from app.schemas.invoice import InvoiceCreate
from app.utils.financial_processor import create_and_pay_invoice

logger = logging.getLogger(__name__)

class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db

    def get_subscription(self, subscription_id: int) -> Optional[Subscription]:
        """Получение абонемента по ID"""
        return crud.get_subscription(self.db, subscription_id)

    def get_all_subscriptions(self) -> List[Subscription]:
        """Получение всех абонементов"""
        return crud.get_all_subscriptions(self.db)

    def get_active_subscriptions(self) -> List[Subscription]:
        """Получение активных абонементов"""
        return crud.get_active_subscriptions(self.db)

    def get_subscription_by_name(self, name: str) -> Optional[Subscription]:
        """Получение абонемента по названию"""
        return crud.get_subscription_by_name(self.db, name)

    def create_subscription(self, subscription: SubscriptionCreate) -> Subscription:
        """Создание нового абонемента"""
        return crud.create_subscription(self.db, subscription)

    def update_subscription(self, subscription_id: int, subscription: SubscriptionUpdate) -> Optional[Subscription]:
        """Обновление абонемента"""
        return crud.update_subscription(self.db, subscription_id, subscription)

    def get_student_subscription(self, student_subscription_id: int) -> Optional[StudentSubscription]:
        """Получение подписки студента по ID"""
        return get_student_subscription(self.db, student_subscription_id)

    def get_student_subscriptions(self, student_id: int, status: Optional[str] = None, include_expired: bool = False) -> List[StudentSubscription]:
        """Получение подписок студента"""
        return get_student_subscriptions(self.db, student_id, status, include_expired)

    def get_active_student_subscriptions(self, student_id: int) -> List[StudentSubscription]:
        """Получение активных подписок студента"""
        return get_active_student_subscriptions(self.db, student_id)

    def get_student_subscriptions_by_status(self, student_id: int, status: str) -> List[StudentSubscription]:
        """Получение подписок студента по статусу"""
        return get_student_subscriptions_by_status(self.db, student_id, status)

    def add_subscription_to_student(
        self,
        student_id: int,
        subscription_id: int,
        is_auto_renew: bool,
        created_by_id: int
    ) -> StudentSubscription:
        """Добавление абонемента студенту"""
        # Получаем студента
        student = student_crud.get_student(self.db, student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Получаем абонемент
        subscription = self.get_subscription(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Проверяем, что студент активен
        if not student.is_active:
            raise HTTPException(status_code=400, detail="Cannot add subscription to inactive student")

        with self.db.begin():
            # Получаем предыдущий активный абонемент
            previous_subscription = get_active_student_subscription(self.db, student_id)

            # Переносим неиспользованные занятия (максимум 3)
            transferred_sessions = 0
            if previous_subscription and previous_subscription.sessions_left > 0:
                transferred_sessions = min(previous_subscription.sessions_left, 3)
                # Обнуляем оставшиеся тренировки в старом абонементе
                previous_subscription.sessions_left = 0
                previous_subscription.transferred_sessions = 0

            # Создаем подписку студента через CRUD
            start_date = datetime.now(timezone.utc)
            end_date = start_date + timedelta(days=subscription.validity_days)

            student_subscription_data = StudentSubscriptionCreate(
                student_id=student_id,
                subscription_id=subscription_id,
                start_date=start_date,
                end_date=end_date,
                is_auto_renew=is_auto_renew,
                sessions_left=subscription.number_of_sessions + transferred_sessions,
                transferred_sessions=transferred_sessions,
                status="active",
                freeze_start_date=None,
                freeze_end_date=None
            )
            
            student_subscription = create_student_subscription(self.db, student_subscription_data)
            
            # Создаем инвойс с автоматической попыткой оплаты через FinancialProcessor
            invoice_data = InvoiceCreate(
                client_id=student.client_id,
                student_id=student_id,
                subscription_id=subscription_id,
                type=InvoiceType.SUBSCRIPTION,
                amount=subscription.price,
                description=f"Subscription: {subscription.name}",
                status=InvoiceStatus.UNPAID,  # FinancialProcessor сам определит статус на основе баланса
                is_auto_renewal=False
            )
            
            invoice = create_and_pay_invoice(self.db, invoice_data, auto_pay=True)
            
            # Обновляем активный абонемент студента через CRUD
            update_student_active_subscription(self.db, student_id, subscription_id)
            self.db.refresh(student_subscription)

        return student_subscription

    def update_auto_renewal(
        self,
        student_subscription_id: int,
        is_auto_renew: bool,
        updated_by_id: int
    ) -> StudentSubscription:
        """Обновление статуса автопродления"""
        subscription = self.get_student_subscription(student_subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        with self.db.begin():
            # Используем CRUD для обновления
            updated_subscription = update_student_subscription(
                self.db, 
                student_subscription_id, 
                StudentSubscriptionUpdate(is_auto_renew=is_auto_renew)
            )
            return updated_subscription

    def freeze_subscription(
        self,
        student_subscription_id: int,
        freeze_start_date: datetime,
        freeze_duration_days: int,
        updated_by_id: int
    ) -> StudentSubscription:
        """Заморозка абонемента"""
        subscription = self.get_student_subscription(student_subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Проверяем, что абонемент активен
        if subscription.status != "active":
            raise HTTPException(status_code=400, detail="Can only freeze active subscriptions")

        with self.db.begin():
            # Используем CRUD для заморозки
            freeze_end_date = freeze_start_date + timedelta(days=freeze_duration_days)
            frozen_subscription = freeze_subscription(
                self.db,
                student_subscription_id,
                freeze_start_date.date(),
                freeze_end_date.date()
            )
            
            if not frozen_subscription:
                raise HTTPException(status_code=400, detail="Failed to freeze subscription")

            logger.debug(f"Subscription after freeze: {frozen_subscription.status}")
            logger.debug(f"Subscription after freeze: {frozen_subscription.freeze_start_date}")
            logger.debug(f"Subscription after freeze: {frozen_subscription.freeze_end_date}")
          
            return frozen_subscription

    def unfreeze_subscription(
        self,
        student_subscription_id: int,
        updated_by_id: int
    ) -> StudentSubscription:
        """Разморозка абонемента"""
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

        with self.db.begin():
            # Используем CRUD для разморозки
            unfrozen_subscription = unfreeze_subscription(self.db, student_subscription_id)
            
            if not unfrozen_subscription:
                raise HTTPException(status_code=400, detail="Failed to unfreeze subscription")

            # Дополнительная логика для пересчета даты окончания
            freeze_remaining_days = min(
                (freeze_end_date_utc - current_time_utc).days, 
                (freeze_end_date_utc - freeze_start_date_utc).days
            )
            if freeze_remaining_days > 0:
                # Обновляем дату окончания через CRUD
                update_data = StudentSubscriptionUpdate(
                    end_date=unfrozen_subscription.end_date - timedelta(days=freeze_remaining_days)
                )
                unfrozen_subscription = update_student_subscription(
                    self.db, 
                    student_subscription_id, 
                    update_data
                )

        return unfrozen_subscription

    def process_auto_renewals(self) -> List[StudentSubscription]:
        """
        Проверяет абонементы с включенным автопродлением, которые заканчиваются сегодня,
        и создает новые абонементы на следующий период.
        """
        # Получаем все активные абонементы с автопродлением, которые заканчиваются сегодня
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        # Получаем подписки с автопродлением, которые заканчиваются сегодня
        subscriptions_to_renew = get_auto_renewal_subscriptions(self.db, today_start, today_end)

        logger.info(f"Found {len(subscriptions_to_renew)} subscriptions for auto-renewal")
        renewed_subscriptions = []
        
        for subscription in subscriptions_to_renew:
            try:
                # Проверяем, что студент и абонемент все еще существуют и активны
                student = student_crud.get_student(self.db, subscription.student_id)
                if not student or not student.is_active:
                    logger.warning(f"Student {subscription.student_id} not found or inactive, skipping auto-renewal")
                    continue
                
                subscription_template = self.get_subscription(subscription.subscription_id)
                if not subscription_template or not subscription_template.is_active:
                    logger.warning(f"Subscription template {subscription.subscription_id} not found or inactive, skipping auto-renewal")
                    continue
                
                with self.db.begin():
                    # Рассчитываем перенос занятий (максимум 3)
                    transferred_sessions = min(subscription.sessions_left, 3)
                    
                    # Создаем новый абонемент через CRUD
                    new_subscription_data = StudentSubscriptionCreate(
                        student_id=subscription.student_id,
                        subscription_id=subscription.subscription_id,
                        start_date=subscription.end_date,  # Начинается сразу после окончания текущего
                        end_date=subscription.end_date + timedelta(days=subscription_template.validity_days),
                        is_auto_renew=True,
                        sessions_left=subscription_template.number_of_sessions + transferred_sessions,
                        transferred_sessions=transferred_sessions,
                        status="active",
                        freeze_start_date=None,
                        freeze_end_date=None
                    )
                    
                    new_subscription = create_student_subscription(self.db, new_subscription_data)

                    # Обновляем старую подписку - обнуляем оставшиеся занятия
                    update_student_subscription(
                        self.db,
                        subscription.id,
                        StudentSubscriptionUpdate(sessions_left=0, transferred_sessions=0)
                    )

                    # Создаем инвойс для автопродления через FinancialProcessor
                    invoice_data = InvoiceCreate(
                        client_id=student.client_id,
                        student_id=subscription.student_id,
                        subscription_id=subscription.subscription_id,
                        student_subscription_id=new_subscription.id,  # Сразу связываем с новой подпиской
                        type=InvoiceType.SUBSCRIPTION,
                        amount=subscription_template.price,
                        description=f"Auto-renewal: {subscription_template.name}",
                        status=InvoiceStatus.UNPAID,
                        is_auto_renewal=True
                    )
                    auto_renewal_invoice = create_and_pay_invoice(self.db, invoice_data, auto_pay=True)
                    
                    # Связываем текущий абонемент с инвойсом автопродления (для защиты от дублей) через CRUD
                    update_subscription_auto_renewal_invoice(
                        self.db, 
                        subscription.id, 
                        auto_renewal_invoice.id
                    )
                    renewed_subscriptions.append(new_subscription)
                    logger.info(f"Successfully auto-renewed subscription {subscription.id} for student {subscription.student_id}")
                    
            except Exception as e:
                logger.error(f"Failed to auto-renew subscription {subscription.id} for student {subscription.student_id}: {str(e)}")
                # Продолжаем с другими подписками, не прерывая весь процесс
                continue

        logger.info(f"Successfully renewed {len(renewed_subscriptions)} subscriptions")
        return renewed_subscriptions

    def auto_unfreeze_expired_subscriptions(self) -> List[StudentSubscription]:
        """
        Автоматически размораживает абонементы, у которых истек срок заморозки
        """
        current_time = datetime.now(timezone.utc)
        
        # Получаем все замороженные абонементы
        frozen_subscriptions = get_frozen_subscriptions(self.db)
        
        unfrozen_subscriptions = []
        
        for subscription in frozen_subscriptions:
            try:
                with self.db.begin():
                    # Размораживаем абонемент
                    unfrozen_subscription = unfreeze_subscription(self.db, subscription.id)
                    
                    if unfrozen_subscription:
                        unfrozen_subscriptions.append(unfrozen_subscription)
                        logger.info(f"Auto-unfroze subscription {subscription.id} for student {subscription.student_id}")
                        
            except Exception as e:
                logger.error(f"Failed to unfreeze subscription {subscription.id} for student {subscription.student_id}: {str(e)}")
                # Продолжаем с другими подписками, не прерывая весь процесс
                continue

        return unfrozen_subscriptions 