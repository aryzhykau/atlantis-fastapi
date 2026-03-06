"""Эндпоинты для пропущенных занятий (missed sessions)."""
import logging
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.permissions import get_current_user
from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.models import MissedSession
from app.schemas.subscription_v2 import MissedSessionResponse, MissedSessionList
from app.crud.subscription_v2 import (
    get_system_setting,
    excuse_missed_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/missed-sessions", tags=["Missed Sessions"])


@router.get("/student/{student_id}", response_model=MissedSessionList)
def get_missed_sessions_endpoint(
    student_id: int,
    is_excused: Optional[bool] = Query(None),
    is_made_up: Optional[bool] = Query(None),
    current_user=Depends(verify_jwt_token),
    db: Session = Depends(get_db),
):
    """Получить список пропущенных занятий студента."""
    query = db.query(MissedSession).filter(MissedSession.student_id == student_id)
    if is_excused is not None:
        query = query.filter(MissedSession.is_excused == is_excused)
    if is_made_up is not None:
        if is_made_up:
            query = query.filter(MissedSession.made_up_at.isnot(None))
        else:
            query = query.filter(MissedSession.made_up_at.is_(None))
    items = query.order_by(MissedSession.created_at.desc()).all()
    return MissedSessionList(items=items, total=len(items))


@router.post("/{missed_session_id}/excuse", response_model=MissedSessionResponse)
def excuse_missed_session_endpoint(
    missed_session_id: int,
    current_user=Depends(get_current_user(["ADMIN", "TRAINER", "OWNER"])),
    db: Session = Depends(get_db),
):
    """Пометить пропуск как уважительный и установить дедлайн отработки."""
    missed = db.query(MissedSession).filter(MissedSession.id == missed_session_id).first()
    if not missed:
        raise HTTPException(status_code=404, detail="Missed session not found")
    if missed.is_excused:
        raise HTTPException(status_code=400, detail="Already excused")

    # Получаем дату тренировки для расчёта дедлайна
    rts = missed.real_training_student
    training_date = rts.real_training.training_date

    makeup_window_days = int(get_system_setting(db, "makeup_window_days", "90"))
    from datetime import date
    makeup_deadline = training_date + timedelta(days=makeup_window_days)

    result = excuse_missed_session(
        db,
        missed_session_id=missed_session_id,
        excused_by_id=current_user.id,
        makeup_deadline_date=makeup_deadline,
    )
    db.commit()
    return result
