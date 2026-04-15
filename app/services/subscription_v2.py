"""Сервисные утилиты для системы абонементов v2.

Чистые функции без зависимостей от БД — в начале файла.
Бизнес-логика (add_subscription_to_student_v2, process_auto_renewals_v2,
process_overdue_invoices_v2) — в конце.
"""
import calendar
import logging
from datetime import date, datetime, timedelta, timezone
from typing import List

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _get_monday(d: date) -> date:
    """Возвращает понедельник недели, в которую попадает дата d."""
    return d - timedelta(days=d.weekday())


def _count_sessions_in_period(
    period_start: date,
    period_end: date,
    sessions_per_week: int,
) -> int:
    """Считает максимально возможное число тренировок в периоде [period_start, period_end].

    Неделя = Пн–Вс. Для каждой недели, пересекающейся с периодом,
    вклад = min(sessions_per_week, кол-во дней недели внутри периода).

    Пример: sessions_per_week=2, последняя неделя с единственным понедельником
    → min(2, 1) = 1 тренировка.
    """
    total = 0
    # Начинаем с понедельника первой недели, пересекающейся с периодом
    week_monday = _get_monday(period_start)
    while week_monday <= period_end:
        week_sunday = week_monday + timedelta(days=6)
        # Пересечение недели и периода
        overlap_start = max(week_monday, period_start)
        overlap_end = min(week_sunday, period_end)
        days_in_period = (overlap_end - overlap_start).days + 1
        total += min(sessions_per_week, days_in_period)
        week_monday += timedelta(weeks=1)
    return total


def _calculate_prorated_amount(
    price: float,
    purchase_date: date,
    sessions_per_week: int,
) -> float:
    """Рассчитывает пропорциональную стоимость абонемента при покупке в середине месяца.

    prorated_amount = price * remaining_possible / total_sessions_in_month
    """
    month_start = purchase_date.replace(day=1)
    month_end = _get_month_end_date(purchase_date)

    total_sessions_in_month = _count_sessions_in_period(month_start, month_end, sessions_per_week)
    if total_sessions_in_month == 0:
        return 0.0

    remaining_possible = _count_sessions_in_period(purchase_date, month_end, sessions_per_week)
    return round(price * remaining_possible / total_sessions_in_month, 2)


def _get_month_end_date(d: date) -> date:
    """Возвращает последний день месяца для даты d."""
    last_day = calendar.monthrange(d.year, d.month)[1]
    return d.replace(day=last_day)


def _get_first_of_next_month(d: date) -> date:
    """Возвращает первое число следующего месяца."""
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return d.replace(month=d.month + 1, day=1)


def _get_payment_due_date(month_date: date) -> date:
    """Возвращает 7-е число месяца из переданной даты."""
    return month_date.replace(day=7)


# ---------------------------------------------------------------------------
# Business Logic (требуют БД)
# ---------------------------------------------------------------------------

