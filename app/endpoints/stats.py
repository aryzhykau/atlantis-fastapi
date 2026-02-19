from datetime import datetime, timedelta, timezone, date
from typing import Dict, Any, List, Tuple

from fastapi import APIRouter, Depends
from sqlalchemy import func, extract, and_, or_, case, desc
from sqlalchemy.orm import Session

from app.auth.permissions import get_current_user
from app.dependencies import get_db
from app.schemas.user import UserRole
from app.models import (
    User,
    Student,
    RealTraining,
    Invoice,
    Expense,
    StudentSubscription,
    InvoiceStatus,
)


router = APIRouter(prefix="/stats", tags=["Stats"])


def _parse_date(d: str | None) -> date | None:
    if not d:
        return None
    return datetime.strptime(d, "%Y-%m-%d").date()


def _generate_buckets(start: date, end: date, interval: str) -> Tuple[List[str], List[Tuple[date, date]]]:
    labels: List[str] = []
    ranges: List[Tuple[date, date]] = []
    if interval == "day":
        current = start
        while current <= end:
            labels.append(current.strftime("%d.%m"))
            ranges.append((current, current))
            current = current + timedelta(days=1)
        return labels, ranges
    if interval == "week":
        # ISO weeks starting Monday
        # Normalize to Monday
        current = start - timedelta(days=start.weekday())
        while current <= end:
            week_start = current
            week_end = min(current + timedelta(days=6), end)
            labels.append(f"{week_start.strftime('%d.%m')}–{week_end.strftime('%d.%m')}")
            ranges.append((week_start, week_end))
            current = current + timedelta(days=7)
        return labels, ranges
    # month
    current = date(start.year, start.month, 1)
    while current <= end:
        # Compute month end
        next_month = date(current.year + (current.month // 12), (current.month % 12) + 1, 1)
        month_end = min(next_month - timedelta(days=1), end)
        labels.append(current.strftime("%b %Y"))
        ranges.append((current, month_end))
        current = next_month
    return labels, ranges


def _get_debt_metrics(db: Session) -> Dict[str, Any]:
    unpaid_by_client = (
        db.query(
            Invoice.client_id,
            func.sum(Invoice.amount).label("unpaid_total"),
        )
        .filter(Invoice.status == InvoiceStatus.UNPAID)
        .group_by(Invoice.client_id)
        .all()
    )

    client_ids = [row.client_id for row in unpaid_by_client]
    clients = {
        c.id: c
        for c in db.query(User)
        .filter(User.id.in_(client_ids), User.role == UserRole.CLIENT)
        .all()
    } if client_ids else {}

    total_unpaid_invoices = 0.0
    total_outstanding_after_balance = 0.0
    debtors: List[Dict[str, Any]] = []

    for row in unpaid_by_client:
        client = clients.get(row.client_id)
        if not client:
            continue

        unpaid_total = float(row.unpaid_total or 0.0)
        balance_credit = float(client.balance or 0.0)
        amount_owed = max(unpaid_total - balance_credit, 0.0)

        total_unpaid_invoices += unpaid_total
        total_outstanding_after_balance += amount_owed

        if amount_owed > 0:
            debtors.append(
                {
                    "client_id": client.id,
                    "first_name": client.first_name,
                    "last_name": client.last_name,
                    "unpaid_invoices_total": unpaid_total,
                    "balance_credit": balance_credit,
                    "amount_owed": amount_owed,
                }
            )

    debtors.sort(key=lambda item: item["amount_owed"], reverse=True)

    return {
        "total_unpaid_invoices": total_unpaid_invoices,
        "total_outstanding_after_balance": total_outstanding_after_balance,
        "debtors": debtors,
        "debtors_count": len(debtors),
    }


def _get_subscription_metrics(db: Session, now: datetime) -> Dict[str, Any]:
    active_condition = and_(
        StudentSubscription.start_date <= now,
        StudentSubscription.end_date >= now,
        or_(
            StudentSubscription.freeze_start_date.is_(None),
            StudentSubscription.freeze_end_date.is_(None),
            StudentSubscription.freeze_start_date > now,
            StudentSubscription.freeze_end_date < now,
        ),
    )

    active_student_subscriptions = db.query(StudentSubscription).filter(active_condition).count()
    students_with_active_subscriptions_count = (
        db.query(func.count(func.distinct(StudentSubscription.student_id)))
        .filter(active_condition)
        .scalar()
        or 0
    )

    students_with_active_subscriptions_expr = func.count(func.distinct(Student.id))
    active_subscriptions_total_expr = func.count(StudentSubscription.id)

    client_rows = (
        db.query(
            User.id.label("client_id"),
            User.first_name,
            User.last_name,
            students_with_active_subscriptions_expr.label("students_with_active_subscriptions"),
            active_subscriptions_total_expr.label("active_subscriptions_total"),
        )
        .join(Student, Student.client_id == User.id)
        .join(StudentSubscription, StudentSubscription.student_id == Student.id)
        .filter(User.role == UserRole.CLIENT, active_condition)
        .group_by(User.id, User.first_name, User.last_name)
        .order_by(desc(active_subscriptions_total_expr), User.last_name, User.first_name)
        .all()
    )

    clients_with_active_subscriptions: List[Dict[str, Any]] = []
    for row in client_rows:
        clients_with_active_subscriptions.append(
            {
                "client_id": row.client_id,
                "first_name": row.first_name,
                "last_name": row.last_name,
                "students_with_active_subscriptions": int(row.students_with_active_subscriptions or 0),
                "active_subscriptions_total": int(row.active_subscriptions_total or 0),
            }
        )

    return {
        "active_student_subscriptions": active_student_subscriptions,
        "students_with_active_subscriptions_count": int(students_with_active_subscriptions_count),
        "clients_with_active_subscriptions_count": len(client_rows),
        "clients_with_active_subscriptions": clients_with_active_subscriptions,
    }


def _get_trainers_workload(
    db: Session,
    start_d: date,
    end_d: date,
) -> Dict[str, Any]:
    trainings_count_expr = func.count(RealTraining.id)
    work_days_count_expr = func.count(func.distinct(RealTraining.training_date))

    trainer_rows = (
        db.query(
            User.id.label("trainer_id"),
            User.first_name,
            User.last_name,
            trainings_count_expr.label("trainings_count"),
            work_days_count_expr.label("work_days_count"),
        )
        .outerjoin(
            RealTraining,
            and_(
                RealTraining.responsible_trainer_id == User.id,
                RealTraining.training_date >= start_d,
                RealTraining.training_date <= end_d,
                RealTraining.cancelled_at.is_(None),
            ),
        )
        .filter(User.role == UserRole.TRAINER)
        .group_by(User.id, User.first_name, User.last_name)
        .order_by(desc(trainings_count_expr), desc(work_days_count_expr), User.last_name, User.first_name)
        .all()
    )

    trainers_workload = [
        {
            "trainer_id": row.trainer_id,
            "first_name": row.first_name,
            "last_name": row.last_name,
            "trainings_count": int(row.trainings_count or 0),
            "work_days_count": int(row.work_days_count or 0),
        }
        for row in trainer_rows
    ]

    return {
        "trainings_per_trainer": trainers_workload,
        "trainers_count": len(trainers_workload),
        "trainers_with_workdays_count": len([t for t in trainers_workload if t["work_days_count"] > 0]),
    }


@router.get("/overview")
def get_overview_stats(
    start_date: str | None = None,
    end_date: str | None = None,
    interval: str = "month",  # day | week | month
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user(["ADMIN", "OWNER"])),
) -> Dict[str, Any]:

    now = datetime.now(timezone.utc)
    # Defaults: last 12 months
    end_d = _parse_date(end_date) or now.date()
    start_d = _parse_date(start_date) or (date(end_d.year - (1 if end_d.month < 12 else 0), (end_d.month % 12) + 1, 1) - timedelta(days=365))
    if start_d > end_d:
        start_d, end_d = end_d, start_d
    if interval not in ("day", "week", "month"):
        interval = "month"
    labels, ranges = _generate_buckets(start_d, end_d, interval)

    # totals
    total_clients = db.query(User).filter(User.role == UserRole.CLIENT).count()
    total_students = db.query(Student).count()

    # Trainings counts for first and overall period convenience
    trainings_in_month = (
        db.query(RealTraining)
        .filter(RealTraining.training_date >= date(now.year, now.month, 1))
        .filter(RealTraining.training_date <= end_d)
        .count()
    )

    trainings_in_year = (
        db.query(RealTraining)
        .filter(extract('year', RealTraining.training_date) == now.year)
        .count()
    )

    # Revenue and expenses aggregations by month of current year
    revenue_series = [0.0 for _ in labels]
    expense_series = [0.0 for _ in labels]
    trainings_series = [0 for _ in labels]

    # Revenue: PAID invoices, use paid_at if available otherwise created_at
    inv_rows = (
        db.query(Invoice.paid_at, Invoice.created_at, Invoice.amount, Invoice.status)
        .filter(Invoice.status == 'PAID')
        .filter(func.coalesce(Invoice.paid_at, Invoice.created_at) >= datetime.combine(start_d, datetime.min.time(), tzinfo=timezone.utc))
        .filter(func.coalesce(Invoice.paid_at, Invoice.created_at) <= datetime.combine(end_d, datetime.max.time(), tzinfo=timezone.utc))
        .all()
    )
    for paid_at, created_at, amount, _ in inv_rows:
        dt = paid_at or created_at
        d = dt.date()
        for idx, (r_start, r_end) in enumerate(ranges):
            if r_start <= d <= r_end:
                revenue_series[idx] += float(amount or 0)
                break

    # Expenses
    exp_rows = (
        db.query(Expense.expense_date, Expense.amount)
        .filter(Expense.expense_date >= datetime.combine(start_d, datetime.min.time(), tzinfo=timezone.utc))
        .filter(Expense.expense_date <= datetime.combine(end_d, datetime.max.time(), tzinfo=timezone.utc))
        .all()
    )
    for exp_dt, amount in exp_rows:
        d = exp_dt.date()
        for idx, (r_start, r_end) in enumerate(ranges):
            if r_start <= d <= r_end:
                expense_series[idx] += float(amount or 0)
                break

    # Trainings
    tr_rows = (
        db.query(RealTraining.training_date)
        .filter(RealTraining.training_date >= start_d)
        .filter(RealTraining.training_date <= end_d)
        .all()
    )
    for tr_d, in tr_rows:
        for idx, (r_start, r_end) in enumerate(ranges):
            if r_start <= tr_d <= r_end:
                trainings_series[idx] += 1
                break

    return {
        "total_clients": total_clients,
        "total_students": total_students,
        "trainings_in_month": trainings_in_month,
        "trainings_in_year": trainings_in_year,
        "labels": labels,
        "revenue_series": revenue_series,
        "expense_series": expense_series,
        "trainings_series": trainings_series,
    }


@router.get("/admin-dashboard")
def get_admin_dashboard_stats(
    start_date: str | None = None,
    end_date: str | None = None,
    interval: str = "month",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user(["ADMIN", "OWNER"])),
) -> Dict[str, Any]:
    """Admin dashboard with non-financial metrics (ADMIN + OWNER access)"""

    now = datetime.now(timezone.utc)
    end_d = _parse_date(end_date) or now.date()
    start_d = _parse_date(start_date) or (date(end_d.year - (1 if end_d.month < 12 else 0), (end_d.month % 12) + 1, 1) - timedelta(days=365))
    
    if start_d > end_d:
        start_d, end_d = end_d, start_d
    if interval not in ("day", "week", "month"):
        interval = "month"
        
    labels, ranges = _generate_buckets(start_d, end_d, interval)

    # Non-financial metrics only
    total_clients = db.query(User).filter(User.role == UserRole.CLIENT).count()
    total_students = db.query(Student).count()
    
    trainings_in_month = (
        db.query(RealTraining)
        .filter(RealTraining.training_date >= date(now.year, now.month, 1))
        .filter(RealTraining.training_date <= end_d)
        .count()
    )

    trainings_in_year = (
        db.query(RealTraining)
        .filter(extract('year', RealTraining.training_date) == now.year)
        .count()
    )

    # Training series data
    trainings_series = [0 for _ in labels]
    tr_rows = (
        db.query(RealTraining.training_date)
        .filter(RealTraining.training_date >= start_d)
        .filter(RealTraining.training_date <= end_d)
        .all()
    )
    for tr_d, in tr_rows:
        for idx, (r_start, r_end) in enumerate(ranges):
            if r_start <= tr_d <= r_end:
                trainings_series[idx] += 1
                break

    return {
        "total_clients": total_clients,
        "total_students": total_students,
        "trainings_in_month": trainings_in_month,
        "trainings_in_year": trainings_in_year,
        "labels": labels,
        "trainings_series": trainings_series,
    }


