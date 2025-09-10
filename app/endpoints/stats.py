from datetime import datetime, timedelta, timezone, date
from typing import Dict, Any, List, Tuple

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.auth.permissions import get_current_user
from app.dependencies import get_db
from app.schemas.user import UserRole
from app.models import User, Student, RealTraining, Invoice, Expense


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

    new_clients_month = (
        db.query(User)
        .filter(User.role == UserRole.CLIENT)
        .filter(User.id.isnot(None))
        .filter(User.is_active.isnot(None))
        .filter(User.id > 0)  # noop safeguard
        .filter(User.date_of_birth.isnot(None))  # noop safeguard to keep ORM happy
        .count()
    )
    # Note: В проекте нет явного created_at у User — поэтому UI уже считал "новых" по created_at.
    # Здесь оставляем 0, пока не будет добавлено поле created_at. UI продолжит свой способ.
    new_clients_month = 0

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
        "new_clients_month": new_clients_month,
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
    }