def add_subscription_to_student_v2(
    db: Session,
    student_id: int,
    subscription_id: int,
    is_auto_renew: bool,
) -> "StudentSubscription":
    """Назначает абонемент студенту (v2 логика).

    Если покупка 1-го числа: сразу создаёт PENDING инвойс, абонемент активен.
    Если mid-month: абонемент в PENDING_SCHEDULE, инвойс выставится после настройки расписания.
    """
    from app.models import StudentSubscription, Subscription
    from app.models.student import Student
    from app.models.invoice import InvoiceStatus, InvoiceType
    from app.schemas.invoice import InvoiceCreate
    from app.crud import subscription as sub_crud
    from app.crud import student as student_crud
    from app.crud.subscription_v2 import get_pending_schedule_subscription, get_active_or_pending_subscription
    from app.services.financial import FinancialService
    from app.errors.subscription_errors import SubscriptionNotFound, SubscriptionAlreadyActive

    financial_service = FinancialService(db)

    subscription = sub_crud.get_subscription_by_id(db, subscription_id)
    if not subscription:
        raise SubscriptionNotFound("Subscription template not found")
    if not subscription.is_active:
        raise ValueError("Subscription template is not active")

    student = student_crud.get_student_by_id(db, student_id)
    if not student or not student.is_active:
        raise ValueError("Student not found or inactive")

    # Проверка на дублирующий абонемент
    purchase_date = datetime.now(timezone.utc).date()
    existing_active = get_active_or_pending_subscription(db, student_id, purchase_date)
    if existing_active:
        raise SubscriptionAlreadyActive("Student already has an active subscription")
    existing_pending_schedule = get_pending_schedule_subscription(db, student_id)
    if existing_pending_schedule:
        raise SubscriptionAlreadyActive("Student already has a subscription pending schedule setup")

    end_date_d = _get_month_end_date(purchase_date)
    start_dt = datetime(purchase_date.year, purchase_date.month, purchase_date.day, tzinfo=timezone.utc)
    end_dt = datetime(end_date_d.year, end_date_d.month, end_date_d.day, 23, 59, 59, tzinfo=timezone.utc)

    if purchase_date.day == 1:
        # Полный месяц: сразу активируем и выставляем счёт
        payment_due_date = _get_payment_due_date(purchase_date)
        student_sub = StudentSubscription(
            student_id=student_id,
            subscription_id=subscription_id,
            start_date=start_dt,
            end_date=end_dt,
            is_auto_renew=is_auto_renew,
            is_prorated=False,
            payment_due_date=payment_due_date,
            sessions_left=0,
            schedule_confirmed_at=datetime.now(timezone.utc),
        )
        db.add(student_sub)
        db.flush()
        db.refresh(student_sub)

        invoice_data = InvoiceCreate(
            client_id=student.client_id,
            student_id=student_id,
            subscription_id=subscription_id,
            student_subscription_id=student_sub.id,
            type=InvoiceType.SUBSCRIPTION,
            amount=subscription.price,
            description=f"Абонемент: {subscription.name} (v2)",
            status=InvoiceStatus.PENDING,
            is_auto_renewal=False,
        )
        invoice = financial_service.create_standalone_invoice_in_session(db, invoice_data, auto_pay=True)
        invoice.due_date = payment_due_date
        db.flush()
    else:
        # Mid-month: PENDING_SCHEDULE, инвойс выставится после настройки расписания
        student_sub = StudentSubscription(
            student_id=student_id,
            subscription_id=subscription_id,
            start_date=start_dt,
            end_date=end_dt,
            is_auto_renew=is_auto_renew,
            is_prorated=True,
            payment_due_date=None,
            sessions_left=0,
            schedule_confirmed_at=None,  # PENDING_SCHEDULE
        )
        db.add(student_sub)
        db.flush()
        db.refresh(student_sub)

    return student_sub


