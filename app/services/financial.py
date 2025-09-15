# app/services/financial.py
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_

from app.crud import invoice as invoice_crud
from app.crud import payment as payment_crud
from app.crud import user as user_crud
from app.crud import student as student_crud
from app.crud import real_training as real_training_crud
from app.crud import subscription as subscription_crud
from app.crud import expense as expense_crud
from app.models import Invoice, InvoiceStatus, InvoiceType, Payment, User, PaymentHistory, Expense, ExpenseType
from app.models.payment_history import OperationType
from app.schemas.invoice import InvoiceCreate
from app.schemas.expense import ExpenseCreate, ExpenseTypeCreate
from app.schemas.user import UserUpdate
from app.database import transactional

logger = logging.getLogger(__name__)

class FinancialService:
    def __init__(self, db: Session):
        self.db = db

    def _refund_paid_invoice(self, session: Session, invoice: Invoice, cancelled_by_id: int) -> None:
        """
        Refunds a paid invoice by creating a refund payment, updating the client's balance,
        and creating a payment history record.
        """
        # 1. Get the client
        user = user_crud.get_user_by_id(session, invoice.client_id)
        if not user:
            raise ValueError("Client not found for refund")

        user_initial_balance = user.balance if user.balance is not None else 0.0

        # 2. Create a refund payment
        refund_payment = payment_crud.create_payment(
            session,
            client_id=invoice.client_id,
            amount=-invoice.amount,
            registered_by_id=cancelled_by_id,
            description=f"Refund for cancelled invoice {invoice.id}",
        )

        # 3. Update client balance
        user.balance += invoice.amount
        session.add(user)
        session.flush()

        # 4. Create payment history record
        payment_history = PaymentHistory(
            client_id=invoice.client_id,
            payment_id=refund_payment.id,
            invoice_id=invoice.id,
            operation_type=OperationType.REFUND,
            amount=-invoice.amount,
            balance_before=user_initial_balance,
            balance_after=user.balance,
            description=f"Refund for cancelled invoice {invoice.id}",
            created_by_id=cancelled_by_id,
        )
        session.add(payment_history)
        session.flush()

        # 5. Mark invoice as cancelled
        invoice_crud.cancel_invoice(session, invoice.id, cancelled_by_id=cancelled_by_id)

    def attempt_auto_payment(self, session: Session, invoice_id: int) -> bool:
        """Attempts to pay a single invoice using the client's balance."""
        invoice = invoice_crud.get_invoice(session, invoice_id)
        if not invoice:
            raise ValueError("Invoice not found")

        if invoice.status != InvoiceStatus.UNPAID:
            raise ValueError("Invoice is not in UNPAID status")

        user = user_crud.get_user_by_id(session, invoice.client_id)
        if not user:
            raise ValueError("Client not found")

        client_balance = user.balance if user.balance is not None else 0.0

        if client_balance >= invoice.amount:
            invoice_crud.mark_invoice_as_paid(session, invoice.id)
            user_crud.update_user(session, user.id, UserUpdate(balance=client_balance - invoice.amount))
            return True

        return False

    def create_standalone_invoice(
        self, invoice_data: InvoiceCreate, auto_pay: bool = True
    ) -> Invoice:
        """Creates a new invoice and optionally tries to pay it, all within a single transaction."""
        with transactional(self.db) as session:
            # Validate existence of related entities
            client = user_crud.get_user_by_id(session, invoice_data.client_id)
            if not client:
                raise ValueError("Client not found")

            student = student_crud.get_student_by_id(session, invoice_data.student_id)
            if not student:
                raise ValueError("Student not found")

            if invoice_data.subscription_id:
                subscription = subscription_crud.get_subscription_by_id(session, invoice_data.subscription_id)
                if not subscription:
                    raise ValueError("Subscription not found")

            if invoice_data.training_id:
                training = real_training_crud.get_real_training(session, invoice_data.training_id)
                if not training:
                    raise ValueError("Тренировка не найдена")

            invoice = self._create_and_process_invoice_logic(session, invoice_data, auto_pay)
            return invoice

    def _create_and_process_invoice_logic(
        self, session: Session, invoice_data: InvoiceCreate, auto_pay: bool = True
    ) -> Invoice:
        """Core logic to create an invoice and attempt payment. Does not commit."""
        # Create the invoice
        new_invoice = invoice_crud.create_invoice(session, invoice_data)

        if auto_pay:
            # This is a simplified logic. A real system might have more complex rules.
            # For now, we assume if a client has a balance, they want to use it.
            user = user_crud.get_user_by_id(session, new_invoice.client_id)
            client_balance = user.balance if user and user.balance is not None else 0.0

            if client_balance >= new_invoice.amount:
                invoice_crud.mark_invoice_as_paid(session, new_invoice.id)
                user_crud.update_user(session, user.id, UserUpdate(balance=client_balance - new_invoice.amount))

        return new_invoice

    def register_standalone_payment(
        self, client_id: int, amount: float, registered_by_id: int, description: Optional[str] = None
    ) -> Payment:
        """Registers a new payment and processes related invoices within a single transaction."""
        with transactional(self.db) as session:
            payment = self._register_payment_logic(session, client_id, amount, registered_by_id, description)
            return payment

    def _register_payment_logic(
        self, session: Session, client_id: int, amount: float, registered_by_id: int, description: Optional[str] = None
    ) -> Payment:
        """Core logic for registering a payment and applying it to unpaid invoices. Does not commit."""
        # Create the payment
        new_payment = payment_crud.create_payment(
            session,
            client_id=client_id,
            amount=amount,
            registered_by_id=registered_by_id,
            description=description
        )

        # Process unpaid invoices
        user = session.query(User).filter(User.id == client_id).first()
        if not user:
            raise ValueError("Client not found") # Or a more specific exception

        unpaid_invoices = invoice_crud.get_unpaid_invoices(session, client_id=client_id)
        user_initial_balance = user.balance if user.balance is not None else 0.0
        client_balance = user_initial_balance + new_payment.amount

        for invoice in unpaid_invoices:
            if client_balance >= invoice.amount:
                client_balance -= invoice.amount
                invoice_crud.mark_invoice_as_paid(session, invoice.id)
        
        user.balance = client_balance
        session.add(user)
        session.flush()

        # Create payment history record
        payment_history = PaymentHistory(
            client_id=client_id,
            payment_id=new_payment.id,
            operation_type=OperationType.PAYMENT,
            amount=amount,
            balance_before=user_initial_balance,
            balance_after=user.balance,
            description=description,
            created_by_id=registered_by_id
        )
        session.add(payment_history)
        session.flush()

        return new_payment

    def cancel_standalone_payment(
        self, payment_id: int, cancelled_by_id: int, cancellation_reason: Optional[str] = None
    ) -> Payment:
        """Cancels a payment and handles refunds within a single transaction."""
        with transactional(self.db) as session:
            payment = self._cancel_payment_logic(session, payment_id, cancelled_by_id, cancellation_reason)
            return payment

    def _cancel_payment_logic(
        self, session: Session, payment_id: int, cancelled_by_id: int, cancellation_reason: Optional[str] = None
    ) -> Payment:
        """Core logic for cancelling a payment and reverting paid invoices. Does not commit."""
        # 1. Retrieve Payment & Client
        payment_to_cancel = payment_crud.get_payment(session, payment_id)
        if not payment_to_cancel:
            raise ValueError("Payment not found")

        user = user_crud.get_user_by_id(session, payment_to_cancel.client_id)
        if not user:
            raise ValueError("Client not found for cancellation")

        user_initial_balance = user.balance if user.balance is not None else 0.0

        # 2. Apply Refund to Balance
        user.balance -= payment_to_cancel.amount

        # 3. Resolve Negative Balance by Reopening Invoices
        if user.balance < 0:
            paid_invoices = invoice_crud.get_paid_invoices_by_client(session, payment_to_cancel.client_id)
            for invoice in sorted(paid_invoices, key=lambda i: i.paid_at, reverse=True):
                if user.balance >= 0:
                    break
                invoice_crud.mark_invoice_as_unpaid(session, invoice.id)
                user.balance += invoice.amount

        # 4. Cancel the Payment Record
        cancelled_payment = payment_crud.cancel_payment(
            session, payment_id, cancelled_by_id, cancellation_reason
        )

        # 5. Record Cancellation History
        cancellation_history = PaymentHistory(
            client_id=cancelled_payment.client_id,
            payment_id=cancelled_payment.id,
            operation_type=OperationType.CANCELLATION,
            amount=-payment_to_cancel.amount,
            balance_before=user_initial_balance,
            balance_after=user.balance,
            description=cancellation_reason,
            created_by_id=cancelled_by_id
        )
        session.add(cancellation_history)

        # 6. Flush User Changes
        session.add(user)
        session.flush()

        return cancelled_payment

    def get_filtered_payments(self, user_id: int, registered_by_me: bool, period: str) -> List[Payment]:
        # This is a placeholder. Real filtering logic would go here.
        # For now, just return all payments.
        return payment_crud.get_payments(self.db)

    def get_payment_history(self, user_id: int, filters: dict) -> dict:
        # Build a query for PaymentHistory and apply optional filters.
        # `filters` may be a Pydantic model or a plain dict.
        def _get(field):
            if isinstance(filters, dict):
                return filters.get(field)
            return getattr(filters, field, None)

        operation_type = _get('operation_type')
        client_id = _get('client_id')
        created_by_id = _get('created_by_id')
        date_from = _get('date_from')
        date_to = _get('date_to')
        amount_min = _get('amount_min')
        amount_max = _get('amount_max')
        description_search = _get('description_search')
        skip = _get('skip') or 0
        limit = _get('limit') or 50

        query = self.db.query(PaymentHistory)

        if operation_type:
            query = query.filter(PaymentHistory.operation_type == operation_type)

        if client_id:
            query = query.filter(PaymentHistory.client_id == client_id)

        if created_by_id:
            query = query.filter(PaymentHistory.created_by_id == created_by_id)

        # Date filters (expecting YYYY-MM-DD)
        if date_from:
            try:
                from_dt = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(PaymentHistory.created_at >= from_dt)
            except Exception:
                pass

        if date_to:
            try:
                to_dt = datetime.strptime(date_to, "%Y-%m-%d")
                # include the whole day
                to_dt = to_dt + timedelta(days=1)
                query = query.filter(PaymentHistory.created_at < to_dt)
            except Exception:
                pass

        if amount_min is not None:
            try:
                query = query.filter(PaymentHistory.amount >= float(amount_min))
            except Exception:
                pass

        if amount_max is not None:
            try:
                query = query.filter(PaymentHistory.amount <= float(amount_max))
            except Exception:
                pass

        if description_search:
            try:
                query = query.filter(PaymentHistory.description.ilike(f"%{description_search}%"))
            except Exception:
                pass

        total = query.count()

        results = query.order_by(PaymentHistory.created_at.desc()).offset(skip).limit(limit).all()

        items = []
        for ph in results:
            items.append({
                'id': ph.id,
                'client_id': ph.client_id,
                'payment_id': ph.payment_id,
                'invoice_id': ph.invoice_id,
                'operation_type': ph.operation_type,
                'amount': ph.amount,
                'balance_before': ph.balance_before,
                'balance_after': ph.balance_after,
                'description': ph.description,
                'created_at': ph.created_at,
                'created_by_id': ph.created_by_id,
                'client_first_name': ph.client.first_name if ph.client else None,
                'client_last_name': ph.client.last_name if ph.client else None,
                'created_by_first_name': ph.created_by.first_name if ph.created_by else None,
                'created_by_last_name': ph.created_by.last_name if ph.created_by else None,
                'payment_description': ph.payment.description if ph.payment else None,
            })

        has_more = (skip + len(items)) < total

        return {
            'items': items,
            'total': total,
            'skip': skip,
            'limit': limit,
            'has_more': has_more,
        }

    def process_invoices(self, admin_id: int):
        """Placeholder for processing invoices. Logic to be implemented."""
        logger.info(f"Processing invoices initiated by admin_id: {admin_id}")
        # TODO: Implement actual invoice processing logic here
        return {"status": "success", "message": "Invoice processing placeholder executed."}

    def get_invoice(self, invoice_id: int) -> Optional[Invoice]:
        return invoice_crud.get_invoice(self.db, invoice_id)

    def get_invoices(
        self, 
        client_id: Optional[int] = None, 
        student_id: Optional[int] = None, 
        status: Optional[InvoiceStatus] = None, 
        invoice_type: Optional[InvoiceType] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> List[Invoice]:
        """Get invoices with optional filters"""
        return invoice_crud.get_invoices(
            self.db, 
            client_id=client_id, 
            student_id=student_id, 
            status=status, 
            invoice_type=invoice_type,
            skip=skip, 
            limit=limit
        )

    def get_invoice_count(
        self, 
        client_id: Optional[int] = None, 
        student_id: Optional[int] = None, 
        status: Optional[InvoiceStatus] = None, 
        invoice_type: Optional[InvoiceType] = None
    ) -> int:
        """Get total count of invoices with optional filters"""
        return invoice_crud.get_invoice_count(
            self.db, 
            client_id=client_id, 
            student_id=student_id, 
            status=status
        )

    def get_student_invoices(
        self, student_id: int, status: Optional[InvoiceStatus] = None, skip: int = 0, limit: int = 100
    ) -> List[Invoice]:
        return invoice_crud.get_student_invoices(self.db, student_id=student_id, status=status, skip=skip, limit=limit)

    def get_client_invoices(
        self, client_id: int, status: Optional[InvoiceStatus] = None, skip: int = 0, limit: int = 100
    ) -> List[Invoice]:
        return invoice_crud.get_client_invoices(self.db, client_id=client_id, status=status, skip=skip, limit=limit)

    def create_subscription_invoice(
        self,
        client_id: int,
        student_id: int,
        subscription_id: int,
        amount: float,
        description: Optional[str] = None,
        is_auto_renewal: bool = False,
    ) -> Invoice:
        client = user_crud.get_user_by_id(self.db, client_id)
        if not client:
            raise ValueError("Client not found")
        
        student = student_crud.get_student_by_id(self.db, student_id)
        if not student:
            raise ValueError("Student not found") # Or a more specific error if student is not a user

        subscription = subscription_crud.get_subscription_by_id(self.db, subscription_id)
        if not subscription:
            raise ValueError("Subscription not found")

        invoice_data = InvoiceCreate(
            client_id=client_id,
            student_id=student_id,
            subscription_id=subscription_id,
            amount=amount,
            description=description,
            type=InvoiceType.SUBSCRIPTION,
            is_auto_renewal=is_auto_renewal,
        )
        return self.create_standalone_invoice(invoice_data)

    def create_training_invoice(
        self,
        client_id: int,
        student_id: int,
        training_id: int,
        amount: float,
        description: Optional[str] = None,
    ) -> Invoice:
        client = user_crud.get_user_by_id(self.db, client_id)
        if not client:
            raise ValueError("Client not found")

        student = student_crud.get_student_by_id(self.db, student_id)
        if not student:
            raise ValueError("Student not found")

        training = real_training_crud.get_real_training(self.db, training_id)
        if not training:
            raise ValueError("Тренировка не найдена")

        invoice_data = InvoiceCreate(
            client_id=client_id,
            student_id=student_id,
            training_id=training_id,
            amount=amount,
            description=description,
            type=InvoiceType.TRAINING,
        )
        return self.create_standalone_invoice(invoice_data)

    def cancel_invoice(self, invoice_id: int, cancelled_by_id: int) -> Invoice:
        with transactional(self.db) as session:
            invoice = invoice_crud.get_invoice(session, invoice_id)
            if not invoice:
                raise ValueError("Invoice not found")

            if invoice.status == InvoiceStatus.PAID:
                # Revert payment logic (simplified)
                user = user_crud.get_user_by_id(session, invoice.client_id)
                if user:
                    user_balance = user.balance if user.balance is not None else 0.0
                    user_crud.update_user(session, user.id, UserUpdate(balance=user_balance + invoice.amount))
                # TODO: Create a PaymentHistory entry for the refund

            cancelled_invoice = invoice_crud.cancel_invoice(session, invoice_id, cancelled_by_id=cancelled_by_id)
            return cancelled_invoice

    def get_payment_history_with_filters(self, user_id: int, filters: dict) -> dict:
        # Placeholder for payment history with filters
        return {"items": [], "total": 0, "skip": 0, "limit": 0, "has_more": False}

    def get_trainer_registered_payments(self, trainer_id: int, period: str, client_id: Optional[int], amount_min: Optional[float], amount_max: Optional[float], date_from: Optional[str], date_to: Optional[str], description_search: Optional[str], skip: int, limit: int) -> dict:
        """
        Get payments registered by a specific trainer with filtering options.
        """
        # Query with explicit joinedload to ensure client data is loaded
        query = self.db.query(Payment).options(joinedload(Payment.client)).filter(Payment.registered_by_id == trainer_id)
        
        # Apply period filter
        if period:
            now = datetime.now()
            if period == "week":
                start_date = now - timedelta(weeks=1)
            elif period == "2weeks":
                start_date = now - timedelta(weeks=2)
            else:  # period == "all" or other
                start_date = None
                
            if start_date:
                query = query.filter(Payment.payment_date >= start_date)
        
        # Apply date range filters
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(Payment.payment_date >= from_date)
            except ValueError:
                pass  # Invalid date format, skip filter
                
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d")
                # Add 1 day to include the entire day
                to_date = to_date + timedelta(days=1)
                query = query.filter(Payment.payment_date < to_date)
            except ValueError:
                pass  # Invalid date format, skip filter
        
        # Apply other filters
        if client_id:
            query = query.filter(Payment.client_id == client_id)
            
        if amount_min is not None:
            query = query.filter(Payment.amount >= amount_min)
            
        if amount_max is not None:
            query = query.filter(Payment.amount <= amount_max)
            
        if description_search:
            query = query.filter(Payment.description.ilike(f"%{description_search}%"))
        
        # Only include non-cancelled payments
        query = query.filter(Payment.cancelled_at.is_(None))
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        results = query.order_by(Payment.payment_date.desc()).offset(skip).limit(limit).all()
        
        # Debug: Print the first result to see what we're getting
        if results:
            first_payment = results[0]
            print(f"Debug - Payment: {first_payment}")
            print(f"Debug - Client: {first_payment.client}")
            if first_payment.client:
                print(f"Debug - Client name: {first_payment.client.first_name} {first_payment.client.last_name}")
        
        # Transform results to include client information
        payments_with_client_info = []
        for payment in results:
            payment_dict = {
                'id': payment.id,
                'client_id': payment.client_id,
                'amount': payment.amount,
                'description': payment.description,
                'payment_date': payment.payment_date,
                'registered_by_id': payment.registered_by_id,
                'cancelled_at': payment.cancelled_at,
                'cancelled_by_id': payment.cancelled_by_id,
                'client_first_name': payment.client.first_name if payment.client else None,
                'client_last_name': payment.client.last_name if payment.client else None,
            }
            payments_with_client_info.append(payment_dict)
        
        # Calculate has_more
        has_more = (skip + len(payments_with_client_info)) < total
        
        print(f"Debug - Returning {len(payments_with_client_info)} payments with client info")
        if payments_with_client_info:
            print(f"Debug - First payment dict: {payments_with_client_info[0]}")
        
        return {
            "payments": payments_with_client_info,
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": has_more
        }

    def create_expense(self, expense_data: ExpenseCreate) -> Expense:
        return expense_crud.create_expense(self.db, expense=expense_data)

    def get_expenses(
        self, user_id: Optional[int] = None, expense_type_id: Optional[int] = None, skip: int = 0, limit: int = 100
    ) -> List[Expense]:
        return expense_crud.get_expenses(
            self.db, user_id=user_id, expense_type_id=expense_type_id, skip=skip, limit=limit
        )

    def create_expense_type(self, expense_type_data: ExpenseTypeCreate) -> ExpenseType:
        return expense_crud.create_expense_type(self.db, expense_type=expense_type_data)

    def get_expense_types(self, skip: int = 0, limit: int = 100) -> List[ExpenseType]:
        return expense_crud.get_expense_types(self.db, skip=skip, limit=limit)

    def calculate_trainer_salary_for_cancellation(
        self, 
        training_id: int, 
        cancelled_student_id: int, 
        cancellation_time: datetime, 
        training_start_datetime: datetime
    ) -> dict:
        """
        Calculate if trainer should receive salary when a student cancels.
        
        Returns:
        - should_receive_salary: bool
        - reason: str (explanation)
        - remaining_students_count: int
        """
        from datetime import timedelta
        
        training = real_training_crud.get_real_training(self.db, training_id)
        if not training:
            raise ValueError("Тренировка не найдена")
            
        trainer = user_crud.get_user_by_id(self.db, training.responsible_trainer_id)
        if not trainer:
            raise ValueError("Тренер не найден")
            
        # Calculate hours before training
        hours_before = (training_start_datetime - cancellation_time).total_seconds() / 3600
        
        # Count remaining students (excluding the cancelled one)
        remaining_students = [
            student for student in training.students 
            if student.student_id != cancelled_student_id and 
            student.status not in ['CANCELLED_SAFE', 'CANCELLED_PENALTY']
        ]
        remaining_count = len(remaining_students)
        
        # Fixed salary trainers never get individual training salary
        if trainer.is_fixed_salary:
            return {
                "should_receive_salary": False,
                "reason": "Trainer has fixed salary - individual training payments not applicable",
                "remaining_students_count": remaining_count,
                "hours_before_training": hours_before
            }
        
        # Non-fixed salary logic
        if hours_before >= 5:  # 5+ hours before
            if remaining_count > 0:
                return {
                    "should_receive_salary": True,
                    "reason": f"Other students remain ({remaining_count}) - trainer gets salary",
                    "remaining_students_count": remaining_count,
                    "hours_before_training": hours_before
                }
            else:
                return {
                    "should_receive_salary": False,
                    "reason": "No other students remain and cancellation was timely (5+ hours)",
                    "remaining_students_count": remaining_count,
                    "hours_before_training": hours_before
                }
        else:  # Less than 5 hours before
            return {
                "should_receive_salary": True,
                "reason": "Late cancellation (< 5 hours) - trainer compensation applies",
                "remaining_students_count": remaining_count,
                "hours_before_training": hours_before
            }

    def create_trainer_salary_expense(
        self, 
        trainer_id: int, 
        training_id: int, 
        amount: float, 
        description: str,
        created_by_id: int
    ) -> Expense:
        """Create an expense record for trainer salary"""
        
        # Get or create "Trainer Salary" expense type
        trainer_salary_type = expense_crud.get_expense_type_by_name(self.db, "Trainer Salary")
        if not trainer_salary_type:
            from app.schemas.expense import ExpenseTypeCreate
            trainer_salary_type = self.create_expense_type(
                ExpenseTypeCreate(
                    name="Trainer Salary",
                    description="Individual training session payments to trainers"
                )
            )
        
        expense_data = ExpenseCreate(
            user_id=trainer_id,
            expense_type_id=trainer_salary_type.id,
            amount=amount,
            description=description
        )
        
        return self.create_expense(expense_data)
