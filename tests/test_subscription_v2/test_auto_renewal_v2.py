"""Тесты: process_auto_renewals_v2 (BE-20)."""
from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models import StudentSubscription
from app.models.invoice import Invoice, InvoiceStatus, InvoiceType
from app.services.subscription_v2 import process_auto_renewals_v2
from tests.test_subscription_v2.conftest import make_student_sub_v2

# «Сегодня» = последний день марта (auto-renewal день)
LAST_DAY_MARCH = date(2026, 3, 31)
FIRST_APRIL    = date(2026, 4, 1)
LAST_APRIL     = date(2026, 4, 30)
DUE_APRIL      = date(2026, 4, 7)


def _run(db_session):
    """Запускает auto-renewal с today=2026-03-31 (последний день месяца)."""
    with patch("app.services.subscription_v2.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 3, 31, 2, 0, 0, tzinfo=timezone.utc)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        return process_auto_renewals_v2(db_session)


class TestAutoRenewalV2:

    def test_creates_new_subscription_for_next_month(
        self, db_session: Session, student_rich, sub_v2_template, client_with_balance
    ):
        """Должен создать новый pending-абонемент на апрель."""
        old_sub = make_student_sub_v2(
            db_session, student_rich.id, sub_v2_template,
            start_date=date(2026, 3, 1),
            end_date=LAST_DAY_MARCH,
            is_auto_renew=True,
        )

        result = _run(db_session)

        assert result["processed"] >= 1
        new_sub = (
            db_session.query(StudentSubscription)
            .filter(
                StudentSubscription.student_id == student_rich.id,
                StudentSubscription.id != old_sub.id,
            )
            .first()
        )
        assert new_sub is not None
        assert new_sub.start_date.date() == FIRST_APRIL
        assert new_sub.end_date.date() == LAST_APRIL
        assert new_sub.is_prorated is False
        assert new_sub.payment_due_date == DUE_APRIL

    def test_creates_pending_invoice_for_new_sub(
        self, db_session: Session, student_poor, sub_v2_template, client_no_balance
    ):
        """Инвойс создаётся со статусом PENDING (если баланс = 0)."""
        make_student_sub_v2(
            db_session, student_poor.id, sub_v2_template,
            start_date=date(2026, 3, 1),
            end_date=LAST_DAY_MARCH,
            is_auto_renew=True,
        )

        _run(db_session)

        new_sub = (
            db_session.query(StudentSubscription)
            .filter(
                StudentSubscription.student_id == student_poor.id,
                StudentSubscription.start_date >= datetime(2026, 4, 1, tzinfo=timezone.utc),
            )
            .first()
        )
        assert new_sub is not None
        invoice = db_session.query(Invoice).filter(
            Invoice.student_subscription_id == new_sub.id
        ).first()
        assert invoice is not None
        assert invoice.status == InvoiceStatus.PENDING
        assert invoice.due_date == DUE_APRIL
        assert invoice.is_auto_renewal is True

    def test_idempotency_does_not_double_renew(
        self, db_session: Session, student_rich, sub_v2_template, client_with_balance
    ):
        """Повторный запуск не создаёт второй абонемент (auto_renewal_invoice_id IS NOT NULL)."""
        old_sub = make_student_sub_v2(
            db_session, student_rich.id, sub_v2_template,
            start_date=date(2026, 3, 1),
            end_date=LAST_DAY_MARCH,
            is_auto_renew=True,
        )

        # Первый запуск
        _run(db_session)

        db_session.refresh(old_sub)
        assert old_sub.auto_renewal_invoice_id is not None

        count_before = db_session.query(StudentSubscription).filter(
            StudentSubscription.student_id == student_rich.id
        ).count()

        # Повторный запуск
        _run(db_session)

        count_after = db_session.query(StudentSubscription).filter(
            StudentSubscription.student_id == student_rich.id
        ).count()
        assert count_after == count_before  # новых не создалось

    def test_no_renewal_for_is_auto_renew_false(
        self, db_session: Session, student_rich, sub_v2_template, client_with_balance
    ):
        """Абонемент без is_auto_renew=True не продлевается."""
        make_student_sub_v2(
            db_session, student_rich.id, sub_v2_template,
            start_date=date(2026, 3, 1),
            end_date=LAST_DAY_MARCH,
            is_auto_renew=False,
        )

        result = _run(db_session)

        assert result["processed"] == 0

    def test_no_renewal_if_end_date_not_today(
        self, db_session: Session, student_rich, sub_v2_template, client_with_balance
    ):
        """Абонемент с end_date не в списке кандидатов (завтра заканчивается)."""
        make_student_sub_v2(
            db_session, student_rich.id, sub_v2_template,
            start_date=date(2026, 3, 2),
            end_date=date(2026, 4, 30),  # не сегодня
            is_auto_renew=True,
        )

        result = _run(db_session)

        assert result["processed"] == 0

    def test_auto_pay_on_renewal_with_balance(
        self, db_session: Session, student_rich, sub_v2_template, client_with_balance
    ):
        """При достаточном балансе инвойс auto-renewal оплачивается сразу."""
        make_student_sub_v2(
            db_session, student_rich.id, sub_v2_template,
            start_date=date(2026, 3, 1),
            end_date=LAST_DAY_MARCH,
            is_auto_renew=True,
        )

        _run(db_session)

        new_sub = (
            db_session.query(StudentSubscription)
            .filter(
                StudentSubscription.student_id == student_rich.id,
                StudentSubscription.start_date >= datetime(2026, 4, 1, tzinfo=timezone.utc),
            )
            .first()
        )
        invoice = db_session.query(Invoice).filter(
            Invoice.student_subscription_id == new_sub.id
        ).first()
        # Баланс 10000 >= 5000 → PAID
        assert invoice.status == InvoiceStatus.PAID
