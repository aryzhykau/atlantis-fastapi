# app/services/financial.py
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

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
                    raise ValueError("Training not found")

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
        # For now, we'll just return all history for the client_id if provided in filters
        # A more robust implementation would apply all filters
        client_id = filters.client_id
        if client_id:
            items = payment_crud.get_payment_history(self.db, client_id=client_id)
            return {
                "items": items,
                "total": len(items),
                "skip": 0,
                "limit": len(items),
                "has_more": False
            }
        return {
            "items": [],
            "total": 0,
            "skip": 0,
            "limit": 0,
            "has_more": False
        }

    def process_invoices(self, admin_id: int):
        """Placeholder for processing invoices. Logic to be implemented."""
        logger.info(f"Processing invoices initiated by admin_id: {admin_id}")
        # TODO: Implement actual invoice processing logic here
        return {"status": "success", "message": "Invoice processing placeholder executed."}

    def get_invoice(self, invoice_id: int) -> Optional[Invoice]:
        return invoice_crud.get_invoice(self.db, invoice_id)

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
            raise ValueError("Training not found")

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
        # Placeholder for trainer registered payments
        return {"payments": [], "total": 0, "skip": 0, "limit": 0, "has_more": False}

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
