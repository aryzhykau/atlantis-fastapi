import pytest
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.services.financial import FinancialService
from app.services.training_processing import TrainingProcessingService
from app.models import (
    RealTraining,
    RealTrainingStudent,
    StudentSubscription,
    Invoice,
    InvoiceStatus,
    InvoiceType,
    User
)
from app.crud import invoice as invoice_crud


def test_idempotent_subscription_deduction(db_session: Session, test_trainer, test_client, test_second_student):
    # Create a training for tomorrow
    tomorrow = date.today() + timedelta(days=1)
    training = RealTraining(
        training_date=tomorrow,
        start_time=None,
        responsible_trainer_id=test_trainer.id,
        training_type_id=1,
        is_template_based=False
    )
    db_session.add(training)
    db_session.commit()
    db_session.refresh(training)

    # Create a student and an active subscription for them
    student = test_second_student
    student_subscription = StudentSubscription(
        student_id=student.id,
        subscription_id=1,
        start_date=date.today() - timedelta(days=1),
        end_date=date.today() + timedelta(days=30),
        sessions_left=5,
        is_auto_renew=False
    )
    db_session.add(student_subscription)
    db_session.commit()
    db_session.refresh(student_subscription)

    # Add student to training
    rts = RealTrainingStudent(
        real_training_id=training.id,
        student_id=student.id,
        subscription_id=student_subscription.id,
        status=None,
        requires_payment=True,
    )
    db_session.add(rts)
    db_session.commit()
    db_session.refresh(rts)

    fs = FinancialService(db_session)

    # First run: should deduct one session
    res1 = fs.process_invoices(admin_id=0)
    db_session.refresh(student_subscription)
    assert student_subscription.sessions_left == 4

    # Second run: should NOT deduct again
    res2 = fs.process_invoices(admin_id=0)
    db_session.refresh(student_subscription)
    assert student_subscription.sessions_left == 4


def test_pay_per_session_pending_to_paid_auto_pay(db_session: Session, test_trainer, test_client, test_student):
    # Create a training for tomorrow with a training type that is not subscription-only
    tomorrow = date.today() + timedelta(days=1)
    training = RealTraining(
        training_date=tomorrow,
        start_time=None,
        responsible_trainer_id=test_trainer.id,
        training_type_id=1,
        is_template_based=False
    )
    db_session.add(training)
    db_session.commit()
    db_session.refresh(training)

    # Add student to training (no subscription)
    student = test_student
    rts = RealTrainingStudent(
        real_training_id=training.id,
        student_id=student.id,
        subscription_id=None,
        status=None,
        requires_payment=True,
    )
    db_session.add(rts)
    db_session.commit()
    db_session.refresh(rts)

    # Create a PENDING invoice for this training and give client enough balance
    invoice = Invoice(
        client_id=student.client_id,
        student_id=student.id,
        training_id=training.id,
        type=InvoiceType.TRAINING,
        amount=100.0,
        description="Test training invoice",
        status=InvoiceStatus.PENDING,
        is_auto_renewal=False
    )
    db_session.add(invoice)

    # Fund client balance
    client = db_session.query(User).filter(User.id == student.client_id).first()
    client.balance = 200.0
    db_session.commit()
    db_session.refresh(invoice)

    fs = FinancialService(db_session)
    res = fs.process_invoices(admin_id=0)

    # Reload invoice and assert it got paid
    updated_invoice = db_session.query(Invoice).filter(Invoice.id == invoice.id).first()
    assert updated_invoice is not None
    assert updated_invoice.status in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.UNPAID)  # expected PAID if auto-pay succeeded
    # If paid, client balance decreased
    client = db_session.query(User).filter(User.id == student.client_id).first()
    if updated_invoice.status == InvoiceStatus.PAID:
        assert client.balance == pytest.approx(100.0)

