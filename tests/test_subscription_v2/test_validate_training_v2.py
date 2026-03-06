"""Тесты: validate_subscription_for_training_v2 (BE-20)."""
from datetime import date, datetime, timezone, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models import StudentSubscription
from app.models.invoice import Invoice, InvoiceStatus, InvoiceType
from app.models.missed_session import MissedSession
from app.models.real_training import AttendanceStatus
from app.models.system_settings import SystemSettings
from app.validators.subscription_validators_v2 import validate_subscription_for_training_v2

from tests.test_subscription_v2.conftest import (
    make_student_sub_v2,
    make_real_training,
    make_rts,
)

TODAY = date(2026, 3, 2)          # понедельник
WEEK_START = date(2026, 3, 2)     # Пн
WEEK_END   = date(2026, 3, 8)     # Вс


def seed_setting(db_session, key, value):
    s = db_session.query(SystemSettings).filter(SystemSettings.key == key).first()
    if s:
        s.value = value
    else:
        db_session.add(SystemSettings(key=key, value=value))
    db_session.commit()


class TestValidateSubscriptionForTrainingV2:

    # ------------------------------------------------------------------
    # 1. Нет абонемента
    # ------------------------------------------------------------------

    def test_no_subscription_returns_invalid(self, db_session: Session, student_rich, test_admin):
        is_valid, error, _, _ = validate_subscription_for_training_v2(
            db_session, student_rich.id, TODAY, True
        )
        assert is_valid is False
        assert "абонемент" in error.lower()

    # ------------------------------------------------------------------
    # 2. Должник + BLOCK_ACCESS
    # ------------------------------------------------------------------

    def test_debtor_block_access(
        self, db_session: Session, student_rich, client_with_balance, sub_v2_template, test_admin
    ):
        seed_setting(db_session, "debt_behavior", "BLOCK_ACCESS")
        make_student_sub_v2(db_session, student_rich.id, sub_v2_template, TODAY, date(2026, 3, 31))
        # Создаём UNPAID инвойс
        db_session.add(Invoice(
            client_id=client_with_balance.id,
            student_id=student_rich.id,
            amount=100.0,
            description="debt",
            type=InvoiceType.SUBSCRIPTION,
            status=InvoiceStatus.UNPAID,
        ))
        db_session.commit()

        is_valid, error, _, _ = validate_subscription_for_training_v2(
            db_session, student_rich.id, TODAY, True
        )
        assert is_valid is False
        assert "задолженность" in error.lower() or "заблокирован" in error.lower()

    # ------------------------------------------------------------------
    # 3. Должник + HIGHLIGHT_ONLY
    # ------------------------------------------------------------------

    def test_debtor_highlight_only_allowed(
        self, db_session: Session, student_rich, client_with_balance, sub_v2_template, test_admin,
        training_type_sub_only
    ):
        seed_setting(db_session, "debt_behavior", "HIGHLIGHT_ONLY")
        make_student_sub_v2(db_session, student_rich.id, sub_v2_template, TODAY, date(2026, 3, 31))
        db_session.add(Invoice(
            client_id=client_with_balance.id,
            student_id=student_rich.id,
            amount=100.0,
            description="debt",
            type=InvoiceType.SUBSCRIPTION,
            status=InvoiceStatus.UNPAID,
        ))
        db_session.commit()

        is_valid, error, sub, _ = validate_subscription_for_training_v2(
            db_session, student_rich.id, TODAY, True
        )
        assert is_valid is True

    # ------------------------------------------------------------------
    # 4. Тренировка не subscription_only → early exit
    # ------------------------------------------------------------------

    def test_non_subscription_only_always_allowed(
        self, db_session: Session, student_rich, sub_v2_template
    ):
        make_student_sub_v2(db_session, student_rich.id, sub_v2_template, TODAY, date(2026, 3, 31))
        is_valid, error, sub, _ = validate_subscription_for_training_v2(
            db_session, student_rich.id, TODAY, False  # is_subscription_only=False
        )
        assert is_valid is True
        assert error == ""

    # ------------------------------------------------------------------
    # 5. Лимит не достигнут → обычная запись
    # ------------------------------------------------------------------

    def test_within_weekly_limit(
        self, db_session: Session, student_rich, sub_v2_template,
        training_type_sub_only, test_admin
    ):
        seed_setting(db_session, "debt_behavior", "HIGHLIGHT_ONLY")
        student_sub = make_student_sub_v2(
            db_session, student_rich.id, sub_v2_template, TODAY, date(2026, 3, 31)
        )
        # Одна запись на этой неделе (лимит 2), статус PRESENT
        rt = make_real_training(db_session, TODAY, training_type_sub_only, test_admin.id)
        make_rts(db_session, rt, student_rich.id, AttendanceStatus.PRESENT, student_sub.id)

        is_valid, error, sub, makeup = validate_subscription_for_training_v2(
            db_session, student_rich.id, TODAY + timedelta(days=2), True
        )
        assert is_valid is True
        assert makeup is None

    # ------------------------------------------------------------------
    # 6. Превышен лимит, нет отработки → отказ
    # ------------------------------------------------------------------

    def test_over_limit_no_makeup(
        self, db_session: Session, student_rich, sub_v2_template,
        training_type_sub_only, test_admin
    ):
        seed_setting(db_session, "debt_behavior", "HIGHLIGHT_ONLY")
        student_sub = make_student_sub_v2(
            db_session, student_rich.id, sub_v2_template, TODAY, date(2026, 3, 31)
        )
        # 2 записи на этой неделе = достигнут лимит sessions_per_week=2
        rt1 = make_real_training(db_session, TODAY, training_type_sub_only, test_admin.id)
        rt2 = make_real_training(db_session, TODAY + timedelta(days=1), training_type_sub_only, test_admin.id)
        make_rts(db_session, rt1, student_rich.id, AttendanceStatus.PRESENT, student_sub.id)
        make_rts(db_session, rt2, student_rich.id, AttendanceStatus.PRESENT, student_sub.id)

        training_date = TODAY + timedelta(days=2)
        is_valid, error, _, _ = validate_subscription_for_training_v2(
            db_session, student_rich.id, training_date, True
        )
        assert is_valid is False
        assert "лимит" in error.lower()

    # ------------------------------------------------------------------
    # 7. Превышен лимит, есть excused пропуск → отработка разрешена
    # ------------------------------------------------------------------

    def test_over_limit_with_excused_makeup(
        self, db_session: Session, student_rich, sub_v2_template,
        training_type_sub_only, test_admin
    ):
        seed_setting(db_session, "debt_behavior", "HIGHLIGHT_ONLY")
        student_sub = make_student_sub_v2(
            db_session, student_rich.id, sub_v2_template, TODAY, date(2026, 3, 31)
        )
        # 2 записи на этой неделе — достигнут лимит
        rt1 = make_real_training(db_session, TODAY, training_type_sub_only, test_admin.id)
        rt2 = make_real_training(db_session, TODAY + timedelta(days=1), training_type_sub_only, test_admin.id)
        rts1 = make_rts(db_session, rt1, student_rich.id, AttendanceStatus.PRESENT, student_sub.id)
        rts2 = make_rts(db_session, rt2, student_rich.id, AttendanceStatus.PRESENT, student_sub.id)

        # Старый excused пропуск с действующим дедлайном
        old_rt = make_real_training(db_session, date(2026, 2, 5), training_type_sub_only, test_admin.id)
        old_rts = make_rts(db_session, old_rt, student_rich.id, AttendanceStatus.ABSENT, student_sub.id)
        missed = MissedSession(
            student_id=student_rich.id,
            student_subscription_id=student_sub.id,
            real_training_student_id=old_rts.id,
            is_excused=True,
            makeup_deadline_date=date(2026, 5, 5),
        )
        db_session.add(missed)
        db_session.commit()

        training_date = TODAY + timedelta(days=2)
        is_valid, error, sub, makeup_session = validate_subscription_for_training_v2(
            db_session, student_rich.id, training_date, True
        )
        assert is_valid is True
        assert makeup_session is not None
        assert makeup_session.id == missed.id

    # ------------------------------------------------------------------
    # 8. CANCELLED_SAFE не учитывается в лимите
    # ------------------------------------------------------------------

    def test_cancelled_safe_not_counted(
        self, db_session: Session, student_rich, sub_v2_template,
        training_type_sub_only, test_admin
    ):
        seed_setting(db_session, "debt_behavior", "HIGHLIGHT_ONLY")
        student_sub = make_student_sub_v2(
            db_session, student_rich.id, sub_v2_template, TODAY, date(2026, 3, 31)
        )
        # 2 записи, но одна CANCELLED_SAFE → фактически только 1 «использованная»
        rt1 = make_real_training(db_session, TODAY, training_type_sub_only, test_admin.id)
        rt2 = make_real_training(db_session, TODAY + timedelta(days=1), training_type_sub_only, test_admin.id)
        make_rts(db_session, rt1, student_rich.id, AttendanceStatus.PRESENT, student_sub.id)
        make_rts(db_session, rt2, student_rich.id, AttendanceStatus.CANCELLED_SAFE, student_sub.id)

        training_date = TODAY + timedelta(days=2)
        is_valid, error, sub, _ = validate_subscription_for_training_v2(
            db_session, student_rich.id, training_date, True
        )
        # 1 < 2 (sessions_per_week) → разрешено
        assert is_valid is True