def confirm_schedule_and_create_invoice(
    db: Session,
    student_subscription_id: int,
    template_ids: list[int],
) -> "Invoice":
    """Триггер: вызывается когда count(шаблоны) == sessions_per_week.

    Считает сессии по дням недели из TrainingStudentTemplate (не зависит от RealTraining).

    Для каждого шаблона студента:
      - day_of_week = TrainingTemplate.day_number (1=Пн ... 7=Вс)
      - effective_start = max(today, TrainingStudentTemplate.start_date)
      - remaining = кол-во вхождений этого дня недели от effective_start до конца месяца
      - total    = кол-во вхождений этого дня недели за весь месяц

    Если remaining == 0 → сдвигаем на следующий месяц, полная цена.
    """
    from app.models import StudentSubscription
    from app.models.training_template import TrainingStudentTemplate, TrainingTemplate
    from app.models.invoice import InvoiceStatus, InvoiceType
    from app.schemas.invoice import InvoiceCreate
    from app.crud import subscription as sub_crud
    from app.crud import student as student_crud
    from app.services.financial import FinancialService

    financial_service = FinancialService(db)

    student_sub = db.query(StudentSubscription).filter(
        StudentSubscription.id == student_subscription_id
    ).first()
    if not student_sub:
        raise ValueError(f"StudentSubscription {student_subscription_id} not found")
    if student_sub.schedule_confirmed_at is not None:
        return None  # идемпотентность

    subscription = sub_crud.get_subscription_by_id(db, student_sub.subscription_id)
    student = student_crud.get_student_by_id(db, student_sub.student_id)

    today = datetime.now(timezone.utc).date()
    month_start = today.replace(day=1)
    month_end = _get_month_end_date(today)

    def _count_weekday_occurrences(day_number: int, start: date, end: date) -> int:
        """Считает кол-во вхождений дня недели (1=Пн..7=Вс) в диапазоне [start, end]."""
        if start > end:
            return 0
        # isoweekday(): 1=Пн .. 7=Вс — совпадает с day_number
        days_total = (end - start).days + 1
        full_weeks, remainder = divmod(days_total, 7)
        count = full_weeks
        # start.isoweekday() .. start.isoweekday() + remainder - 1
        start_dow = start.isoweekday()
        for offset in range(remainder):
            if ((start_dow - 1 + offset) % 7) + 1 == day_number:
                count += 1
        return count

    # Загружаем студенческие шаблоны по training_template_id
    student_templates = (
        db.query(TrainingStudentTemplate, TrainingTemplate)
        .join(TrainingTemplate, TrainingStudentTemplate.training_template_id == TrainingTemplate.id)
        .filter(
            TrainingStudentTemplate.student_id == student_sub.student_id,
            TrainingStudentTemplate.is_frozen == False,
            TrainingTemplate.id.in_(template_ids),
        )
        .all()
    )

    total_sessions = 0
    remaining_sessions = 0

    for tst, tt in student_templates:
        day_number = tt.day_number  # 1..7
        # effective start = max(today, шаблон.start_date)
        effective_start = max(today, tst.start_date)
        total_sessions += _count_weekday_occurrences(day_number, month_start, month_end)
        remaining_sessions += _count_weekday_occurrences(day_number, effective_start, month_end)

    if remaining_sessions == 0 or total_sessions == 0:
        # В этом месяце тренировок уже нет — сдвигаем на следующий
        next_first = _get_first_of_next_month(today)
        next_last = _get_month_end_date(next_first)
        student_sub.start_date = datetime(next_first.year, next_first.month, next_first.day, tzinfo=timezone.utc)
        student_sub.end_date = datetime(next_last.year, next_last.month, next_last.day, 23, 59, 59, tzinfo=timezone.utc)
        amount = subscription.price
        payment_due_date = _get_payment_due_date(next_first)
    else:
        amount = round(subscription.price * remaining_sessions / total_sessions, 2)
        next_month_first = _get_first_of_next_month(today)
        payment_due_date = _get_payment_due_date(next_month_first)

    student_sub.payment_due_date = payment_due_date
    student_sub.schedule_confirmed_at = datetime.now(timezone.utc)
    db.flush()

    invoice_data = InvoiceCreate(
        client_id=student.client_id,
        student_id=student_sub.student_id,
        subscription_id=student_sub.subscription_id,
        student_subscription_id=student_sub.id,
        type=InvoiceType.SUBSCRIPTION,
        amount=amount,
        description=f"Абонемент: {subscription.name} (v2)",
        status=InvoiceStatus.PENDING,
        is_auto_renewal=False,
    )
    invoice = financial_service.create_standalone_invoice_in_session(db, invoice_data, auto_pay=True)
    invoice.due_date = payment_due_date
    db.flush()

    return invoice


