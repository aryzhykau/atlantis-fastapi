# tests/unit/test_financial_service.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.services.financial import FinancialService
from app.models import Invoice, InvoiceStatus, InvoiceType, Payment, User, PaymentHistory
from app.schemas.invoice import InvoiceCreate
from app.schemas.user import UserUpdate
from app.models.payment_history import OperationType

# Mock the transactional context manager
@pytest.fixture
def mock_transactional():
    with patch('app.services.financial.transactional') as mock_transactional:
        mock_session = MagicMock(spec=Session)
        mock_transactional.return_value.__enter__.return_value = mock_session
        yield mock_transactional, mock_session

class TestFinancialService:

    def test_create_standalone_invoice(self, mock_transactional):
        """Test the public method for creating an invoice, ensuring it uses the transactional context."""
        mock_context, mock_session = mock_transactional
        db_mock = Mock()
        service = FinancialService(db_mock)

        with patch.object(service, '_create_and_process_invoice_logic') as mock_logic:
            mock_invoice = Mock(spec=Invoice)
            mock_logic.return_value = mock_invoice
            invoice_data = Mock(spec=InvoiceCreate, client_id=1, student_id=1, subscription_id=None, training_id=None)

            result = service.create_standalone_invoice(invoice_data, auto_pay=True)

            mock_context.assert_called_once_with(db_mock)
            mock_logic.assert_called_once_with(mock_session, invoice_data, True)
            assert result == mock_invoice

    @patch('app.services.financial.invoice_crud')
    @patch('app.services.financial.user_crud')
    def test_create_and_process_invoice_logic_no_autopay(self, mock_user_crud, mock_invoice_crud):
        """Test the core logic for creating an invoice without auto-payment."""
        mock_session = Mock(spec=Session)
        service = FinancialService(mock_session)

        mock_invoice = Mock(spec=Invoice)
        mock_invoice_crud.create_invoice.return_value = mock_invoice
        invoice_data = Mock(spec=InvoiceCreate)

        result = service._create_and_process_invoice_logic(mock_session, invoice_data, auto_pay=False)

        mock_invoice_crud.create_invoice.assert_called_once_with(mock_session, invoice_data)
        # Ensure payment logic was NOT called
        mock_user_crud.get_user.assert_not_called()
        mock_user_crud.update_user.assert_not_called()
        mock_invoice_crud.mark_invoice_as_paid.assert_not_called()
        assert result == mock_invoice

    @patch('app.services.financial.invoice_crud')
    @patch('app.services.financial.user_crud')
    def test_create_and_process_invoice_logic_autopay_sufficient_balance(self, mock_user_crud, mock_invoice_crud):
        """Test the core logic with auto-payment and sufficient balance."""
        mock_session = Mock(spec=Session)
        service = FinancialService(mock_session)

        mock_invoice = Mock(spec=Invoice, id=1, amount=100, client_id=1)
        mock_invoice_crud.create_invoice.return_value = mock_invoice
        mock_user = Mock(spec=User, id=1, balance=150.0)
        mock_user_crud.get_user.return_value = mock_user
        invoice_data = Mock(spec=InvoiceCreate)

        service._create_and_process_invoice_logic(mock_session, invoice_data, auto_pay=True)

        mock_invoice_crud.create_invoice.assert_called_once_with(mock_session, invoice_data)
        mock_user_crud.get_user.assert_called_once_with(mock_session, 1)
        mock_invoice_crud.mark_invoice_as_paid.assert_called_once_with(mock_session, 1)
        mock_user_crud.update_user.assert_called_once_with(mock_session, 1, UserUpdate(balance=50.0))

    @patch('app.services.financial.invoice_crud')
    @patch('app.services.financial.user_crud')
    def test_create_and_process_invoice_logic_autopay_insufficient_balance(self, mock_user_crud, mock_invoice_crud):
        """Test the core logic with auto-payment and insufficient balance."""
        mock_session = Mock(spec=Session)
        service = FinancialService(mock_session)

        mock_invoice = Mock(spec=Invoice, id=1, amount=100, client_id=1)
        mock_invoice_crud.create_invoice.return_value = mock_invoice
        mock_user = Mock(spec=User, id=1, balance=50.0)
        mock_user_crud.get_user.return_value = mock_user
        invoice_data = Mock(spec=InvoiceCreate)

        service._create_and_process_invoice_logic(mock_session, invoice_data, auto_pay=True)

        mock_invoice_crud.mark_invoice_as_paid.assert_not_called()
        mock_user_crud.update_user.assert_not_called()

    def test_register_standalone_payment(self, mock_transactional):
        """Test the public method for registering a payment, ensuring it uses the transactional context."""
        mock_context, mock_session = mock_transactional
        db_mock = Mock()
        service = FinancialService(db_mock)

        # Mock the private logic method
        with patch.object(service, '_register_payment_logic') as mock_logic:
            mock_payment = Mock(spec=Payment)
            mock_logic.return_value = mock_payment

            result = service.register_standalone_payment(client_id=1, amount=100, registered_by_id=1)

            # Verify that the transactional context manager was used
            mock_context.assert_called_once_with(db_mock)
            # Verify that the core logic method was called with the session from the context manager
            mock_logic.assert_called_once_with(mock_session, 1, 100, 1, None)
            # Verify the result
            assert result == mock_payment

    @patch('app.services.financial.payment_crud')
    @patch('app.services.financial.invoice_crud')
    @patch('app.services.financial.PaymentHistory')
    def test_register_payment_logic(self, MockPaymentHistory, mock_invoice_crud, mock_payment_crud):
        """Test the core logic for registering a payment and processing invoices."""
        mock_session = Mock(spec=Session)
        service = FinancialService(mock_session)

        # Setup mocks
        mock_payment = Mock(spec=Payment, amount=100)
        mock_payment_crud.create_payment.return_value = mock_payment
        mock_user = Mock(spec=User, balance=50.0)
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user

        unpaid_invoice = Mock(spec=Invoice, amount=120)
        mock_invoice_crud.get_unpaid_invoices.return_value = [unpaid_invoice]

        # Call the logic method
        service._register_payment_logic(mock_session, client_id=1, amount=100, registered_by_id=1)

        # Assertions
        mock_payment_crud.create_payment.assert_called_once()
        mock_invoice_crud.get_unpaid_invoices.assert_called_once_with(mock_session, client_id=1)
        # Balance (50) + Payment (100) = 150. This is enough to pay the 120 invoice.
        mock_invoice_crud.mark_invoice_as_paid.assert_called_once_with(mock_session, unpaid_invoice.id)
        mock_session.add.assert_called_with(MockPaymentHistory()) # Check if PaymentHistory is added

    @patch('app.services.financial.payment_crud')
    @patch('app.services.financial.invoice_crud')
    @patch('app.services.financial.user_crud')
    def test_register_payment_logic_client_not_found(self, mock_user_crud, mock_invoice_crud, mock_payment_crud):
        """Test _register_payment_logic when client is not found."""
        mock_session = Mock(spec=Session)
        service = FinancialService(mock_session)
        mock_payment = Mock(spec=Payment, amount=100)
        mock_payment_crud.create_payment.return_value = mock_payment

        # Mock the session.query().filter().first() call for User to return None
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Client not found"):
            service._register_payment_logic(mock_session, client_id=999, amount=100, registered_by_id=1)
        mock_session.query.assert_called_with(User)
        mock_invoice_crud.get_unpaid_invoices.assert_not_called()

    def test_cancel_standalone_payment(self, mock_transactional):
        """Test the public method for cancelling a payment, ensuring it uses the transactional context."""
        mock_context, mock_session = mock_transactional
        db_mock = Mock()
        service = FinancialService(db_mock)

        with patch.object(service, '_cancel_payment_logic') as mock_logic:
            mock_payment = Mock(spec=Payment)
            mock_logic.return_value = mock_payment

            result = service.cancel_standalone_payment(payment_id=1, cancelled_by_id=1)

            mock_context.assert_called_once_with(db_mock)
            mock_logic.assert_called_once_with(mock_session, 1, 1, None)
            assert result == mock_payment

    @patch('app.services.financial.payment_crud')
    @patch('app.services.financial.invoice_crud')
    @patch('app.services.financial.user_crud')
    def test_cancel_payment_logic_payment_not_found(self, mock_user_crud, mock_invoice_crud, mock_payment_crud):
        """Test _cancel_payment_logic when payment is not found."""
        mock_session = Mock(spec=Session)
        service = FinancialService(mock_session)
        mock_payment_crud.get_payment.return_value = None

        with pytest.raises(ValueError, match="Payment not found"):
            service._cancel_payment_logic(mock_session, payment_id=999, cancelled_by_id=1)
        mock_payment_crud.get_payment.assert_called_once_with(mock_session, 999)
        mock_payment_crud.cancel_payment.assert_not_called()

    @patch('app.services.financial.payment_crud')
    @patch('app.services.financial.invoice_crud')
    @patch('app.services.financial.user_crud')
    def test_cancel_payment_logic_user_not_found(self, mock_user_crud, mock_invoice_crud, mock_payment_crud):
        """Test _cancel_payment_logic when user is not found for cancellation."""
        mock_session = Mock(spec=Session)
        service = FinancialService(mock_session)
        mock_payment = Mock(spec=Payment, client_id=1, amount=100)
        mock_payment_crud.get_payment.return_value = mock_payment
        mock_payment_crud.cancel_payment.return_value = mock_payment # Assume cancellation succeeds

        # Mock the session.query().filter().first() call for User
        mock_session.query.return_value.filter.return_value.first.return_value = None # User not found

        with pytest.raises(ValueError, match="Client not found for cancellation"):
            service._cancel_payment_logic(mock_session, payment_id=1, cancelled_by_id=1)
        mock_session.query.assert_called_with(User)
        mock_invoice_crud.get_paid_invoices_by_client.assert_not_called()

    @patch('app.services.financial.payment_crud')
    @patch('app.services.financial.invoice_crud')
    @patch('app.services.financial.user_crud')
    @patch('app.services.financial.PaymentHistory')
    def test_cancel_payment_logic_with_paid_invoices(self, MockPaymentHistory, mock_user_crud, mock_invoice_crud, mock_payment_crud):
        """Test _cancel_payment_logic with paid invoices to revert."""
        mock_session = Mock(spec=Session)
        service = FinancialService(mock_session)

        mock_payment = Mock(spec=Payment, client_id=1, amount=100)
        mock_payment_crud.get_payment.return_value = mock_payment
        mock_payment_crud.cancel_payment.return_value = mock_payment

        # Mock the session.query().filter().first() call for User
        mock_user = Mock(spec=User, id=1, balance=50.0) # Initial balance before payment
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user

        # Create mock paid invoices
        mock_invoice1 = Mock(spec=Invoice, id=101, amount=30, paid_at=datetime(2023, 1, 1, tzinfo=timezone.utc))
        mock_invoice2 = Mock(spec=Invoice, id=102, amount=70, paid_at=datetime(2023, 1, 2, tzinfo=timezone.utc))
        mock_invoice_crud.get_paid_invoices_by_client.return_value = [mock_invoice1, mock_invoice2]

        # Mock session.flush() to prevent errors when user.balance is updated
        mock_session.flush.return_value = None

        result = service._cancel_payment_logic(mock_session, payment_id=1, cancelled_by_id=1, cancellation_reason="Test")

        mock_payment_crud.get_payment.assert_called_once_with(mock_session, 1)
        mock_payment_crud.cancel_payment.assert_called_once_with(mock_session, 1, 1, "Test")
        mock_session.query.assert_called_with(User)
        mock_invoice_crud.get_paid_invoices_by_client.assert_called_once_with(mock_session, 1)
        
        # Assert invoices were marked unpaid
        mock_invoice_crud.mark_invoice_as_unpaid.assert_any_call(mock_session, mock_invoice1.id)
        mock_invoice_crud.mark_invoice_as_unpaid.assert_any_call(mock_session, mock_invoice2.id)
        assert mock_invoice_crud.mark_invoice_as_unpaid.call_count == 2

        # Assert user balance update
        assert mock_user.balance == 150.0 # 50 (initial) + 100 (payment)

        # Assert PaymentHistory record creation
        mock_session.add.assert_called_with(MockPaymentHistory())
        mock_session.flush.assert_called()
        assert result == mock_payment

    @patch('app.services.financial.payment_crud')
    @patch('app.services.financial.invoice_crud')
    @patch('app.services.financial.user_crud')
    @patch('app.services.financial.PaymentHistory')
    def test_cancel_payment_logic_refund_amount_zero_mid_loop(self, MockPaymentHistory, mock_user_crud, mock_invoice_crud, mock_payment_crud):
        """Test _cancel_payment_logic where refund_amount becomes zero mid-loop."""
        mock_session = Mock(spec=Session)
        service = FinancialService(mock_session)

        mock_payment = Mock(spec=Payment, client_id=1, amount=100)
        mock_payment_crud.get_payment.return_value = mock_payment
        mock_payment_crud.cancel_payment.return_value = mock_payment

        mock_user = Mock(spec=User, id=1, balance=50.0)
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user

        # Invoices that will consume the refund amount exactly or with some left over
        mock_invoice1 = Mock(spec=Invoice, id=101, amount=50, paid_at=datetime(2023, 1, 1, tzinfo=timezone.utc))
        mock_invoice2 = Mock(spec=Invoice, id=102, amount=50, paid_at=datetime(2023, 1, 2, tzinfo=timezone.utc))
        mock_invoice3 = Mock(spec=Invoice, id=103, amount=10, paid_at=datetime(2023, 1, 3, tzinfo=timezone.utc)) 
        mock_invoice_crud.get_paid_invoices_by_client.return_value = [mock_invoice3, mock_invoice2, mock_invoice1] # Sorted by paid_at DESC

        mock_session.flush.return_value = None

        result = service._cancel_payment_logic(mock_session, payment_id=1, cancelled_by_id=1, cancellation_reason="Test")

        mock_invoice_crud.mark_invoice_as_unpaid.assert_any_call(mock_session, mock_invoice3.id)
        mock_invoice_crud.mark_invoice_as_unpaid.assert_any_call(mock_session, mock_invoice2.id)
        assert mock_invoice_crud.mark_invoice_as_unpaid.call_count == 2 # Only two invoices should be marked unpaid
        mock_invoice_crud.mark_invoice_as_unpaid.assert_called_with(mock_session, mock_invoice2.id) # Last call
        assert mock_user.balance == 110.0
        assert result == mock_payment

    @patch('app.services.financial.invoice_crud')
    @patch('app.services.financial.FinancialService.create_standalone_invoice')
    def test_create_subscription_invoice(self, mock_create_standalone_invoice, mock_invoice_crud):
        """Test create_subscription_invoice method."""
        mock_session = Mock(spec=Session)
        service = FinancialService(mock_session)
        mock_invoice = Mock(spec=Invoice)
        mock_create_standalone_invoice.return_value = mock_invoice

        result = service.create_subscription_invoice(
            client_id=1, student_id=1, subscription_id=1, amount=100.0, description="Test Sub Invoice", is_auto_renewal=True
        )
        mock_create_standalone_invoice.assert_called_once()
        assert result == mock_invoice

    @patch('app.services.financial.invoice_crud')
    @patch('app.services.financial.FinancialService.create_standalone_invoice')
    def test_create_training_invoice(self, mock_create_standalone_invoice, mock_invoice_crud):
        """Test create_training_invoice method."""
        mock_session = Mock(spec=Session)
        service = FinancialService(mock_session)
        mock_invoice = Mock(spec=Invoice)
        mock_create_standalone_invoice.return_value = mock_invoice

        result = service.create_training_invoice(
            client_id=1, student_id=1, training_id=1, amount=50.0, description="Test Training Invoice"
        )
        mock_create_standalone_invoice.assert_called_once()
        assert result == mock_invoice

    @patch('app.services.financial.invoice_crud')
    @patch('app.services.financial.user_crud')
    def test_cancel_invoice_success(self, mock_user_crud, mock_invoice_crud, mock_transactional):
        """Test cancel_invoice method success path."""
        mock_context, mock_session = mock_transactional
        service = FinancialService(mock_session)
        mock_invoice = Mock(spec=Invoice, id=1, client_id=1, amount=100.0, status=InvoiceStatus.PAID)
        mock_invoice_crud.get_invoice.return_value = mock_invoice
        mock_invoice_crud.cancel_invoice.return_value = mock_invoice
        mock_user = Mock(spec=User, id=1, balance=50.0)
        mock_user_crud.get_user.return_value = mock_user

        result = service.cancel_invoice(invoice_id=1, cancelled_by_id=1)

        mock_context.assert_called_once_with(mock_session)
        mock_invoice_crud.get_invoice.assert_called_once_with(mock_session, 1)
        mock_user_crud.get_user.assert_called_once_with(mock_session, 1)
        mock_user_crud.update_user.assert_called_once_with(mock_session, 1, UserUpdate(balance=150.0))
        mock_invoice_crud.cancel_invoice.assert_called_once_with(mock_session, 1, cancelled_by_id=1)
        assert result == mock_invoice

    @patch('app.services.financial.invoice_crud')
    def test_cancel_invoice_not_found(self, mock_invoice_crud, mock_transactional):
        """Test cancel_invoice method when invoice is not found."""
        mock_context, mock_session = mock_transactional
        service = FinancialService(mock_session)
        mock_invoice_crud.get_invoice.return_value = None

        with pytest.raises(ValueError, match="Invoice not found"):
            service.cancel_invoice(invoice_id=999, cancelled_by_id=1)
        mock_invoice_crud.get_invoice.assert_called_once_with(mock_session, 999)

    @patch('app.services.financial.invoice_crud')
    @patch('app.services.financial.user_crud')
    def test_cancel_invoice_user_not_found(self, mock_user_crud, mock_invoice_crud, mock_transactional):
        """Test cancel_invoice method when user is not found for invoice client."""
        mock_context, mock_session = mock_transactional
        service = FinancialService(mock_session)
        mock_invoice = Mock(spec=Invoice, id=1, client_id=1, amount=100.0, status=InvoiceStatus.PAID) # Set status to PAID
        mock_invoice_crud.get_invoice.return_value = mock_invoice
        mock_user_crud.get_user.return_value = None # Simulate user not found
        mock_invoice_crud.cancel_invoice.return_value = mock_invoice # Ensure it returns the same invoice

        # Expect no error, as the service handles the missing user gracefully (doesn't update balance)
        result = service.cancel_invoice(invoice_id=1, cancelled_by_id=1)

        mock_context.assert_called_once_with(mock_session)
        mock_invoice_crud.get_invoice.assert_called_once_with(mock_session, 1)
        mock_user_crud.get_user.assert_called_once_with(mock_session, 1)
        mock_user_crud.update_user.assert_not_called() # Should not try to update non-existent user
        mock_invoice_crud.cancel_invoice.assert_called_once_with(mock_session, 1, cancelled_by_id=1)
        assert result == mock_invoice

    @patch('app.services.financial.payment_crud')
    def test_get_payment_history_with_client_id(self, mock_payment_crud):
        """Test get_payment_history method with client_id."""
        mock_session = Mock(spec=Session)
        service = FinancialService(mock_session)
        mock_history_items = [Mock(spec=PaymentHistory)]
        mock_payment_crud.get_payment_history.return_value = mock_history_items

        filters = Mock()
        filters.client_id = 1
        filters.skip = 0
        filters.limit = 100

        result = service.get_payment_history(user_id=1, filters=filters)

        mock_payment_crud.get_payment_history.assert_called_once_with(mock_session, client_id=1)
        assert result["items"] == mock_history_items
        assert result["total"] == len(mock_history_items)
        assert result["skip"] == 0
        assert result["limit"] == len(mock_history_items)
        assert result["has_more"] == False

    def test_get_payment_history_no_client_id(self):
        """Test get_payment_history method without client_id."""
        mock_session = Mock(spec=Session)
        service = FinancialService(mock_session)
        filters = Mock()
        filters.client_id = None

        result = service.get_payment_history(user_id=1, filters=filters)

        assert result == {"items": [], "total": 0, "skip": 0, "limit": 0, "has_more": False}

    def test_get_trainer_registered_payments(self):
        """Test get_trainer_registered_payments method (placeholder)."""
        mock_session = Mock(spec=Session)
        service = FinancialService(mock_session)
        result = service.get_trainer_registered_payments(
            trainer_id=1, period="month", client_id=None, amount_min=None, amount_max=None,
            date_from=None, date_to=None, description_search=None, skip=0, limit=10
        )
        assert result == {"payments": [], "total": 0, "skip": 0, "limit": 0, "has_more": False}
