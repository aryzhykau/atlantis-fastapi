import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import Invoice, InvoiceStatus, InvoiceType, User, Student, UserRole
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate
from app.crud import invoice as crud_invoice

# Assuming db_session fixture is available from conftest.py
# and provides a clean session for each test.

@pytest.fixture
def create_test_client(db_session: Session):
    client_id_counter = 0
    def _create_client():
        nonlocal client_id_counter
        client_id_counter += 1
        client = User(first_name=f"Test", last_name=f"Client {client_id_counter}", email=f"client{client_id_counter}@example.com", phone=f"123456789{client_id_counter}", role=UserRole.CLIENT, date_of_birth=datetime(2000, 1, 1).date())
        db_session.add(client)
        db_session.commit()
        db_session.refresh(client)
        return client
    return _create_client

@pytest.fixture
def create_test_student(db_session: Session):
    student_id_counter = 0
    def _create_student():
        nonlocal student_id_counter
        student_id_counter += 1
        # client_id is a foreign key, so we need to provide a dummy one
        client = User(first_name=f"Test", last_name=f"Client_for_Student {student_id_counter}", email=f"client_student{student_id_counter}@example.com", phone=f"987654321{student_id_counter}", role=UserRole.CLIENT, date_of_birth=datetime(2000, 1, 1).date())
        db_session.add(client)
        db_session.commit()
        db_session.refresh(client)
        student = Student(first_name=f"Test", last_name=f"Student {student_id_counter}", date_of_birth=datetime(2000, 1, 1).date(), client_id=client.id)
        db_session.add(student)
        db_session.commit()
        db_session.refresh(student)
        return student
    return _create_student

@pytest.fixture
def create_test_invoice(db_session: Session, create_test_client, create_test_student):
    invoice_id_counter = 0
    def _create_invoice(
        client_obj: User = None,
        student_obj: Student = None,
        amount: float = 100.0,
        status: InvoiceStatus = InvoiceStatus.UNPAID,
        invoice_type: InvoiceType = InvoiceType.TRAINING,
        description: str = "Test Invoice",
        training_id: int = None,
        subscription_id: int = None,
        student_subscription_id: int = None,
        is_auto_renewal: bool = False,
        created_at: datetime = None,
        paid_at: datetime = None,
        cancelled_at: datetime = None,
    ):
        nonlocal invoice_id_counter
        invoice_id_counter += 1

        if client_obj is None:
            client_obj = create_test_client()
        if student_obj is None:
            student_obj = create_test_student()

        invoice_data = InvoiceCreate(
            client_id=client_obj.id,
            student_id=student_obj.id,
            training_id=training_id,
            subscription_id=subscription_id,
            student_subscription_id=student_subscription_id,
            type=invoice_type,
            amount=amount,
            description=description,
            status=status,
            is_auto_renewal=is_auto_renewal,
        )
        invoice = crud_invoice.create_invoice(db_session, invoice_data)
        
        if created_at:
            invoice.created_at = created_at
        if paid_at:
            invoice.paid_at = paid_at
        if cancelled_at:
            invoice.cancelled_at = cancelled_at
        db_session.add(invoice)
        db_session.commit()
        db_session.refresh(invoice)
        return invoice
    return _create_invoice

