"""Daily operations v2 — обработка is_subscription_only тренировок."""
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database import transactional
from app.models import (
    RealTraining,
    RealTrainingStudent,
    AttendanceStatus,
    StudentSubscription,
    MissedSession,
)
from app.models.training_type import TrainingType
from app.crud.subscription_v2 import (
    get_active_or_pending_subscription,
    create_missed_session,
    get_system_setting,
)

logger = logging.getLogger(__name__)


class DailyOperationsServiceV2:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def process_daily_operations_v2(self) -> dict:
        """Обрабатывает тренировки прошедшего дня (сегодня ≡ вчера для v2).

        Запускается ежедневно в 01:00 для тренировок текущего дня.
        """
        processing_date = date.today()
        logger.info(f"[v2] Processing daily operations for date: {processing_date}")

        trainings = (
            self.db.query(RealTraining)
            .join(TrainingType, RealTraining.training_type_id == TrainingType.id)
            .filter(
                RealTraining.training_date == processing_date,
                RealTraining.cancelled_at.is_(None),
                TrainingType.is_subscription_only == True,
            )
            .all()
        )

        processed = 0
        skipped = 0
        errors = 0

        for training in trainings:
            for student_training in training.students:
                try:
                    result = self._process_subscription_user_v2(student_training)
                    if result == "processed":
                        processed += 1
                    else:
                        skipped += 1
                except Exception as e:
                    logger.error(
                        f"[v2] Error processing student_training {student_training.id}: {e}"
                    )
                    errors += 1

        self.db.commit()
        logger.info(f"[v2] Done. processed={processed} skipped={skipped} errors={errors}")
        return {"processed": processed, "skipped": skipped, "errors": errors}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_subscription_user_v2(self, student_training: RealTrainingStudent) -> str:
        """Обрабатывает одну запись студента на is_subscription_only тренировку (v2).

        - CANCELLED_SAFE → MissedSession(is_excused=True, deadline=+window) — студент может отработать.
        - ABSENT / CANCELLED_PENALTY → MissedSession(is_excused=False) — фиксация без отработки.
        - PRESENT / REGISTERED → ничего дополнительно делать не нужно.
        - sessions_left НЕ декрементируется.
        """
        status = student_training.status

        if status not in (
            AttendanceStatus.CANCELLED_SAFE,
            AttendanceStatus.ABSENT,
            AttendanceStatus.CANCELLED_PENALTY,
            AttendanceStatus.PRESENT,
            AttendanceStatus.REGISTERED,
        ):
            logger.debug(f"[v2] student_training {student_training.id}: status={status} — skip")
            return "skipped"

        if status in (
            AttendanceStatus.CANCELLED_SAFE,
            AttendanceStatus.ABSENT,
            AttendanceStatus.CANCELLED_PENALTY,
        ):
            training_date = student_training.real_training.training_date
            subscription = get_active_or_pending_subscription(
                self.db,
                student_training.student_id,
                training_date,
            )

            if not subscription:
                logger.warning(
                    f"[v2] student_training {student_training.id}: no subscription found "
                    f"for student {student_training.student_id} on {training_date} — skip"
                )
                return "skipped"

            # Идемпотентность — не создаём дубликаты
            existing = (
                self.db.query(MissedSession)
                .filter(MissedSession.real_training_student_id == student_training.id)
                .first()
            )
            if existing:
                logger.debug(
                    f"[v2] MissedSession already exists for student_training {student_training.id}"
                )
                return "skipped"

            if status == AttendanceStatus.CANCELLED_SAFE:
                # Безопасная отмена — студент может отработать пропущенное занятие.
                # is_excused=True + дедлайн устанавливаются автоматически.
                makeup_window_days = int(get_system_setting(self.db, "makeup_window_days", "90"))
                makeup_deadline = training_date + timedelta(days=makeup_window_days)
                missed = create_missed_session(
                    self.db,
                    student_id=student_training.student_id,
                    student_subscription_id=subscription.id,
                    real_training_student_id=student_training.id,
                    is_excused=True,
                    makeup_deadline_date=makeup_deadline,
                )
                logger.info(
                    f"[v2] CANCELLED_SAFE: MissedSession {missed.id} created for student "
                    f"{student_training.student_id}, deadline={makeup_deadline}"
                )
            else:
                # ABSENT / CANCELLED_PENALTY — пропуск фиксируется, но отработка недоступна
                # (is_excused=False, makeup_deadline_date=None).
                missed = create_missed_session(
                    self.db,
                    student_id=student_training.student_id,
                    student_subscription_id=subscription.id,
                    real_training_student_id=student_training.id,
                )
                logger.info(
                    f"[v2] {status.value}: MissedSession {missed.id} created for student "
                    f"{student_training.student_id} on {training_date} (no makeup)"
                )

        return "processed"
