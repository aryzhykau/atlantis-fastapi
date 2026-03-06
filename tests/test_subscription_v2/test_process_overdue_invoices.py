"""Тесты: process_overdue_invoices_v2 (BE-20)."""
from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus, InvoiceType
from app.services.subscription_v2 import process_overdue_invoices_v2


def make_invoice(db_session, client_id, student_id, status, due_date, itype=InvoiceType.SUBSCRIPTION):
    inv = Invoice(
        client_id=client_id,
        student_id=student_id,
        amount=5000.0,
        description="test",
        type=itype,
        status=status,
        due_date=due_date,
    )
    db_session.add(inv)
    db_session.commit()
    db_session.refresh(inv)
    return inv


PAST_DATE   = date(2026, 2, 7)   # просрочен
FUTURE_DATE = date(2026, 3, 7)   # ещё в будущем
TODAY       = date(2026, 3, 1)


class TestProcessOverdueInvoicesV2:

    def _run(self, db_session):
        """Запускает функцию с замоканной датой today=2026-03-01."""
        with patch("app.services.subscription_v2.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 1, 8, 0, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            return process_overdue_invoices_v2(db_session)

    def test_pending_overdue_no_balance_becomes_unpaid(
        self, db_session: Session, student_poor, client_no_balance
    ):
        inv = make_invoice(db_session, client_no_balance.id, student_poor.id, InvoiceStatus.PENDING, PAST_DATE)

        result = self._run(db_session)

        db_session.refresh(inv)
        assert inv.status == InvoiceStatus.UNPAID
        assert result["unpaid"] >= 1

    def test_pending_overdue_with_balance_becomes_paid(
        self, db_session: Session, student_rich, client_with_balance
    ):
        initial_balance = client_with_balance.balance
        inv = make_invoice(db_session, client_with_balance.id, student_rich.id, InvoiceStatus.PENDING, PAST_DATE)

        result = self._run(db_session)

        db_session.refresh(inv)
        assert inv.status == InvoiceStatus.PAID
        assert result["paid"] >= 1
        db_session.refresh(client_with_balance)
        assert client_with_balance.balance == initial_balance - inv.amount

    def test_pending_future_due_date_not_touched(
        self, db_session: Session, student_poor, client_no_balance
    ):
        inv = make_invoice(db_session, client_no_balance.id, student_poor.id, InvoiceStatus.PENDING, FUTURE_DATE)

        self._run(db_session)

        db_session.refresh(inv)
        # due_date ещё в будущем → статус не меняется
        assert inv.status == InvoiceStatus.PENDING

    def test_unpaid_invoice_not_touched(
        self, db_session: Session, student_poor, client_no_balance
    ):
        inv = make_invoice(db_session, client_no_balance.id, student_poor.id, InvoiceStatus.UNPAID, PAST_DATE)

        self._run(db_session)

        db_session.refresh(inv)
        assert inv.status == InvoiceStatus.UNPAID

    def test_training_type_invoice_not_touched(
        self, db_session: Session, student_poor, client_no_balance
    ):
        """Инвойсы типа TRAINING не трогаются (только SUBSCRIPTION)."""
        inv = make_invoice(
            db_session, client_no_balance.id, student_poor.id,
            InvoiceStatus.PENDING, PAST_DATE, itype=InvoiceType.TRAINING
        )

        self._run(db_session)

        db_session.refresh(inv)
        assert inv.status == InvoiceStatus.PENDING

    def test_multiple_invoices_mixed(
        self, db_session: Session,
        student_rich, client_with_balance,
        student_poor, client_no_balance,
    ):
        """Несколько инвойсов, часть оплачивается, часть → UNPAID."""
        inv_pay = make_invoice(db_session, client_with_balance.id, student_rich.id, InvoiceStatus.PENDING, PAST_DATE)
        inv_fail = make_invoice(db_session, client_no_balance.id, student_poor.id, InvoiceStatus.PENDING, PAST_DATE)

        result = self._run(db_session)

        db_session.refresh(inv_pay)
        db_session.refresh(inv_fail)
        assert inv_pay.status == InvoiceStatus.PAID
        assert inv_fail.status == InvoiceStatus.UNPAID
        assert result["paid"] >= 1
        assert result["unpaid"] >= 1
