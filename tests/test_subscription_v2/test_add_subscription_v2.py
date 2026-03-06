"""Integration-тесты: add_subscription_to_student_v2 (BE-20)."""
from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models import StudentSubscription
from app.models.invoice import Invoice, InvoiceStatus, InvoiceType
from app.models.student import Student
from app.models.user import User
from app.services.subscription_v2 import (
    add_subscription_to_student_v2,
    _get_month_end_date,
    _get_payment_due_date,
    _get_first_of_next_month,
)


class TestAddSubscriptionV2:

    def test_purchase_on_first_of_month_is_not_prorated(
        self,
        db_session: Session,
        student_rich: Student,
        sub_v2_template,
        client_with_balance: User,
    ):
        """Покупка 1-го числа: полная цена, is_prorated=False."""
        purchase_date = date(2026, 3, 1)

        with patch("app.services.subscription_v2.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            sub = add_subscription_to_student_v2(
                db_session,
                student_id=student_rich.id,
                subscription_id=sub_v2_template.id,
                is_auto_renew=True,
            )

        db_session.refresh(sub)
        assert sub.is_prorated is False
        assert sub.payment_due_date == date(2026, 3, 7)
        assert sub.end_date.date() == date(2026, 3, 31)
        assert sub.is_auto_renew is True

        # Инвойс должен быть создан
        invoice = db_session.query(Invoice).filter(
            Invoice.student_subscription_id == sub.id
        ).first()
        assert invoice is not None
        assert invoice.type == InvoiceType.SUBSCRIPTION
        assert invoice.amount == sub_v2_template.price

    def test_purchase_mid_month_is_prorated(
        self,
        db_session: Session,
        student_rich: Student,
        sub_v2_template,
        client_with_balance: User,
    ):
        """Покупка в середине месяца: is_prorated=True, пропорциональная цена."""
        with patch("app.services.subscription_v2.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 19, 10, 0, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            sub = add_subscription_to_student_v2(
                db_session,
                student_id=student_rich.id,
                subscription_id=sub_v2_template.id,
                is_auto_renew=False,
            )

        db_session.refresh(sub)
        assert sub.is_prorated is True
        assert sub.start_date.date() == date(2026, 2, 19)
        assert sub.end_date.date() == date(2026, 2, 28)
        # payment_due_date = 7-е СЛЕДУЮЩЕГО месяца при prorated
        assert sub.payment_due_date == date(2026, 3, 7)

        invoice = db_session.query(Invoice).filter(
            Invoice.student_subscription_id == sub.id
        ).first()
        assert invoice is not None
        # Пропорциональная сумма < полной цены
        assert invoice.amount < sub_v2_template.price
        # Feb 19 (чт), total=9, remaining=4 → round(5000*4/9, 2) = 2222.22
        assert invoice.amount == round(5000.0 * 4 / 9, 2)

    def test_auto_pay_when_sufficient_balance(
        self,
        db_session: Session,
        student_rich: Student,
        sub_v2_template,
        client_with_balance: User,
    ):
        """При достаточном балансе инвойс автоматически помечается PAID."""
        initial_balance = client_with_balance.balance  # 10000

        with patch("app.services.subscription_v2.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            sub = add_subscription_to_student_v2(
                db_session,
                student_id=student_rich.id,
                subscription_id=sub_v2_template.id,
                is_auto_renew=False,
            )

        invoice = db_session.query(Invoice).filter(
            Invoice.student_subscription_id == sub.id
        ).first()
        # Баланс 10000 >= 5000 → PAID
        assert invoice.status == InvoiceStatus.PAID

        db_session.refresh(client_with_balance)
        assert client_with_balance.balance == initial_balance - sub_v2_template.price

    def test_invoice_stays_pending_when_insufficient_balance(
        self,
        db_session: Session,
        student_poor: Student,
        sub_v2_template,
        client_no_balance: User,
    ):
        """При нулевом балансе инвойс остаётся PENDING."""
        with patch("app.services.subscription_v2.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            sub = add_subscription_to_student_v2(
                db_session,
                student_id=student_poor.id,
                subscription_id=sub_v2_template.id,
                is_auto_renew=False,
            )

        invoice = db_session.query(Invoice).filter(
            Invoice.student_subscription_id == sub.id
        ).first()
        assert invoice.status == InvoiceStatus.PENDING

    def test_invoice_has_due_date(
        self,
        db_session: Session,
        student_rich: Student,
        sub_v2_template,
        client_with_balance: User,
    ):
        """Инвойс должен содержать due_date = payment_due_date абонемента."""
        with patch("app.services.subscription_v2.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            sub = add_subscription_to_student_v2(
                db_session,
                student_id=student_rich.id,
                subscription_id=sub_v2_template.id,
                is_auto_renew=False,
            )

        invoice = db_session.query(Invoice).filter(
            Invoice.student_subscription_id == sub.id
        ).first()
        assert invoice.due_date == sub.payment_due_date

    def test_raises_if_subscription_template_not_found(self, db_session: Session, student_rich: Student):
        from app.errors.subscription_errors import SubscriptionNotFound
        with pytest.raises(SubscriptionNotFound):
            add_subscription_to_student_v2(db_session, student_rich.id, 99999, False)

    def test_raises_if_subscription_inactive(self, db_session: Session, student_rich: Student, sub_v2_template):
        sub_v2_template.is_active = False
        db_session.commit()
        with pytest.raises(ValueError, match="not active"):
            with patch("app.services.subscription_v2.datetime") as mock_dt:
                mock_dt.now.return_value = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)
                mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
                add_subscription_to_student_v2(db_session, student_rich.id, sub_v2_template.id, False)
