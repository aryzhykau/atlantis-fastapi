"""Unit-тесты: _count_sessions_in_period, _calculate_prorated_amount (BE-20)."""
import pytest
from datetime import date

from app.services.subscription_v2 import (
    _count_sessions_in_period,
    _calculate_prorated_amount,
    _get_month_end_date,
    _get_first_of_next_month,
    _get_payment_due_date,
    _get_monday,
)


# ---------------------------------------------------------------------------
# _get_monday
# ---------------------------------------------------------------------------

class TestGetMonday:
    def test_monday_returns_itself(self):
        assert _get_monday(date(2026, 3, 2)) == date(2026, 3, 2)  # Пн

    def test_wednesday_returns_monday(self):
        assert _get_monday(date(2026, 3, 4)) == date(2026, 3, 2)

    def test_sunday_returns_monday(self):
        assert _get_monday(date(2026, 3, 8)) == date(2026, 3, 2)


# ---------------------------------------------------------------------------
# _count_sessions_in_period
# ---------------------------------------------------------------------------

class TestCountSessionsInPeriod:
    def test_full_week_2pw(self):
        # Пн-Вс — полная неделя, 2×/нед → 2
        assert _count_sessions_in_period(date(2026, 3, 2), date(2026, 3, 8), 2) == 2

    def test_full_week_3pw(self):
        assert _count_sessions_in_period(date(2026, 3, 2), date(2026, 3, 8), 3) == 3

    def test_single_day_week_2pw(self):
        # Только понедельник — min(2, 1) = 1
        assert _count_sessions_in_period(date(2026, 3, 2), date(2026, 3, 2), 2) == 1

    def test_two_days_3pw(self):
        # Пн-Вт — min(3, 2) = 2
        assert _count_sessions_in_period(date(2026, 3, 2), date(2026, 3, 3), 3) == 2

    def test_full_month_february_2026(self):
        # Февраль 2026: Feb 1 = воскресенье, значит 5 пересекающихся недель
        # W0: Jan26-Feb1 → 1 день overlap → min(2,1)=1
        # W1: Feb2-8 → 2, W2: Feb9-15 → 2, W3: Feb16-22 → 2
        # W4: Feb23-Mar1 → Feb23-28 = 6 дней → min(2,6)=2  → total=9
        assert _count_sessions_in_period(date(2026, 2, 1), date(2026, 2, 28), 2) == 9

    def test_full_month_march_2026(self):
        # Март 2026 (31 день): 4 полных нед (2-29) + W1 (1 вс) + W5 (30-31 пн-вт)
        # W1: 2026-02-23..2026-03-01 → overlap with mar: 01 Mar только → min(2,1)=1
        # W2: 02-08 → 7 дней → min(2,7)=2
        # W3: 09-15 → 2
        # W4: 16-22 → 2
        # W5: 23-29 → 2
        # W6: 30-Apr5 → overlap: 30-31 Mar → min(2,2)=2
        # total = 1+2+2+2+2+2 = 11
        result = _count_sessions_in_period(date(2026, 3, 1), date(2026, 3, 31), 2)
        assert result == 11

    def test_partial_period_from_mid_month(self):
        # Февраль 2026, с 19-го (среда W3) до 28-го
        # W3: 16-22 → overlap 19-22 → 4 дней → min(2,4)=2
        # W4: 23-28 → 6 дней → min(2,6)=2
        # total = 4 (как в бизнес-кейсе BK2-1)
        result = _count_sessions_in_period(date(2026, 2, 19), date(2026, 2, 28), 2)
        assert result == 4

    def test_sessions_per_week_1(self):
        # 1×/нед, февраль 2026: 5 пересекающихся недель → min(1,...)=1 каждая → total=5
        assert _count_sessions_in_period(date(2026, 2, 1), date(2026, 2, 28), 1) == 5

    def test_start_equals_end(self):
        # Один день (вторник) → min(2, 1) = 1
        assert _count_sessions_in_period(date(2026, 3, 3), date(2026, 3, 3), 2) == 1


# ---------------------------------------------------------------------------
# _calculate_prorated_amount
# ---------------------------------------------------------------------------

class TestCalculateProratedAmount:
    def test_first_of_month_is_full_price(self):
        # 1 марта → 100% стоимости
        amount = _calculate_prorated_amount(5000.0, date(2026, 3, 1), 2)
        full = 5000.0
        assert amount == full

    def test_mid_february_case(self):
        # Покупка 19 фев 2026 (чт), 2×/нед, цена 5000
        # remaining: W3(Feb16-22) overlap Feb19-22=4д→2, W4(Feb23-Mar1) overlap Feb23-28=6д→2 → 4
        # total=9 → prorated = round(5000 * 4/9, 2) = 2222.22
        amount = _calculate_prorated_amount(5000.0, date(2026, 2, 19), 2)
        assert amount == round(5000.0 * 4 / 9, 2)

    def test_last_day_of_month(self):
        # Покупка 28 фев 2026 (сб) — последний день месяца
        # remaining: W4(Feb23-Mar1) overlap Feb28-28=1д→min(2,1)=1
        # total=9 → prorated = round(5000 * 1/9, 2) = 555.56
        amount = _calculate_prorated_amount(5000.0, date(2026, 2, 28), 2)
        assert amount == round(5000.0 * 1 / 9, 2)

    def test_rounding(self):
        # Должен вернуть округлённое до 2 знаков значение
        # Feb 19: remaining=4, total=9 → round(1000*4/9, 2) = 444.44
        amount = _calculate_prorated_amount(1000.0, date(2026, 2, 19), 2)
        assert amount == round(1000.0 * 4 / 9, 2)

    def test_zero_price(self):
        assert _calculate_prorated_amount(0.0, date(2026, 2, 19), 2) == 0.0


# ---------------------------------------------------------------------------
# Вспомогательные утилиты
# ---------------------------------------------------------------------------

class TestDateUtils:
    def test_month_end_february_2026(self):
        assert _get_month_end_date(date(2026, 2, 1)) == date(2026, 2, 28)

    def test_month_end_march_2026(self):
        assert _get_month_end_date(date(2026, 3, 15)) == date(2026, 3, 31)

    def test_month_end_december(self):
        assert _get_month_end_date(date(2026, 12, 5)) == date(2026, 12, 31)

    def test_first_of_next_month_regular(self):
        assert _get_first_of_next_month(date(2026, 2, 28)) == date(2026, 3, 1)

    def test_first_of_next_month_december(self):
        assert _get_first_of_next_month(date(2026, 12, 15)) == date(2027, 1, 1)

    def test_payment_due_date(self):
        assert _get_payment_due_date(date(2026, 3, 1)) == date(2026, 3, 7)
        assert _get_payment_due_date(date(2026, 2, 28)) == date(2026, 2, 7)