class TestInvoiceCRUD:
    def test_get_invoice(self, db_session: Session, create_test_invoice):
        invoice = create_test_invoice()
        retrieved_invoice = crud_invoice.get_invoice(db_session, invoice.id)
        assert retrieved_invoice is not None
        assert retrieved_invoice.id == invoice.id

        non_existent_invoice = crud_invoice.get_invoice(db_session, 999)
        assert non_existent_invoice is None

    def test_get_invoices(self, db_session: Session, create_test_invoice, create_test_client, create_test_student):
        client1 = create_test_client()
        client2 = create_test_client()
        student1 = create_test_student()
        student2 = create_test_student()

        invoice1 = create_test_invoice(client_obj=client1, student_obj=student1, amount=100.0, status=InvoiceStatus.UNPAID, created_at=datetime(2025, 7, 15, 9, 0, 0, tzinfo=timezone.utc))
        invoice2 = create_test_invoice(client_obj=client1, student_obj=student2, amount=150.0, status=InvoiceStatus.PAID, created_at=datetime(2025, 7, 15, 10, 0, 0, tzinfo=timezone.utc))
        invoice3 = create_test_invoice(client_obj=client2, student_obj=student1, amount=200.0, status=InvoiceStatus.CANCELLED, created_at=datetime(2025, 7, 15, 11, 0, 0, tzinfo=timezone.utc))

        # Test without filters
        invoices = crud_invoice.get_invoices(db_session)
        assert len(invoices) == 3
        assert invoice1 in invoices and invoice2 in invoices and invoice3 in invoices

        # Test filter by client_id
        client1_invoices = crud_invoice.get_invoices(db_session, client_id=client1.id)
        assert len(client1_invoices) == 2
        assert invoice1 in client1_invoices and invoice2 in client1_invoices

        # Test filter by student_id
        student1_invoices = crud_invoice.get_invoices(db_session, student_id=student1.id)
        assert len(student1_invoices) == 2
        assert invoice1 in student1_invoices and invoice3 in student1_invoices

        # Test filter by status
        unpaid_invoices = crud_invoice.get_invoices(db_session, status=InvoiceStatus.UNPAID)
        assert len(unpaid_invoices) == 1
        assert invoice1 in unpaid_invoices

        # Test filter by invoice_type (all are TRAINING by default in fixture)
        training_invoices = crud_invoice.get_invoices(db_session, invoice_type=InvoiceType.TRAINING)
        assert len(training_invoices) == 3

        # Test pagination
        all_invoices_sorted = crud_invoice.get_invoices(db_session)
        assert all_invoices_sorted[0].id == invoice3.id # Newest
        assert all_invoices_sorted[1].id == invoice2.id
        assert all_invoices_sorted[2].id == invoice1.id

        paginated_invoices_skip1_limit1 = crud_invoice.get_invoices(db_session, skip=1, limit=1)
        assert len(paginated_invoices_skip1_limit1) == 1
        assert paginated_invoices_skip1_limit1[0].id == invoice2.id

        # Test combining multiple filters
        client1_unpaid_invoices = crud_invoice.get_invoices(db_session, client_id=client1.id, status=InvoiceStatus.UNPAID)
        assert len(client1_unpaid_invoices) == 1
        assert invoice1 in client1_unpaid_invoices

    def test_get_student_invoices(self, db_session: Session, create_test_invoice, create_test_client, create_test_student):
        client1 = create_test_client()
        client2 = create_test_client()
        student1 = create_test_student()
        student2 = create_test_student()

        invoice1 = create_test_invoice(client_obj=client1, student_obj=student1, amount=100.0, status=InvoiceStatus.UNPAID)
        invoice2 = create_test_invoice(client_obj=client2, student_obj=student1, amount=150.0, status=InvoiceStatus.PAID)
        invoice3 = create_test_invoice(client_obj=client1, student_obj=student2, amount=200.0, status=InvoiceStatus.UNPAID)

        student1_invoices = crud_invoice.get_student_invoices(db_session, student_id=student1.id)
        assert len(student1_invoices) == 2
        assert invoice1 in student1_invoices and invoice2 in student1_invoices

        student1_paid_invoices = crud_invoice.get_student_invoices(db_session, student_id=student1.id, status=InvoiceStatus.PAID)
        assert len(student1_paid_invoices) == 1
        assert invoice2 in student1_paid_invoices

        no_invoices = crud_invoice.get_student_invoices(db_session, student_id=999)
        assert len(no_invoices) == 0

    def test_get_client_invoices(self, db_session: Session, create_test_invoice, create_test_client, create_test_student):
        client1 = create_test_client()
        client2 = create_test_client()
        student1 = create_test_student()
        student2 = create_test_student()

        invoice1 = create_test_invoice(client_obj=client1, student_obj=student1, amount=100.0, status=InvoiceStatus.UNPAID)
        invoice2 = create_test_invoice(client_obj=client1, student_obj=student2, amount=150.0, status=InvoiceStatus.PAID)
        invoice3 = create_test_invoice(client_obj=client2, student_obj=student1, amount=200.0, status=InvoiceStatus.UNPAID)

        client1_invoices = crud_invoice.get_client_invoices(db_session, client_id=client1.id)
        assert len(client1_invoices) == 2
        assert invoice1 in client1_invoices and invoice2 in client1_invoices

        client1_unpaid_invoices = crud_invoice.get_client_invoices(db_session, client_id=client1.id, status=InvoiceStatus.UNPAID)
        assert len(client1_unpaid_invoices) == 1
        assert invoice1 in client1_unpaid_invoices

        no_invoices = crud_invoice.get_client_invoices(db_session, client_id=999)
        assert len(no_invoices) == 0

    def test_get_training_invoice(self, db_session: Session, create_test_invoice, create_test_client, create_test_student):
        client = create_test_client()
        student1 = create_test_student()
        student2 = create_test_student()

        invoice1 = create_test_invoice(client_obj=client, student_obj=student1, amount=100.0, training_id=1)
        invoice2 = create_test_invoice(client_obj=client, student_obj=student1, amount=100.0, training_id=2, status=InvoiceStatus.CANCELLED)
        invoice3 = create_test_invoice(client_obj=client, student_obj=student2, amount=100.0, training_id=1) # Different student

        retrieved_invoice = crud_invoice.get_training_invoice(db_session, training_id=1, student_id=student1.id)
        assert retrieved_invoice is not None
        assert retrieved_invoice.id == invoice1.id

        # Should not return cancelled invoice
        cancelled_invoice = crud_invoice.get_training_invoice(db_session, training_id=2, student_id=student1.id)
        assert cancelled_invoice is None

        # Non-existent training/student combo
        non_existent = crud_invoice.get_training_invoice(db_session, training_id=999, student_id=student1.id)
        assert non_existent is None

    def test_get_subscription_invoice(self, db_session: Session, create_test_invoice, create_test_client, create_test_student):
        client = create_test_client()
        student1 = create_test_student()
        student2 = create_test_student()

        invoice1 = create_test_invoice(client_obj=client, student_obj=student1, amount=100.0, subscription_id=1)
        invoice2 = create_test_invoice(client_obj=client, student_obj=student1, amount=100.0, subscription_id=2, status=InvoiceStatus.CANCELLED)
        invoice3 = create_test_invoice(client_obj=client, student_obj=student2, amount=100.0, subscription_id=1) # Different student

        retrieved_invoice = crud_invoice.get_subscription_invoice(db_session, subscription_id=1, student_id=student1.id)
        assert retrieved_invoice is not None
        assert retrieved_invoice.id == invoice1.id

        # Should not return cancelled invoice
        cancelled_invoice = crud_invoice.get_subscription_invoice(db_session, subscription_id=2, student_id=student1.id)
        assert cancelled_invoice is None

        # Non-existent subscription/student combo
        non_existent = crud_invoice.get_subscription_invoice(db_session, subscription_id=999, student_id=student1.id)
        assert non_existent is None

    def test_create_invoice(self, db_session: Session, create_test_client, create_test_student):
        client = create_test_client()
        student = create_test_student()
        invoice_data = InvoiceCreate(
            client_id=client.id,
            student_id=student.id,
            training_id=1,
            subscription_id=None,
            student_subscription_id=None,
            type=InvoiceType.TRAINING,
            amount=50.0,
            description="New Training Invoice",
            status=InvoiceStatus.UNPAID,
            is_auto_renewal=False,
        )
        new_invoice = crud_invoice.create_invoice(db_session, invoice_data)
        db_session.commit() # Commit to make it persistent for retrieval

        assert new_invoice.id is not None
        assert new_invoice.client_id == client.id
        assert new_invoice.student_id == student.id
        assert new_invoice.amount == 50.0
        assert new_invoice.status == InvoiceStatus.UNPAID
        assert new_invoice.description == "New Training Invoice"
        assert new_invoice.created_at is not None

        retrieved_invoice = crud_invoice.get_invoice(db_session, new_invoice.id)
        assert retrieved_invoice.amount == 50.0

    def test_update_invoice(self, db_session: Session, create_test_invoice):
        invoice = create_test_invoice()
        update_data = InvoiceUpdate(amount=120.0, description="Updated Description")
        updated_invoice = crud_invoice.update_invoice(db_session, invoice.id, update_data)
        db_session.commit() # Commit to make it persistent for retrieval

        assert updated_invoice is not None
        assert updated_invoice.id == invoice.id
        assert updated_invoice.amount == 120.0
        assert updated_invoice.description == "Updated Description"

        retrieved_invoice = crud_invoice.get_invoice(db_session, invoice.id)
        assert retrieved_invoice.amount == 120.0
        assert retrieved_invoice.description == "Updated Description"

        # Test updating non-existent invoice
        non_existent_update = crud_invoice.update_invoice(db_session, 999, update_data)
        assert non_existent_update is None

    def test_cancel_invoice(self, db_session: Session, create_test_invoice):
        invoice = create_test_invoice()
        cancelled_invoice = crud_invoice.cancel_invoice(db_session, invoice.id, cancelled_by_id=1)
        db_session.commit()

        assert cancelled_invoice is not None
        assert cancelled_invoice.id == invoice.id
        assert cancelled_invoice.status == InvoiceStatus.CANCELLED
        assert cancelled_invoice.cancelled_at is not None
        # Compare timestamps with a small tolerance
        # Ensure cancelled_at from DB is timezone-aware for comparison
        retrieved_cancelled_at = cancelled_invoice.cancelled_at
        if retrieved_cancelled_at.tzinfo is None:
            retrieved_cancelled_at = retrieved_cancelled_at.replace(tzinfo=timezone.utc)
        assert abs((datetime.now(timezone.utc) - retrieved_cancelled_at).total_seconds()) < 1

        retrieved_invoice = crud_invoice.get_invoice(db_session, invoice.id)
        assert retrieved_invoice.status == InvoiceStatus.CANCELLED
        # Ensure retrieved_invoice.cancelled_at is timezone-aware for comparison
        retrieved_cancelled_at_from_get = retrieved_invoice.cancelled_at
        if retrieved_cancelled_at_from_get and retrieved_cancelled_at_from_get.tzinfo is None:
            retrieved_cancelled_at_from_get = retrieved_cancelled_at_from_get.replace(tzinfo=timezone.utc)
        assert abs((datetime.now(timezone.utc) - retrieved_cancelled_at_from_get).total_seconds()) < 1

        # Test cancelling non-existent invoice
        non_existent_cancel = crud_invoice.cancel_invoice(db_session, 999, cancelled_by_id=1)
        assert non_existent_cancel is None

    def test_mark_invoice_as_paid(self, db_session: Session, create_test_invoice):
        invoice = create_test_invoice()
        paid_at_time = datetime(2025, 7, 14, 10, 0, 0, tzinfo=timezone.utc)
        paid_invoice = crud_invoice.mark_invoice_as_paid(db_session, invoice.id, paid_at=paid_at_time)
        db_session.commit()

        assert paid_invoice is not None
        assert paid_invoice.id == invoice.id
        assert paid_invoice.status == InvoiceStatus.PAID
        # Compare timestamps with a small tolerance
        # Ensure paid_at from DB is timezone-aware for comparison
        retrieved_paid_at = paid_invoice.paid_at
        if retrieved_paid_at and retrieved_paid_at.tzinfo is None:
            retrieved_paid_at = retrieved_paid_at.replace(tzinfo=timezone.utc)
        assert abs((retrieved_paid_at - paid_at_time).total_seconds()) < 1

        retrieved_invoice = crud_invoice.get_invoice(db_session, invoice.id)
        assert retrieved_invoice.status == InvoiceStatus.PAID
        # Ensure retrieved_invoice.paid_at is timezone-aware for comparison
        retrieved_paid_at_from_get = retrieved_invoice.paid_at
        if retrieved_paid_at_from_get and retrieved_paid_at_from_get.tzinfo is None:
            retrieved_paid_at_from_get = retrieved_paid_at_from_get.replace(tzinfo=timezone.utc)
        assert abs((retrieved_paid_at_from_get - paid_at_time).total_seconds()) < 1

        # Test without specific paid_at time
        invoice2 = create_test_invoice()
        paid_invoice2 = crud_invoice.mark_invoice_as_paid(db_session, invoice2.id)
        db_session.commit()
        assert paid_invoice2.status == InvoiceStatus.PAID
        assert paid_invoice2.paid_at is not None
        # Ensure paid_invoice2.paid_at is timezone-aware for comparison
        retrieved_paid_at_invoice2 = paid_invoice2.paid_at
        if retrieved_paid_at_invoice2 and retrieved_paid_at_invoice2.tzinfo is None:
            retrieved_paid_at_invoice2 = retrieved_paid_at_invoice2.replace(tzinfo=timezone.utc)
        assert abs((datetime.now(timezone.utc) - retrieved_paid_at_invoice2).total_seconds()) < 1

        # Test marking non-existent invoice as paid
        non_existent_paid = crud_invoice.mark_invoice_as_paid(db_session, 999)
        assert non_existent_paid is None

    def test_mark_invoice_as_unpaid(self, db_session: Session, create_test_invoice):
        invoice = create_test_invoice(status=InvoiceStatus.PAID, paid_at=datetime.now(timezone.utc))
        unpaid_invoice = crud_invoice.mark_invoice_as_unpaid(db_session, invoice.id)
        db_session.commit()

        assert unpaid_invoice is not None
        assert unpaid_invoice.id == invoice.id
        assert unpaid_invoice.status == InvoiceStatus.UNPAID
        assert unpaid_invoice.paid_at is None

        retrieved_invoice = crud_invoice.get_invoice(db_session, invoice.id)
        assert retrieved_invoice.status == InvoiceStatus.UNPAID
        assert retrieved_invoice.paid_at is None

        # Test marking non-existent invoice as unpaid
        non_existent_unpaid = crud_invoice.mark_invoice_as_unpaid(db_session, 999)
        assert non_existent_unpaid is None

    def test_get_unpaid_invoices(self, db_session: Session, create_test_invoice, create_test_client, create_test_student):
        client1 = create_test_client()
        client2 = create_test_client()
        student1 = create_test_student()
        student2 = create_test_student()

        invoice1 = create_test_invoice(client_obj=client1, student_obj=student1, amount=100.0, status=InvoiceStatus.UNPAID)
        invoice2 = create_test_invoice(client_obj=client1, student_obj=student2, amount=150.0, status=InvoiceStatus.PAID)
        invoice3 = create_test_invoice(client_obj=client2, student_obj=student1, amount=200.0, status=InvoiceStatus.UNPAID)

        unpaid_invoices = crud_invoice.get_unpaid_invoices(db_session)
        assert len(unpaid_invoices) == 2
        assert invoice1 in unpaid_invoices and invoice3 in unpaid_invoices

        client1_unpaid = crud_invoice.get_unpaid_invoices(db_session, client_id=client1.id)
        assert len(client1_unpaid) == 1
        assert invoice1 in client1_unpaid

        student1_unpaid = crud_invoice.get_unpaid_invoices(db_session, student_id=student1.id)
        assert len(student1_unpaid) == 2
        assert invoice1 in student1_unpaid and invoice3 in student1_unpaid

    def test_get_paid_invoices(self, db_session: Session, create_test_invoice, create_test_client, create_test_student):
        client1 = create_test_client()
        client2 = create_test_client()
        student1 = create_test_student()
        student2 = create_test_student()

        invoice1 = create_test_invoice(client_obj=client1, student_obj=student1, amount=100.0, status=InvoiceStatus.PAID, paid_at=datetime(2025, 6, 1, tzinfo=timezone.utc))
        invoice2 = create_test_invoice(client_obj=client1, student_obj=student2, amount=150.0, status=InvoiceStatus.UNPAID)
        invoice3 = create_test_invoice(client_obj=client2, student_obj=student1, amount=200.0, status=InvoiceStatus.PAID, paid_at=datetime(2025, 6, 15, tzinfo=timezone.utc))
        invoice4 = create_test_invoice(client_obj=client1, student_obj=student1, amount=50.0, status=InvoiceStatus.PAID, paid_at=datetime(2025, 7, 1, tzinfo=timezone.utc))

        paid_invoices = crud_invoice.get_paid_invoices(db_session)
        assert len(paid_invoices) == 3
        assert invoice4 in paid_invoices and invoice3 in paid_invoices and invoice1 in paid_invoices # Ordered by paid_at DESC

        client1_paid = crud_invoice.get_paid_invoices(db_session, client_id=client1.id)
        assert len(client1_paid) == 2
        assert invoice4 in client1_paid and invoice1 in client1_paid

        student1_paid = crud_invoice.get_paid_invoices(db_session, student_id=student1.id)
        assert len(student1_paid) == 3 # Corrected assertion
        assert invoice4 in student1_paid and invoice3 in student1_paid and invoice1 in student1_paid

        # Test date filters
        start_date = datetime(2025, 6, 10, tzinfo=timezone.utc)
        end_date = datetime(2025, 6, 20, tzinfo=timezone.utc)
        paid_invoices_filtered_date = crud_invoice.get_paid_invoices(db_session, start_date=start_date, end_date=end_date)
        assert len(paid_invoices_filtered_date) == 1
        assert invoice3 in paid_invoices_filtered_date

        # Test combining client_id and date filters
        client1_paid_filtered_date = crud_invoice.get_paid_invoices(db_session, client_id=client1.id, start_date=datetime(2025, 6, 1, tzinfo=timezone.utc), end_date=datetime(2025, 6, 10, tzinfo=timezone.utc))
        assert len(client1_paid_filtered_date) == 1
        assert invoice1 in client1_paid_filtered_date

    def test_get_paid_invoices_by_client(self, db_session: Session, create_test_invoice, create_test_client, create_test_student):
        client1 = create_test_client()
        client2 = create_test_client()
        student1 = create_test_student()
        student2 = create_test_student()

        invoice1 = create_test_invoice(client_obj=client1, student_obj=student1, amount=100.0, status=InvoiceStatus.PAID, paid_at=datetime(2025, 6, 1, tzinfo=timezone.utc))
        invoice2 = create_test_invoice(client_obj=client1, student_obj=student2, amount=150.0, status=InvoiceStatus.UNPAID)
        invoice3 = create_test_invoice(client_obj=client2, student_obj=student1, amount=200.0, status=InvoiceStatus.PAID, paid_at=datetime(2025, 6, 15, tzinfo=timezone.utc))
        invoice4 = create_test_invoice(client_obj=client1, student_obj=student1, amount=50.0, status=InvoiceStatus.PAID, paid_at=datetime(2025, 7, 1, tzinfo=timezone.utc))

        client1_paid = crud_invoice.get_paid_invoices_by_client(db_session, client_id=client1.id)
        assert len(client1_paid) == 2
        assert invoice4 in client1_paid and invoice1 in client1_paid

        # Test date filters
        start_date = datetime(2025, 6, 10, tzinfo=timezone.utc)
        end_date = datetime(2025, 6, 20, tzinfo=timezone.utc)
        client1_paid_filtered_date = crud_invoice.get_paid_invoices_by_client(db_session, client_id=client1.id, start_date=start_date, end_date=end_date)
        assert len(client1_paid_filtered_date) == 0 # No invoices for client 1 in this range

    def test_get_cancelled_invoices(self, db_session: Session, create_test_invoice, create_test_client, create_test_student):
        client1 = create_test_client()
        client2 = create_test_client()
        student1 = create_test_student()
        student2 = create_test_student()

        invoice1 = create_test_invoice(client_obj=client1, student_obj=student1, amount=100.0, status=InvoiceStatus.CANCELLED, cancelled_at=datetime(2025, 6, 1, tzinfo=timezone.utc))
        invoice2 = create_test_invoice(client_obj=client1, student_obj=student2, amount=150.0, status=InvoiceStatus.PAID)
        invoice3 = create_test_invoice(client_obj=client2, student_obj=student1, amount=200.0, status=InvoiceStatus.CANCELLED, cancelled_at=datetime(2025, 6, 15, tzinfo=timezone.utc))

        cancelled_invoices = crud_invoice.get_cancelled_invoices(db_session)
        assert len(cancelled_invoices) == 2
        assert invoice3 in cancelled_invoices and invoice1 in cancelled_invoices # Ordered by cancelled_at DESC

        client1_cancelled = crud_invoice.get_cancelled_invoices(db_session, client_id=client1.id)
        assert len(client1_cancelled) == 1
        assert invoice1 in client1_cancelled

        student1_cancelled = crud_invoice.get_cancelled_invoices(db_session, student_id=student1.id)
        assert len(student1_cancelled) == 2
        assert invoice3 in student1_cancelled and invoice1 in student1_cancelled

    def test_delete_invoice(self, db_session: Session, create_test_invoice):
        invoice = create_test_invoice()
        deleted_invoice = crud_invoice.delete_invoice(db_session, invoice.id)
        db_session.commit()

        assert deleted_invoice is not None
        assert deleted_invoice.id == invoice.id

        retrieved_invoice = crud_invoice.get_invoice(db_session, invoice.id)
        assert retrieved_invoice is None

        # Test deleting non-existent invoice
        non_existent_delete = crud_invoice.delete_invoice(db_session, 999)
        assert non_existent_delete is None

    def test_get_invoice_count(self, db_session: Session, create_test_invoice, create_test_client, create_test_student):
        client1 = create_test_client()
        client2 = create_test_client()
        student1 = create_test_student()
        student2 = create_test_student()

        invoice1 = create_test_invoice(client_obj=client1, student_obj=student1, amount=100.0, status=InvoiceStatus.UNPAID)
        invoice2 = create_test_invoice(client_obj=client1, student_obj=student2, amount=150.0, status=InvoiceStatus.PAID)
        invoice3 = create_test_invoice(client_obj=client2, student_obj=student1, amount=200.0, status=InvoiceStatus.UNPAID)

        total_count = crud_invoice.get_invoice_count(db_session)
        assert total_count == 3

        client1_count = crud_invoice.get_invoice_count(db_session, client_id=client1.id)
        assert client1_count == 2

        student1_count = crud_invoice.get_invoice_count(db_session, student_id=student1.id)
        assert student1_count == 2

        unpaid_count = crud_invoice.get_invoice_count(db_session, status=InvoiceStatus.UNPAID)
        assert unpaid_count == 2

        client1_unpaid_count = crud_invoice.get_invoice_count(db_session, client_id=client1.id, status=InvoiceStatus.UNPAID)
        assert client1_unpaid_count == 1