@router.get("/owner-dashboard")
def get_owner_dashboard_stats(
    start_date: str | None = None,
    end_date: str | None = None,
    interval: str = "month",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user(["OWNER"])),
) -> Dict[str, Any]:
    """Owner dashboard with full financial metrics (OWNER only)"""

    now = datetime.now(timezone.utc)
    end_d = _parse_date(end_date) or now.date()
    start_d = _parse_date(start_date) or (date(end_d.year - (1 if end_d.month < 12 else 0), (end_d.month % 12) + 1, 1) - timedelta(days=365))
    
    if start_d > end_d:
        start_d, end_d = end_d, start_d
    if interval not in ("day", "week", "month"):
        interval = "month"
        
    labels, ranges = _generate_buckets(start_d, end_d, interval)

    # All metrics including financial
    total_clients = db.query(User).filter(User.role == UserRole.CLIENT).count()
    total_students = db.query(Student).count()
    
    trainings_in_month = (
        db.query(RealTraining)
        .filter(RealTraining.training_date >= date(now.year, now.month, 1))
        .filter(RealTraining.training_date <= end_d)
        .count()
    )

    trainings_in_year = (
        db.query(RealTraining)
        .filter(extract('year', RealTraining.training_date) == now.year)
        .count()
    )

    # Financial metrics
    revenue_series = [0.0 for _ in labels]
    expense_series = [0.0 for _ in labels]
    trainings_series = [0 for _ in labels]

    # Revenue calculation
    inv_rows = (
        db.query(Invoice.paid_at, Invoice.created_at, Invoice.amount, Invoice.status)
        .filter(Invoice.status == 'PAID')
        .filter(func.coalesce(Invoice.paid_at, Invoice.created_at) >= datetime.combine(start_d, datetime.min.time(), tzinfo=timezone.utc))
        .filter(func.coalesce(Invoice.paid_at, Invoice.created_at) <= datetime.combine(end_d, datetime.max.time(), tzinfo=timezone.utc))
        .all()
    )
    for paid_at, created_at, amount, _ in inv_rows:
        dt = paid_at or created_at
        d = dt.date()
        for idx, (r_start, r_end) in enumerate(ranges):
            if r_start <= d <= r_end:
                revenue_series[idx] += float(amount or 0)
                break

    # Expenses calculation
    exp_rows = (
        db.query(Expense.expense_date, Expense.amount)
        .filter(Expense.expense_date >= datetime.combine(start_d, datetime.min.time(), tzinfo=timezone.utc))
        .filter(Expense.expense_date <= datetime.combine(end_d, datetime.max.time(), tzinfo=timezone.utc))
        .all()
    )
    for exp_dt, amount in exp_rows:
        d = exp_dt.date()
        for idx, (r_start, r_end) in enumerate(ranges):
            if r_start <= d <= r_end:
                expense_series[idx] += float(amount or 0)
                break

    # Training series
    tr_rows = (
        db.query(RealTraining.training_date)
        .filter(RealTraining.training_date >= start_d)
        .filter(RealTraining.training_date <= end_d)
        .all()
    )
    for tr_d, in tr_rows:
        for idx, (r_start, r_end) in enumerate(ranges):
            if r_start <= tr_d <= r_end:
                trainings_series[idx] += 1
                break

    # Calculate additional owner metrics
    total_revenue = sum(revenue_series)
    total_expenses = sum(expense_series)
    net_profit = total_revenue - total_expenses
    
    # Average revenue per client
    avg_revenue_per_client = total_revenue / total_clients if total_clients > 0 else 0
    debt_metrics = _get_debt_metrics(db)
    subscription_metrics = _get_subscription_metrics(db, now)
    trainers_workload_metrics = _get_trainers_workload(db, start_d, end_d)

    return {
        "total_clients": total_clients,
        "total_students": total_students,
        "trainings_in_month": trainings_in_month,
        "trainings_in_year": trainings_in_year,
        "labels": labels,
        "revenue_series": revenue_series,
        "expense_series": expense_series,
        "trainings_series": trainings_series,
        "total_revenue": total_revenue,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "avg_revenue_per_client": avg_revenue_per_client,
        **debt_metrics,
        **subscription_metrics,
        **trainers_workload_metrics,
    }
