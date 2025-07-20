import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.services.subscription import SubscriptionService
from app.models import StudentSubscription, Subscription, Student
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate, StudentSubscriptionCreate, StudentSubscriptionUpdate
from app.schemas.invoice import InvoiceCreate
from app.errors.subscription_errors import (
    SubscriptionError,
    SubscriptionNotFound,
    SubscriptionNotActive,
    SubscriptionAlreadyFrozen,
    SubscriptionNotFrozen
)

# Mock the transactional context manager
@pytest.fixture
def mock_transactional():
    with patch('app.services.subscription.transactional') as mock_transactional:
        # This makes the `with` statement yield the mock session
        mock_session = MagicMock(spec=Session)
        mock_transactional.return_value.__enter__.return_value = mock_session
        yield mock_transactional, mock_session

# Fixtures for common mock objects
@pytest.fixture
def mock_db():
    return Mock(spec=Session)

@pytest.fixture
def mock_subscription_model():
    sub = Mock(spec=Subscription)
    sub.id = 1
    sub.name = "Test Subscription"
    sub.validity_days = 30
    sub.number_of_sessions = 8
    sub.price = 100.0
    sub.is_active = True
    return sub

@pytest.fixture
def mock_student_subscription_model():
    student_sub = Mock(spec=StudentSubscription)
    student_sub.id = 1
    student_sub.student_id = 1
    student_sub.subscription_id = 1
    student_sub.start_date = datetime.now(timezone.utc) - timedelta(days=10)
    student_sub.end_date = datetime.now(timezone.utc) + timedelta(days=20)
    student_sub.is_auto_renew = False
    student_sub.sessions_left = 5
    student_sub.transferred_sessions = 0
    student_sub.freeze_start_date = None
    student_sub.freeze_end_date = None
    student_sub.status = "active"
    return student_sub

@pytest.fixture
def mock_frozen_student_subscription_model():
    # Create a new mock object to avoid modifying the original mock_student_subscription_model
    frozen_sub = Mock(spec=StudentSubscription)
    frozen_sub.id = 1
    frozen_sub.student_id = 1
    frozen_sub.subscription_id = 1
    frozen_sub.start_date = datetime.now(timezone.utc) - timedelta(days=10)
    frozen_sub.end_date = datetime.now(timezone.utc) + timedelta(days=20)
    frozen_sub.is_auto_renew = False
    frozen_sub.sessions_left = 5
    frozen_sub.transferred_sessions = 0
    frozen_sub.freeze_start_date = datetime.now(timezone.utc) - timedelta(days=5)
    frozen_sub.freeze_end_date = datetime.now(timezone.utc) + timedelta(days=5)
    frozen_sub.status = "active" # Should be active to pass the first check
    return frozen_sub

@pytest.fixture
def mock_student_model():
    student = Mock(spec=Student)
    student.id = 1
    student.is_active = True
    student.client_id = 1
    return student

