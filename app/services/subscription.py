import logging
from datetime import datetime, timezone, timedelta, date
from typing import List, Optional

from sqlalchemy.orm import Session

from app.crud import subscription as crud
from app.crud import student as student_crud
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

from app.database import transactional
from app.services.financial import FinancialService
from app.services.student_service import StudentService
from app.errors.subscription_errors import (
    SubscriptionError,
    SubscriptionNotFound,
    SubscriptionNotActive,
    SubscriptionAlreadyFrozen,
    SubscriptionNotFrozen
)

logger = logging.getLogger(__name__)

class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db
        self.financial_service = FinancialService(db)
        self.student_service = StudentService()

    # --- Public Methods (Transactional) ---

    def create_subscription(self, subscription_data: SubscriptionCreate) -> Subscription:
        """Creates a new subscription type."""
        with transactional(self.db) as session:
            return crud.create_subscription(session, subscription_data)

    def update_subscription(self, subscription_id: int, subscription_data: SubscriptionUpdate) -> Optional[Subscription]:
        """Updates an existing subscription type."""
        with transactional(self.db) as session:
            return crud.update_subscription(session, subscription_id, subscription_data)

    def add_subscription_to_student(
        self,
        student_id: int,
        subscription_id: int,
        is_auto_renew: bool,
        created_by_id: int
    ) -> StudentSubscription:
        """Adds a subscription to a student, creating an associated invoice."""
        with transactional(self.db) as session:
            return self._add_subscription_to_student_logic(
                session, student_id, subscription_id, is_auto_renew, created_by_id
            )

    def update_auto_renewal(
        self,
        student_subscription_id: int,
        is_auto_renew: bool,
        updated_by_id: int
    ) -> StudentSubscription:
        """Updates the auto-renewal status of a student subscription."""
        with transactional(self.db) as session:
            return self._update_auto_renewal_logic(session, student_subscription_id, is_auto_renew, updated_by_id)

    def freeze_subscription(
        self,
        student_subscription_id: int,
        freeze_start_date: datetime,
        freeze_duration_days: int,
        updated_by_id: int
    ) -> StudentSubscription:
        """Freezes a student subscription."""
        with transactional(self.db) as session:
            return self._freeze_subscription_logic(session, student_subscription_id, freeze_start_date, freeze_duration_days, updated_by_id)

    def unfreeze_subscription(
        self,
        student_subscription_id: int,
        updated_by_id: int
    ) -> StudentSubscription:
        """Unfreezes a student subscription."""
        with transactional(self.db) as session:
            return self._unfreeze_subscription_logic(session, student_subscription_id, updated_by_id)

    def process_auto_renewals(self, days_back: int = 7) -> List[StudentSubscription]:
        """
        Processes auto-renewals for subscriptions ending today or that ended in the past.
        This method is designed to be called by a scheduled task.
        
        Args:
            days_back: How many days back to look for expired subscriptions (default: 7)
        """
        # This entire method will run in a single transaction
        with transactional(self.db) as session:
            return self._process_auto_renewals_logic(session, days_back)

    def auto_unfreeze_expired_subscriptions(self) -> List[StudentSubscription]:
        """
        Automatically unfreezes subscriptions whose freeze period has expired.
        This method is designed to be called by a scheduled task.
        """
        # This entire method will run in a single transaction
        with transactional(self.db) as session:
            return self._auto_unfreeze_expired_subscriptions_logic(session)

    # --- Private Logic Methods (Non-Transactional) ---

    def _add_subscription_to_student_logic(
        self,
        session: Session,
        student_id: int,
        subscription_id: int,
        is_auto_renew: bool,
        created_by_id: int
    ) -> StudentSubscription:
        student = student_crud.get_student_by_id(session, student_id)
        if not student:
            raise SubscriptionNotFound("Student not found")

        subscription = crud.get_subscription_by_id(session, subscription_id)
        if not subscription:
            raise SubscriptionNotFound("Subscription not found")

        if not student.is_active:
            raise SubscriptionNotActive("Cannot add subscription to inactive student")

        start_date = datetime.now(timezone.utc)
        end_date = start_date + timedelta(days=subscription.validity_days)

        student_subscription_data = StudentSubscriptionCreate(
            student_id=student_id,
            subscription_id=subscription_id,
            start_date=start_date,
            end_date=end_date,
            is_auto_renew=is_auto_renew,
            sessions_left=subscription.number_of_sessions,
            transferred_sessions=0,
            freeze_start_date=None,
            freeze_end_date=None
        )
        
        student_subscription = crud.create_student_subscription(session, student_subscription_data)
        
        # Use InvoiceService's private method, which does not commit
        invoice_data = InvoiceCreate(
            client_id=student.client_id,
            student_id=student_id,
            subscription_id=subscription_id,
            type=InvoiceType.SUBSCRIPTION,
            amount=subscription.price,
            description=f"Subscription: {subscription.name}",
            status=InvoiceStatus.UNPAID, 
            is_auto_renewal=False
        )
        
        # Call the financial service method
        self.financial_service.create_standalone_invoice(invoice_data, auto_pay=True)
        
        self.student_service.update_active_subscription_id(session, student)
        session.refresh(student_subscription)
        
        return student_subscription

    def _update_auto_renewal_logic(
        self,
        session: Session,
        student_subscription_id: int,
        is_auto_renew: bool,
        updated_by_id: int
    ) -> StudentSubscription:
        subscription = crud.get_student_subscription(session, student_subscription_id)
        if not subscription:
            raise SubscriptionNotFound("Subscription not found")

        updated_subscription = crud.update_student_subscription(
            session, 
            student_subscription_id, 
            StudentSubscriptionUpdate(is_auto_renew=is_auto_renew)
        )
        
        return updated_subscription

    def _freeze_subscription_logic(
        self,
        session: Session,
        student_subscription_id: int,
        freeze_start_date: datetime,
        freeze_duration_days: int,
        updated_by_id: int
    ) -> StudentSubscription:
        subscription = crud.get_student_subscription(session, student_subscription_id)
        if not subscription:
            raise SubscriptionNotFound("Subscription not found")

        if subscription.status != "active":
            raise SubscriptionNotActive("Can only freeze active subscriptions")

        if subscription.freeze_start_date or subscription.freeze_end_date:
            raise SubscriptionAlreadyFrozen("Subscription is already frozen")

        freeze_end_date = freeze_start_date + timedelta(days=freeze_duration_days)
        
        # Продлеваем дату окончания абонемента
        new_end_date = subscription.end_date + timedelta(days=freeze_duration_days)

        update_data = StudentSubscriptionUpdate(
            freeze_start_date=freeze_start_date,
            freeze_end_date=freeze_end_date,
            end_date=new_end_date
        )

        frozen_subscription = crud.update_student_subscription(
            session,
            student_subscription_id,
            update_data
        )

        if not frozen_subscription:
            raise SubscriptionError("Failed to freeze subscription")

        logger.debug(f"Subscription after freeze: {frozen_subscription.status}")
        logger.debug(f"Subscription after freeze: {frozen_subscription.freeze_start_date}")
        logger.debug(f"Subscription after freeze: {frozen_subscription.freeze_end_date}")

        return frozen_subscription

    def _unfreeze_subscription_logic(
        self,
        session: Session,
        student_subscription_id: int,
        updated_by_id: int
    ) -> StudentSubscription:
        subscription = crud.get_student_subscription(session, student_subscription_id)
        if not subscription:
            raise SubscriptionNotFound("Subscription not found")

        if not subscription.freeze_start_date or not subscription.freeze_end_date:
            raise SubscriptionNotFrozen("Subscription is not frozen")
        
        freeze_end_date_utc = subscription.freeze_end_date.replace(tzinfo=timezone.utc)
        current_time_utc = datetime.now(timezone.utc)

        # Рассчитываем неиспользованные дни заморозки
        remaining_freeze_days = 0
        if current_time_utc < freeze_end_date_utc:
            remaining_freeze_days = (freeze_end_date_utc - current_time_utc).days

        # Корректируем дату окончания абонемента
        new_end_date = subscription.end_date
        if remaining_freeze_days > 0:
            new_end_date -= timedelta(days=remaining_freeze_days)

        update_data = StudentSubscriptionUpdate(
            freeze_start_date=None,
            freeze_end_date=None,
            end_date=new_end_date
        )
        
        unfrozen_subscription = crud.update_student_subscription(
            session,
            student_subscription_id,
            update_data
        )
        
        if not unfrozen_subscription:
            raise SubscriptionError("Failed to unfreeze subscription")

        return unfrozen_subscription

    def _process_auto_renewals_logic(self, session: Session, days_back: int = 7) -> List[StudentSubscription]:
        subscriptions_to_renew = crud.get_auto_renewal_subscriptions(session, days_back)

        logger.info(f"Found {len(subscriptions_to_renew)} subscriptions for auto-renewal (looking back {days_back} days)")
        renewed_subscriptions = []
        current_time = datetime.now(timezone.utc)
        
        for subscription in subscriptions_to_renew:
            try:
                student = student_crud.get_student_by_id(session, subscription.student_id)
                if not student or not student.is_active:
                    logger.warning(f"Student {subscription.student_id} not found or inactive, skipping auto-renewal")
                    continue
                
                subscription_template = crud.get_subscription_by_id(session, subscription.subscription_id)
                if not subscription_template or not subscription_template.is_active:
                    logger.warning(f"Subscription template {subscription.subscription_id} not found or inactive, skipping auto-renewal")
                    continue
                
                # Calculate if this is a delayed renewal
                days_expired = (current_time.date() - subscription.end_date.date()).days
                is_delayed_renewal = days_expired > 0
                
                # For delayed renewals, start from today; for current renewals, start from next day
                if is_delayed_renewal:
                    new_start_date = current_time
                    logger.info(f"Processing delayed auto-renewal for subscription {subscription.id}, expired {days_expired} days ago")
                else:
                    new_start_date = subscription.end_date + timedelta(days=1)
                
                new_subscription_data = StudentSubscriptionCreate(
                    student_id=subscription.student_id,
                    subscription_id=subscription.subscription_id,
                    start_date=new_start_date,
                    end_date=new_start_date + timedelta(days=subscription_template.validity_days),
                    is_auto_renew=True,
                    sessions_left=subscription_template.number_of_sessions,
                    transferred_sessions=0,
                    freeze_start_date=None,
                    freeze_end_date=None
                )
                
                new_subscription = crud.create_student_subscription(session, new_subscription_data)

                # For delayed renewals, transfer all unused sessions; for current renewals, limit to 3
                max_sessions_to_transfer = subscription.sessions_left if is_delayed_renewal else min(3, subscription.sessions_left)
                crud.transfer_sessions(session, subscription, new_subscription, max_sessions_to_transfer)

                # Create appropriate invoice description
                if is_delayed_renewal:
                    description = f"Delayed Auto-renewal: {subscription_template.name} (expired {days_expired} days ago)"
                else:
                    description = f"Auto-renewal: {subscription_template.name}"
                
                invoice_data = InvoiceCreate(
                    client_id=student.client_id,
                    student_id=subscription.student_id,
                    subscription_id=subscription.subscription_id,
                    student_subscription_id=new_subscription.id, 
                    type=InvoiceType.SUBSCRIPTION,
                    amount=subscription_template.price,
                    description=description,
                    status=InvoiceStatus.UNPAID,
                    is_auto_renewal=True
                )
                logger.debug(f"Creating invoice with student_subscription_id={new_subscription.id}")
                
                # Call the financial service method
                self.financial_service.create_standalone_invoice(invoice_data, auto_pay=True)
                logger.debug(f"Created invoice for auto-renewal")
                
                crud.update_subscription_auto_renewal_invoice(
                    session, 
                    subscription.id, 
                    new_subscription.id # This should be the invoice ID, not new_subscription.id
                )
                
                renewed_subscriptions.append(new_subscription)
                
                if is_delayed_renewal:
                    logger.info(f"Successfully processed delayed auto-renewal for subscription {subscription.id} "
                              f"(expired {days_expired} days ago) for student {subscription.student_id}, "
                              f"transferred {max_sessions_to_transfer} sessions")
                else:
                    logger.info(f"Successfully auto-renewed subscription {subscription.id} for student {subscription.student_id}")
                
            except Exception as e:
                logger.error(f"Failed to auto-renew subscription {subscription.id} for student {subscription.student_id}: {str(e)}")
                continue

        logger.info(f"Successfully renewed {len(renewed_subscriptions)} subscriptions")
        return renewed_subscriptions

    def _auto_unfreeze_expired_subscriptions_logic(self, session: Session) -> List[StudentSubscription]:
        current_time = datetime.now(timezone.utc)
        
        frozen_subscriptions = crud.get_frozen_subscriptions(session)
        
        unfrozen_subscriptions = []
        
        for subscription in frozen_subscriptions:
            try:
                unfrozen_subscription = crud.unfreeze_subscription(session, subscription.id)
                
                if unfrozen_subscription:
                    unfrozen_subscriptions.append(unfrozen_subscription)
                    logger.info(f"Auto-unfroze subscription {subscription.id} for student {subscription.student_id}")
                    
            except Exception as e:
                logger.error(f"Failed to unfreeze subscription {subscription.id} for student {subscription.student_id}: {str(e)}")
                continue

        return unfrozen_subscriptions