def process_auto_renewals_v2(db: Session) -> dict:
    """Cron: создаёт абонементы на следующий месяц для подписчиков с is_auto_renew.

    Запускается в последний день месяца (02:00).
    Идемпотентен: пропускает тех, у кого уже есть auto_renewal_invoice_id.
    """
    from app.database import transactional
    from app.models import StudentSubscription, Subscription
    from app.models.invoice import InvoiceStatus, InvoiceType
    from app.schemas.invoice import InvoiceCreate
    from app.crud import subscription as sub_crud
    from app.crud import student as student_crud
    from app.services.financial import FinancialService

    financial_service = FinancialService(db)
    today = datetime.now(timezone.utc).date()

    base_query = (
        db.query(StudentSubscription)
        .filter(
            and_(
                StudentSubscription.is_auto_renew == True,
                func.date(StudentSubscription.end_date) == today,
                StudentSubscription.auto_renewal_invoice_id.is_(None),
                # Не замороженные
                ~(
                    and_(
                        StudentSubscription.freeze_start_date.isnot(None),
                        StudentSubscription.freeze_end_date.isnot(None),
                        StudentSubscription.freeze_end_date >= func.now(),
                    )
                ),
            )
        )
    )
    try:
        candidates: List[StudentSubscription] = base_query.with_for_update(skip_locked=True).all()
    except Exception:
        # SQLite (тесты) не поддерживает skip_locked — fallback
        candidates = base_query.all()

    processed = 0
    errors = 0
    for old_sub in candidates:
        try:
            subscription = sub_crud.get_subscription_by_id(db, old_sub.subscription_id)
            if not subscription or not subscription.is_active:
                logger.warning(f"Subscription template {old_sub.subscription_id} inactive, skipping student {old_sub.student_id}")
                continue

            student = student_crud.get_student_by_id(db, old_sub.student_id)
            if not student or not student.is_active:
                logger.warning(f"Student {old_sub.student_id} inactive, skipping")
                continue

            next_first = _get_first_of_next_month(today)
            next_last = _get_month_end_date(next_first)
            payment_due_date = _get_payment_due_date(next_first)

            new_sub = StudentSubscription(
                student_id=old_sub.student_id,
                subscription_id=old_sub.subscription_id,
                start_date=datetime(next_first.year, next_first.month, next_first.day, tzinfo=timezone.utc),
                end_date=datetime(next_last.year, next_last.month, next_last.day, 23, 59, 59, tzinfo=timezone.utc),
                is_auto_renew=True,
                is_prorated=False,
                payment_due_date=payment_due_date,
                sessions_left=0,
            )
            db.add(new_sub)
            db.flush()
            db.refresh(new_sub)

            invoice_data = InvoiceCreate(
                client_id=student.client_id,
                student_id=old_sub.student_id,
                subscription_id=old_sub.subscription_id,
                student_subscription_id=new_sub.id,
                type=InvoiceType.SUBSCRIPTION,
                amount=subscription.price,
                description=f"Автопродление: {subscription.name}",
                status=InvoiceStatus.PENDING,
                is_auto_renewal=True,
            )
            invoice = financial_service.create_standalone_invoice_in_session(db, invoice_data, auto_pay=True)
            invoice.due_date = payment_due_date
            db.flush()

            # Идемпотентность
            old_sub.auto_renewal_invoice_id = invoice.id
            db.flush()

            processed += 1
        except Exception as e:
            logger.error(f"Error processing auto-renewal for subscription {old_sub.id}: {e}")
            errors += 1

    db.commit()
    return {"processed": processed, "errors": errors}


def process_overdue_invoices_v2(db: Session) -> dict:
    """Cron: переводит просроченные PENDING инвойсы в UNPAID (или PAID если баланс достаточен).

    Запускается ежедневно в 08:00.
    """
    from app.models.invoice import InvoiceStatus, InvoiceType, Invoice
    from app.crud import invoice as invoice_crud
    from app.crud import user as user_crud
    from app.schemas.user import UserUpdate

    today = datetime.now(timezone.utc).date()

    overdue = (
        db.query(Invoice)
        .filter(
            and_(
                Invoice.status == InvoiceStatus.PENDING,
                Invoice.due_date < today,
                Invoice.type == InvoiceType.SUBSCRIPTION,
            )
        )
        .all()
    )

    paid = 0
    unpaid = 0
    for invoice in overdue:
        try:
            user = user_crud.get_user_by_id(db, invoice.client_id)
            balance = (user.balance or 0.0) if user else 0.0
            if user and balance >= invoice.amount:
                from app.schemas.user import UserUpdate
                invoice_crud.mark_invoice_as_paid(db, invoice.id)
                user_crud.update_user(db, user.id, UserUpdate(balance=balance - invoice.amount))
                paid += 1
            else:
                invoice_crud.mark_invoice_as_unpaid(db, invoice.id)
                unpaid += 1
        except Exception as e:
            logger.error(f"Error processing overdue invoice {invoice.id}: {e}")

    db.commit()
    return {"paid": paid, "unpaid": unpaid}
