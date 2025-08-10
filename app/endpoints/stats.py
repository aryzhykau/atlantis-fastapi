from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.schemas.user import UserRole
from app.models import User, Student, RealTraining, Invoice, Expense


router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/overview")
def get_overview_stats(
    year: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(verify_jwt_token),
) -> Dict[str, Any]:
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    now = datetime.now(timezone.utc)
    year = year or now.year
    month_start = datetime(year=now.year, month=now.month, day=1, tzinfo=timezone.utc)

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

    trainings_in_month = (
        db.query(RealTraining)
        .filter(
            extract('year', RealTraining.training_date) == now.year,
            extract('month', RealTraining.training_date) == now.month,
        )
        .count()
    )

    trainings_in_year = (
        db.query(RealTraining)
        .filter(extract('year', RealTraining.training_date) == year)
        .count()
    )

    # Revenue and expenses aggregations by month of current year
    revenue_by_month = [0.0] * 12
    expense_by_month = [0.0] * 12

    rev_rows = (
        db.query(extract('month', Invoice.created_at).label('m'), func.sum(Invoice.amount))
        .filter(extract('year', Invoice.created_at) == year)
        .filter(Invoice.status == 'PAID')
        .group_by('m')
        .all()
    )
    for m, s in rev_rows:
        revenue_by_month[int(m) - 1] = float(s or 0)

    exp_rows = (
        db.query(extract('month', Expense.expense_date).label('m'), func.sum(Expense.amount))
        .filter(extract('year', Expense.expense_date) == year)
        .group_by('m')
        .all()
    )
    for m, s in exp_rows:
        expense_by_month[int(m) - 1] = float(s or 0)

    trainings_by_month = [0] * 12
    tr_rows = (
        db.query(extract('month', RealTraining.training_date).label('m'), func.count(RealTraining.id))
        .filter(extract('year', RealTraining.training_date) == year)
        .group_by('m')
        .all()
    )
    for m, c in tr_rows:
        trainings_by_month[int(m) - 1] = int(c or 0)

    return {
        "total_clients": total_clients,
        "total_students": total_students,
        "new_clients_month": new_clients_month,
        "trainings_in_month": trainings_in_month,
        "trainings_in_year": trainings_in_year,
        "revenue_by_month": revenue_by_month,
        "expense_by_month": expense_by_month,
        "trainings_by_month": trainings_by_month,
    }


