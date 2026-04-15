"""CRUD helpers для системы абонементов v2.

Все функции используют db.flush() (не db.commit()).
Транзакции — только на уровне сервиса.
"""
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models import StudentSubscription, Invoice, MissedSession, SystemSettings
from app.models.real_training import RealTrainingStudent, RealTraining, AttendanceStatus
from app.models.training_type import TrainingType
from app.models.invoice import InvoiceStatus


# ---------------------------------------------------------------------------
# SystemSettings
# ---------------------------------------------------------------------------

def get_system_setting(db: Session, key: str, default: str = "") -> str:
    """Читает значение из system_settings, возвращает default если не найдено."""
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    return setting.value if setting else default


def set_system_setting(db: Session, key: str, value: str, updated_by_id: Optional[int] = None) -> SystemSettings:
    """Создаёт или обновляет запись в system_settings."""
    setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
    if setting:
        setting.value = value
        setting.updated_by_id = updated_by_id
    else:
        setting = SystemSettings(key=key, value=value, updated_by_id=updated_by_id)
        db.add(setting)
    db.flush()
    return setting


# ---------------------------------------------------------------------------
# StudentSubscription
# ---------------------------------------------------------------------------

def get_active_or_pending_subscription(
    db: Session,
    student_id: int,
    training_date: date,
) -> Optional[StudentSubscription]:
    """Возвращает активный или pending абонемент, чей диапазон покрывает training_date.

    Frozen и pending_schedule абонементы исключаются.
    """
    return (
        db.query(StudentSubscription)
        .filter(
            and_(
                StudentSubscription.student_id == student_id,
                func.date(StudentSubscription.start_date) <= training_date,
                func.date(StudentSubscription.end_date) >= training_date,
                # Только подтверждённые (не pending_schedule)
                StudentSubscription.schedule_confirmed_at.isnot(None),
                # Исключаем замороженные
                ~(
                    and_(
                        StudentSubscription.freeze_start_date.isnot(None),
                        StudentSubscription.freeze_end_date.isnot(None),
                        StudentSubscription.freeze_start_date <= func.now(),
                        StudentSubscription.freeze_end_date >= func.now(),
                    )
                ),
            )
        )
        .first()
    )


# ---------------------------------------------------------------------------
# Weekly visit counting
# ---------------------------------------------------------------------------

def count_subscription_only_visits(
    db: Session,
    student_id: int,
    week_start: date,
    week_end: date,
) -> int:
    """Считает ВСЕ записи студента на is_subscription_only тренировки за Пн-Вс неделю.

    Исключает статус CANCELLED_SAFE (слот освобождён).
    Считает: PRESENT, ABSENT, CANCELLED_PENALTY, REGISTERED и все прочие.
    """
    count = (
        db.query(func.count(RealTrainingStudent.id))
        .join(RealTraining, RealTrainingStudent.real_training_id == RealTraining.id)
        .join(TrainingType, RealTraining.training_type_id == TrainingType.id)
        .filter(
            and_(
                RealTrainingStudent.student_id == student_id,
                TrainingType.is_subscription_only == True,
                RealTraining.training_date >= week_start,
                RealTraining.training_date <= week_end,
                RealTrainingStudent.status != AttendanceStatus.CANCELLED_SAFE,
            )
        )
        .scalar()
    )
    return count or 0


# ---------------------------------------------------------------------------
# MissedSession
# ---------------------------------------------------------------------------

def get_oldest_valid_excused_missed_session(
    db: Session,
    student_id: int,
) -> Optional[MissedSession]:
    """FIFO: старейший excused пропуск без отработки с не просроченным дедлайном."""
    today = datetime.now(timezone.utc).date()
    return (
        db.query(MissedSession)
        .join(
            RealTrainingStudent,
            MissedSession.real_training_student_id == RealTrainingStudent.id,
        )
        .join(RealTraining, RealTrainingStudent.real_training_id == RealTraining.id)
        .filter(
            and_(
                MissedSession.student_id == student_id,
                MissedSession.is_excused == True,
                MissedSession.made_up_at.is_(None),
                MissedSession.makeup_deadline_date >= today,
            )
        )
        .order_by(RealTraining.training_date.asc())
        .first()
    )


def create_missed_session(
    db: Session,
    student_id: int,
    student_subscription_id: int,
    real_training_student_id: int,
    is_excused: bool = False,
    makeup_deadline_date: Optional[date] = None,
) -> MissedSession:
    """Создаёт запись пропуска.

    - CANCELLED_SAFE / school cancel → is_excused=True + deadline (доступна отработка).
    - ABSENT / CANCELLED_PENALTY → is_excused=False, без дедлайна (только трекинг).
    """
    missed = MissedSession(
        student_id=student_id,
        student_subscription_id=student_subscription_id,
        real_training_student_id=real_training_student_id,
        is_excused=is_excused,
        makeup_deadline_date=makeup_deadline_date,
    )
    db.add(missed)
    db.flush()
    return missed


def mark_missed_session_as_made_up(
    db: Session,
    missed_session_id: int,
    makeup_rts_id: int,
) -> Optional[MissedSession]:
    """Помечает пропуск как отработанный."""
    missed = db.query(MissedSession).filter(MissedSession.id == missed_session_id).first()
    if not missed:
        return None
    missed.made_up_at = datetime.now(timezone.utc)
    missed.made_up_real_training_student_id = makeup_rts_id
    db.flush()
    return missed


def excuse_missed_session(
    db: Session,
    missed_session_id: int,
    excused_by_id: int,
    makeup_deadline_date: date,
) -> Optional[MissedSession]:
    """Ставит is_excused=True и устанавливает дедлайн отработки."""
    missed = db.query(MissedSession).filter(MissedSession.id == missed_session_id).first()
    if not missed:
        return None
    missed.is_excused = True
    missed.excused_by_id = excused_by_id
    missed.excused_at = datetime.now(timezone.utc)
    missed.makeup_deadline_date = makeup_deadline_date
    db.flush()
    return missed


# ---------------------------------------------------------------------------
# Helpers for schedule confirmation trigger
# ---------------------------------------------------------------------------

def get_pending_schedule_subscription(
    db: Session,
    student_id: int,
) -> Optional[StudentSubscription]:
    """Возвращает абонемент студента в статусе PENDING_SCHEDULE (schedule_confirmed_at IS NULL)."""
    return (
        db.query(StudentSubscription)
        .filter(
            StudentSubscription.student_id == student_id,
            StudentSubscription.schedule_confirmed_at.is_(None),
        )
        .first()
    )


def count_student_active_templates(
    db: Session,
    student_id: int,
) -> int:
    """Считает количество активных (не замороженных) TrainingStudentTemplate студента."""
    from app.models.training_template import TrainingStudentTemplate
    return (
        db.query(func.count(TrainingStudentTemplate.id))
        .filter(
            TrainingStudentTemplate.student_id == student_id,
            TrainingStudentTemplate.is_frozen == False,
        )
        .scalar()
    ) or 0


def get_student_template_ids(
    db: Session,
    student_id: int,
) -> list[int]:
    """Возвращает список training_template_id для всех активных шаблонов студента."""
    from app.models.training_template import TrainingStudentTemplate
    rows = (
        db.query(TrainingStudentTemplate.training_template_id)
        .filter(
            TrainingStudentTemplate.student_id == student_id,
            TrainingStudentTemplate.is_frozen == False,
        )
        .all()
    )
    return [r[0] for r in rows]
