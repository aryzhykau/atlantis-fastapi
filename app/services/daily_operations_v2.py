"""Daily operations v2 — обработка всех тренировок (subscription_only + pay-per-session)."""
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.database import transactional
from app.models import (
    RealTraining,
    RealTrainingStudent,
    AttendanceStatus,
    StudentSubscription,
    MissedSession,
    Invoice,
    InvoiceStatus,
)
from app.models.training_type import TrainingType
from app.crud.subscription_v2 import (
    get_active_or_pending_subscription,
    create_missed_session,
    get_system_setting,
)
from app.services.financial import FinancialService

logger = logging.getLogger(__name__)


class DailyOperationsServiceV2:
    def __init__(self, db: Session):
        self.db = db
        self.financial_service = FinancialService(db)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def process_daily_operations_v2(self) -> dict:
        """Обрабатывает тренировки вчерашнего дня.

        - is_subscription_only=True  → создаёт MissedSession при пропусках.
        - is_subscription_only=False → переводит PENDING инвойсы в UNPAID/CANCELLED.

        Запускается ежедневно в 01:00.
        """
        processing_date = date.today() - timedelta(days=1)
        logger.info(f"[v2] Processing daily operations for date: {processing_date}")

        trainings = (
            self.db.query(RealTraining)
            .join(TrainingType, RealTraining.training_type_id == TrainingType.id)
            .filter(
                RealTraining.training_date == processing_date,
                RealTraining.cancelled_at.is_(None),
            )
            .all()
        )

        subscription_processed = 0
        subscription_skipped = 0
        pay_per_session_processed = 0
        errors = 0

        for training in trainings:
            is_sub_only = training.training_type and training.training_type.is_subscription_only
            for student_training in training.students:
                try:
                    if is_sub_only:
                        result = self._process_subscription_user_v2(student_training)
                        if result == "processed":
                            subscription_processed += 1
                        else:
                            subscription_skipped += 1
                    else:
                        self._process_pay_per_session_user_v2(student_training)
                        pay_per_session_processed += 1
                except Exception as e:
                    logger.error(
                        f"[v2] Error processing student_training {student_training.id}: {e}"
                    )
                    errors += 1

        self.db.commit()
        logger.info(
            f"[v2] Done. subscription_processed={subscription_processed} "
            f"subscription_skipped={subscription_skipped} "
            f"pay_per_session_processed={pay_per_session_processed} errors={errors}"
        )
        return {
            "subscription_processed": subscription_processed,
            "subscription_skipped": subscription_skipped,
            "pay_per_session_processed": pay_per_session_processed,
            "errors": errors,
        }

    def backfill_pending_invoices(self, before_date: date | None = None) -> dict:
        """Одноразовый бэкфилл: переводит PENDING инвойсы типа TRAINING для уже

        прошедших тренировок (до before_date включительно) в UNPAID или CANCELLED.
        Идемпотентен — безопасно запускать повторно.
        """
        from app.models.invoice import InvoiceType

        if before_date is None:
            before_date = date.today()

        pending_invoices = (
            self.db.query(Invoice)
            .join(RealTraining, Invoice.training_id == RealTraining.id)
            .filter(
                Invoice.status == InvoiceStatus.PENDING,
                Invoice.type == InvoiceType.TRAINING,
                RealTraining.training_date < before_date,
            )
            .all()
        )

        processed = 0
        errors = 0

        for invoice in pending_invoices:
            try:
                # Найти запись студента на тренировку, чтобы определить финальный статус
                student_training = (
                    self.db.query(RealTrainingStudent)
                    .filter(
                        RealTrainingStudent.real_training_id == invoice.training_id,
                        RealTrainingStudent.student_id == invoice.student_id,
                    )
                    .first()
                )

                if student_training and student_training.status == AttendanceStatus.CANCELLED_SAFE:
                    invoice.status = InvoiceStatus.CANCELLED
                    self.db.add(invoice)
                else:
                    # PRESENT / ABSENT / REGISTERED / CANCELLED_PENALTY / нет записи → UNPAID
                    invoice.status = InvoiceStatus.UNPAID
                    self.db.add(invoice)
                    self.db.flush()
                    try:
                        self.financial_service.attempt_auto_payment(self.db, invoice.id)
                    except Exception:
                        pass  # Недостаточно баланса — оставить UNPAID, это ок

                processed += 1
            except Exception as e:
                logger.error(f"[v2 backfill] Error processing invoice {invoice.id}: {e}")
                errors += 1

        self.db.commit()
        logger.info(f"[v2 backfill] Done. processed={processed} errors={errors}")
        return {"processed": processed, "errors": errors}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_pay_per_session_user_v2(self, student_training: RealTrainingStudent) -> None:
        """Переводит PENDING training инвойс в UNPAID или CANCELLED.

        Логика:
        - REGISTERED / PRESENT / ABSENT / CANCELLED_PENALTY → UNPAID → попытка автооплаты.
        - CANCELLED_SAFE → CANCELLED (безопасная отмена, платить не нужно).
        - Нет PENDING инвойса → ничего не делаем.
        """
        invoice = (
            self.db.query(Invoice)
            .filter(
                Invoice.student_id == student_training.student_id,
                Invoice.training_id == student_training.real_training_id,
                Invoice.status == InvoiceStatus.PENDING,
            )
            .first()
        )

        if not invoice:
            return

        if student_training.status in (
            AttendanceStatus.REGISTERED,
            AttendanceStatus.PRESENT,
            AttendanceStatus.ABSENT,
            AttendanceStatus.CANCELLED_PENALTY,
        ):
            invoice.status = InvoiceStatus.UNPAID
            self.db.add(invoice)
            self.db.flush()
            try:
                self.financial_service.attempt_auto_payment(self.db, invoice.id)
            except Exception:
                pass  # Недостаточно баланса — оставить UNPAID
            logger.info(
                f"[v2] Invoice {invoice.id} → UNPAID for student {student_training.student_id} "
                f"(status={student_training.status})"
            )
        elif student_training.status == AttendanceStatus.CANCELLED_SAFE:
            invoice.status = InvoiceStatus.CANCELLED
            self.db.add(invoice)
            logger.info(
                f"[v2] Invoice {invoice.id} → CANCELLED (CANCELLED_SAFE) "
                f"for student {student_training.student_id}"
            )

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