class TestSubscriptionService:

    # --- Test Public Methods (Transactional) ---

    @patch('app.services.subscription.crud')
    def test_create_subscription(self, mock_crud, mock_transactional, mock_db, mock_subscription_model):
        mock_context, mock_session = mock_transactional
        service = SubscriptionService(mock_db)
        
        mock_crud.create_subscription.return_value = mock_subscription_model
        sub_create_data = SubscriptionCreate(name="New Sub", validity_days=30, number_of_sessions=10, price=150.0)

        result = service.create_subscription(sub_create_data)

        mock_context.assert_called_once_with(mock_db)
        mock_crud.create_subscription.assert_called_once_with(mock_session, sub_create_data)
        assert result == mock_subscription_model

    @patch('app.services.subscription.crud')
    def test_update_subscription(self, mock_crud, mock_transactional, mock_db, mock_subscription_model):
        mock_context, mock_session = mock_transactional
        service = SubscriptionService(mock_db)
        
        mock_crud.update_subscription.return_value = mock_subscription_model
        sub_update_data = SubscriptionUpdate(name="Updated Sub")

        result = service.update_subscription(1, sub_update_data)

        mock_context.assert_called_once_with(mock_db)
        mock_crud.update_subscription.assert_called_once_with(mock_session, 1, sub_update_data)
        assert result == mock_subscription_model

    @patch.object(SubscriptionService, '_add_subscription_to_student_logic')
    def test_add_subscription_to_student_public(self, mock_logic, mock_transactional, mock_db, mock_student_subscription_model):
        mock_context, mock_session = mock_transactional
        service = SubscriptionService(mock_db)
        
        mock_logic.return_value = mock_student_subscription_model

        result = service.add_subscription_to_student(1, 1, True, 1)

        mock_context.assert_called_once_with(mock_db)
        mock_logic.assert_called_once_with(mock_session, 1, 1, True, 1)
        assert result == mock_student_subscription_model

    @patch.object(SubscriptionService, '_update_auto_renewal_logic')
    def test_update_auto_renewal_public(self, mock_logic, mock_transactional, mock_db, mock_student_subscription_model):
        mock_context, mock_session = mock_transactional
        service = SubscriptionService(mock_db)
        
        mock_logic.return_value = mock_student_subscription_model

        result = service.update_auto_renewal(1, True, 1)

        mock_context.assert_called_once_with(mock_db)
        mock_logic.assert_called_once_with(mock_session, 1, True, 1)
        assert result == mock_student_subscription_model

    @patch.object(SubscriptionService, '_freeze_subscription_logic')
    def test_freeze_subscription_public(self, mock_logic, mock_transactional, mock_db, mock_frozen_student_subscription_model):
        mock_context, mock_session = mock_transactional
        service = SubscriptionService(mock_db)
        
        mock_logic.return_value = mock_frozen_student_subscription_model
        freeze_start = datetime.now(timezone.utc)
        
        result = service.freeze_subscription(1, freeze_start, 10, 1)

        mock_context.assert_called_once_with(mock_db)
        mock_logic.assert_called_once_with(mock_session, 1, freeze_start, 10, 1)
        assert result == mock_frozen_student_subscription_model

    @patch.object(SubscriptionService, '_unfreeze_subscription_logic')
    def test_unfreeze_subscription_public(self, mock_logic, mock_transactional, mock_db, mock_student_subscription_model):
        mock_context, mock_session = mock_transactional
        service = SubscriptionService(mock_db)
        
        mock_logic.return_value = mock_student_subscription_model
        
        result = service.unfreeze_subscription(1, 1)

        mock_context.assert_called_once_with(mock_db)
        mock_logic.assert_called_once_with(mock_session, 1, 1)
        assert result == mock_student_subscription_model

    @patch.object(SubscriptionService, '_process_auto_renewals_logic')
    def test_process_auto_renewals_public(self, mock_logic, mock_transactional, mock_db, mock_student_subscription_model):
        mock_context, mock_session = mock_transactional
        service = SubscriptionService(mock_db)
        
        mock_logic.return_value = [mock_student_subscription_model]
        
        result = service.process_auto_renewals()

        mock_context.assert_called_once_with(mock_db)
        mock_logic.assert_called_once_with(mock_session)
        assert result == [mock_student_subscription_model]

    @patch.object(SubscriptionService, '_auto_unfreeze_expired_subscriptions_logic')
    def test_auto_unfreeze_expired_subscriptions_public(self, mock_logic, mock_transactional, mock_db, mock_student_subscription_model):
        mock_context, mock_session = mock_transactional
        service = SubscriptionService(mock_db)
        
        mock_logic.return_value = [mock_student_subscription_model]
        
        result = service.auto_unfreeze_expired_subscriptions()

        mock_context.assert_called_once_with(mock_db)
        mock_logic.assert_called_once_with(mock_session)
        assert result == [mock_student_subscription_model]

    # --- Test Private Logic Methods (Non-Transactional) ---

    @patch('app.services.subscription.student_crud')
    @patch('app.services.subscription.crud')
    @patch('app.services.financial.FinancialService') # Patch the class directly
    def test_add_subscription_to_student_logic_success(
        self, MockFinancialService, mock_crud, mock_student_crud, mock_db,
        mock_student_model, mock_subscription_model, mock_student_subscription_model
    ):
        service = SubscriptionService(mock_db)
        # Ensure financial_service is a mock instance
        service.financial_service = MockFinancialService.return_value

        mock_student_crud.get_student_by_id.return_value = mock_student_model
        mock_crud.get_subscription_by_id.return_value = mock_subscription_model
        mock_crud.create_student_subscription.return_value = mock_student_subscription_model
        service.financial_service.create_standalone_invoice.return_value = Mock() # Mock the invoice creation
        mock_student_crud.update_student_active_subscription.return_value = None # Mock this call

        result = service._add_subscription_to_student_logic(mock_db, 1, 1, True, 1)

        mock_student_crud.get_student_by_id.assert_called_once_with(mock_db, 1)
        mock_crud.get_subscription_by_id.assert_called_once_with(mock_db, 1)
        mock_crud.create_student_subscription.assert_called_once()
        service.financial_service.create_standalone_invoice.assert_called_once()
        mock_student_crud.update_student_active_subscription.assert_called_once_with(mock_db, 1, 1)
        mock_db.refresh.assert_called_once_with(mock_student_subscription_model)
        assert result == mock_student_subscription_model

    @patch('app.services.subscription.student_crud')
    def test_add_subscription_to_student_logic_student_not_found(self, mock_student_crud, mock_db):
        service = SubscriptionService(mock_db)
        mock_student_crud.get_student_by_id.return_value = None
        
        with pytest.raises(SubscriptionNotFound, match="Student not found"):
            service._add_subscription_to_student_logic(mock_db, 999, 1, True, 1)

    @patch('app.services.subscription.student_crud')
    @patch('app.services.subscription.crud')
    def test_add_subscription_to_student_logic_subscription_not_found(self, mock_crud, mock_student_crud, mock_db, mock_student_model):
        service = SubscriptionService(mock_db)
        mock_student_crud.get_student_by_id.return_value = mock_student_model
        mock_crud.get_subscription_by_id.return_value = None
        
        with pytest.raises(SubscriptionNotFound, match="Subscription not found"):
            service._add_subscription_to_student_logic(mock_db, 1, 999, True, 1)

    @patch('app.services.subscription.student_crud')
    @patch('app.services.subscription.crud')
    def test_add_subscription_to_student_logic_student_not_active(self, mock_crud, mock_student_crud, mock_db, mock_student_model, mock_subscription_model):
        service = SubscriptionService(mock_db)
        mock_student_model.is_active = False # Set student to inactive
        mock_student_crud.get_student_by_id.return_value = mock_student_model
        mock_crud.get_subscription_by_id.return_value = mock_subscription_model
        
        with pytest.raises(SubscriptionNotActive, match="Cannot add subscription to inactive student"):
            service._add_subscription_to_student_logic(mock_db, 1, 1, True, 1)

    @patch('app.services.subscription.crud')
    def test_update_auto_renewal_logic_success(self, mock_crud, mock_db, mock_student_subscription_model):
        service = SubscriptionService(mock_db)
        mock_crud.get_student_subscription.return_value = mock_student_subscription_model
        mock_crud.update_student_subscription.return_value = mock_student_subscription_model

        result = service._update_auto_renewal_logic(mock_db, 1, True, 1)

        mock_crud.get_student_subscription.assert_called_once_with(mock_db, 1)
        mock_crud.update_student_subscription.assert_called_once()
        assert result == mock_student_subscription_model

    @patch('app.services.subscription.crud')
    def test_update_auto_renewal_logic_not_found(self, mock_crud, mock_db):
        service = SubscriptionService(mock_db)
        mock_crud.get_student_subscription.return_value = None

        with pytest.raises(SubscriptionNotFound, match="Subscription not found"):
            service._update_auto_renewal_logic(mock_db, 999, True, 1)

    @patch('app.services.subscription.crud')
    def test_freeze_subscription_logic_success(self, mock_crud, mock_db, mock_student_subscription_model, mock_frozen_student_subscription_model):
        service = SubscriptionService(mock_db)
        # Ensure the mock is active for this test
        mock_student_subscription_model.status = "active"
        # Ensure it's unfrozen for this test
        mock_student_subscription_model.freeze_start_date = None
        mock_student_subscription_model.freeze_end_date = None
        mock_crud.get_student_subscription.return_value = mock_student_subscription_model
        mock_crud.freeze_subscription.return_value = mock_frozen_student_subscription_model
        freeze_start = datetime.now(timezone.utc)

        result = service._freeze_subscription_logic(mock_db, 1, freeze_start, 10, 1)

        mock_crud.get_student_subscription.assert_called_once_with(mock_db, 1)
        mock_crud.freeze_subscription.assert_called_once()
        assert result == mock_frozen_student_subscription_model

    @patch('app.services.subscription.crud')
    def test_freeze_subscription_logic_not_found(self, mock_crud, mock_db):
        service = SubscriptionService(mock_db)
        mock_crud.get_student_subscription.return_value = None

        with pytest.raises(SubscriptionNotFound, match="Subscription not found"):
            service._freeze_subscription_logic(mock_db, 999, datetime.now(timezone.utc), 10, 1)

    @patch('app.services.subscription.crud')
    def test_freeze_subscription_logic_not_active(self, mock_crud, mock_db, mock_student_subscription_model):
        service = SubscriptionService(mock_db)
        mock_student_subscription_model.status = "inactive" # Set status to inactive
        mock_crud.get_student_subscription.return_value = mock_student_subscription_model

        with pytest.raises(SubscriptionNotActive, match="Can only freeze active subscriptions"):
            service._freeze_subscription_logic(mock_db, 1, datetime.now(timezone.utc), 10, 1)

    @patch('app.services.subscription.crud')
    def test_freeze_subscription_logic_already_frozen(self, mock_crud, mock_db, mock_frozen_student_subscription_model):
        service = SubscriptionService(mock_db)
        # Ensure the mock is active to pass the first check, then frozen for the second
        mock_frozen_student_subscription_model.status = "active"
        mock_frozen_student_subscription_model.freeze_start_date = datetime.now(timezone.utc) - timedelta(days=5)
        mock_frozen_student_subscription_model.freeze_end_date = datetime.now(timezone.utc) + timedelta(days=5)
        mock_crud.get_student_subscription.return_value = mock_frozen_student_subscription_model

        with pytest.raises(SubscriptionAlreadyFrozen, match="Subscription is already frozen"):
            service._freeze_subscription_logic(mock_db, 1, datetime.now(timezone.utc), 10, 1)

    @patch('app.services.subscription.crud')
    def test_unfreeze_subscription_logic_success(self, mock_crud, mock_db, mock_frozen_student_subscription_model, mock_student_subscription_model):
        service = SubscriptionService(mock_db)
        mock_crud.get_student_subscription.return_value = mock_frozen_student_subscription_model
        mock_crud.unfreeze_subscription.return_value = mock_student_subscription_model # Unfrozen state
        mock_crud.update_student_subscription.return_value = mock_student_subscription_model # For end_date adjustment

        result = service._unfreeze_subscription_logic(mock_db, 1, 1)

        mock_crud.get_student_subscription.assert_called_once_with(mock_db, 1)
        mock_crud.unfreeze_subscription.assert_called_once_with(mock_db, 1)
        mock_crud.update_student_subscription.assert_called_once() # For end_date adjustment
        assert result == mock_student_subscription_model

    @patch('app.services.subscription.crud')
    def test_unfreeze_subscription_logic_not_found(self, mock_crud, mock_db):
        service = SubscriptionService(mock_db)
        mock_crud.get_student_subscription.return_value = None

        with pytest.raises(SubscriptionNotFound, match="Subscription not found"):
            service._unfreeze_subscription_logic(mock_db, 999, 1)

    @patch('app.services.subscription.crud')
    def test_unfreeze_subscription_logic_not_frozen(self, mock_crud, mock_db, mock_student_subscription_model):
        service = SubscriptionService(mock_db)
        mock_crud.get_student_subscription.return_value = mock_student_subscription_model # Not frozen
        
        with pytest.raises(SubscriptionNotFrozen, match="Subscription is not frozen"):
            service._unfreeze_subscription_logic(mock_db, 1, 1)

    @patch('app.services.subscription.crud')
    def test_unfreeze_subscription_logic_missing_dates(self, mock_crud, mock_db, mock_student_subscription_model):
        service = SubscriptionService(mock_db)
        mock_student_subscription_model.freeze_start_date = datetime.now(timezone.utc) # One date present
        mock_student_subscription_model.freeze_end_date = None # One date missing
        mock_crud.get_student_subscription.return_value = mock_student_subscription_model
        
        with pytest.raises(SubscriptionError, match="Frozen dates are missing unexpectedly"):
            service._unfreeze_subscription_logic(mock_db, 1, 1)

    @patch('app.services.subscription.crud')
    @patch('app.services.subscription.student_crud')
    @patch('app.services.financial.FinancialService') # Patch the class directly
    def test_process_auto_renewals_logic_success(
        self, MockFinancialService, mock_student_crud, mock_crud, mock_db,
        mock_student_model, mock_subscription_model, mock_student_subscription_model
    ):
        service = SubscriptionService(mock_db)
        # Ensure financial_service is a mock instance
        service.financial_service = MockFinancialService.return_value
        
        # Mock an expiring student subscription
        expiring_student_sub = Mock(spec=StudentSubscription)
        expiring_student_sub.id = 100
        expiring_student_sub.student_id = mock_student_model.id
        expiring_student_sub.subscription_id = mock_subscription_model.id
        expiring_student_sub.end_date = datetime.now(timezone.utc) - timedelta(days=1) # Ended yesterday
        
        mock_crud.get_today_auto_renewal_subscriptions.return_value = [expiring_student_sub]
        mock_student_crud.get_student_by_id.return_value = mock_student_model
        mock_crud.get_subscription_by_id.return_value = mock_subscription_model
        mock_crud.create_student_subscription.return_value = mock_student_subscription_model # New subscription
        mock_crud.transfer_sessions.return_value = 0 # No sessions transferred for simplicity
        service.financial_service.create_standalone_invoice.return_value = Mock()
        mock_crud.update_subscription_auto_renewal_invoice.return_value = None

        result = service._process_auto_renewals_logic(mock_db)

        mock_crud.get_today_auto_renewal_subscriptions.assert_called_once_with(mock_db)
        mock_student_crud.get_student_by_id.assert_called_once_with(mock_db, mock_student_model.id)
        mock_crud.get_subscription_by_id.assert_called_once_with(mock_db, mock_subscription_model.id)
        mock_crud.create_student_subscription.assert_called_once()
        mock_crud.transfer_sessions.assert_called_once()
        service.financial_service.create_standalone_invoice.assert_called_once()
        mock_crud.update_subscription_auto_renewal_invoice.assert_called_once()
        assert result == [mock_student_subscription_model]

    @patch('app.services.subscription.crud')
    @patch('app.services.subscription.student_crud')
    def test_process_auto_renewals_logic_skip_inactive_student(
        self, mock_student_crud, mock_crud, mock_db, mock_student_model
    ):
        service = SubscriptionService(mock_db)
        expiring_student_sub = Mock(spec=StudentSubscription)
        expiring_student_sub.id = mock_student_model.id
        expiring_student_sub.student_id = mock_student_model.id
        expiring_student_sub.subscription_id = 1
        expiring_student_sub.end_date = datetime.now(timezone.utc) - timedelta(days=1)
        
        mock_crud.get_today_auto_renewal_subscriptions.return_value = [expiring_student_sub]
        mock_student_model.is_active = False # Inactive student
        mock_student_crud.get_student_by_id.return_value = mock_student_model

        result = service._process_auto_renewals_logic(mock_db)

        mock_student_crud.get_student_by_id.assert_called_once()
        mock_crud.create_student_subscription.assert_not_called()
        assert result == []

    @patch('app.services.subscription.crud')
    @patch('app.services.subscription.student_crud')
    def test_process_auto_renewals_logic_skip_inactive_subscription_template(
        self, mock_student_crud, mock_crud, mock_db, mock_student_model, mock_subscription_model
    ):
        service = SubscriptionService(mock_db)
        expiring_student_sub = Mock(spec=StudentSubscription)
        expiring_student_sub.id = mock_student_model.id
        expiring_student_sub.student_id = mock_student_model.id
        expiring_student_sub.subscription_id = mock_subscription_model.id
        expiring_student_sub.end_date = datetime.now(timezone.utc) - timedelta(days=1)
        
        mock_crud.get_today_auto_renewal_subscriptions.return_value = [expiring_student_sub]
        mock_student_crud.get_student_by_id.return_value = mock_student_model
        mock_subscription_model.is_active = False # Inactive template
        mock_crud.get_subscription_by_id.return_value = mock_subscription_model

        result = service._process_auto_renewals_logic(mock_db)

        mock_crud.get_subscription_by_id.assert_called_once()
        mock_crud.create_student_subscription.assert_not_called()
        assert result == []

    @patch('app.services.subscription.crud')
    def test_auto_unfreeze_expired_subscriptions_logic_success(self, mock_crud, mock_db, mock_frozen_student_subscription_model, mock_student_subscription_model):
        service = SubscriptionService(mock_db)
        mock_crud.get_frozen_subscriptions.return_value = [mock_frozen_student_subscription_model]
        mock_crud.unfreeze_subscription.return_value = mock_student_subscription_model

        result = service._auto_unfreeze_expired_subscriptions_logic(mock_db)

        mock_crud.get_frozen_subscriptions.assert_called_once_with(mock_db)
        mock_crud.unfreeze_subscription.assert_called_once_with(mock_db, mock_frozen_student_subscription_model.id)
        assert result == [mock_student_subscription_model]

    @patch('app.services.subscription.crud')
    def test_auto_unfreeze_expired_subscriptions_logic_no_frozen(self, mock_crud, mock_db):
        service = SubscriptionService(mock_db)
        mock_crud.get_frozen_subscriptions.return_value = []

        result = service._auto_unfreeze_expired_subscriptions_logic(mock_db)

        mock_crud.get_frozen_subscriptions.assert_called_once_with(mock_db)
        mock_crud.unfreeze_subscription.assert_not_called()
        assert result == []

    @patch('app.services.subscription.crud')
    def test_auto_unfreeze_expired_subscriptions_logic_error_in_loop(self, mock_crud, mock_db, mock_frozen_student_subscription_model):
        service = SubscriptionService(mock_db)
        mock_crud.get_frozen_subscriptions.return_value = [mock_frozen_student_subscription_model]
        mock_crud.unfreeze_subscription.side_effect = Exception("DB Error")

        result = service._auto_unfreeze_expired_subscriptions_logic(mock_db)

        mock_crud.get_frozen_subscriptions.assert_called_once_with(mock_db)
        mock_crud.unfreeze_subscription.assert_called_once_with(mock_db, mock_frozen_student_subscription_model.id)
        # The error is caught and logged, but the loop continues, and no subscription is returned for this one
        assert result == []