import logging
from datetime import datetime, timedelta, date, timezone
from typing import List, Dict, Any, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import (
    RealTraining,
    RealTrainingStudent,
    StudentSubscription,
    Invoice,
    InvoiceStatus,
    InvoiceType
)
from app.models.real_training import AttendanceStatus
from app.schemas.invoice import InvoiceCreate

from app.database import transactional
from app.services.financial import FinancialService

logger = logging.getLogger(__name__)


class TrainingProcessingService:
    def __init__(self, db: Session):
        self.db = db
        self.financial_service = FinancialService(db)

    def process_tomorrow_trainings(self, admin_id: int) -> Dict[str, Any]:
        """
        Основной метод для обработки всех тренировок на завтра
        """
        with transactional(self.db) as session:
            return self._process_tomorrow_trainings_logic(session, admin_id)

    def _process_tomorrow_trainings_logic(self, session: Session, admin_id: int) -> Dict[str, Any]:
        overall_result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "admin_id": admin_id,
            "trainings_processed": 0,
            "total_students_processed": 0,
            "total_sessions_deducted": 0,
            "total_invoices_created": 0,
            "total_errors": 0,
            "training_results": []
        }

        tomorrow_trainings = self._get_tomorrow_trainings(session)
        
        if not tomorrow_trainings:
            overall_result["message"] = "Нет тренировок на завтра для обработки"
            return overall_result

        for training in tomorrow_trainings:
            training_result = self._process_training(session, training)
            overall_result["training_results"].append(training_result)
            overall_result["trainings_processed"] += 1
            overall_result["total_students_processed"] += training_result["students_processed"]
            overall_result["total_sessions_deducted"] += training_result["sessions_deducted"]
            overall_result["total_invoices_created"] += training_result["invoices_created"]
            overall_result["total_errors"] += training_result["errors"]

        overall_result["message"] = "Обработка завершена успешно"
        logger.info(f"Обработано {overall_result['trainings_processed']} тренировок, "
                   f"создано {overall_result['total_invoices_created']} инвойсов, "
                   f"списано {overall_result['total_sessions_deducted']} занятий")

        return overall_result

    def _get_tomorrow_trainings(self, session: Session) -> List[RealTraining]:
        """Получение тренировок на завтра"""
        tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
        return (
            session.query(RealTraining)
            .filter(
                and_(
                    RealTraining.training_date == tomorrow,
                    RealTraining.processed_at.is_(None)
                )
            )
            .all()
        )

    def _get_active_subscription(self, session: Session, student_id: int, training_date: date) -> Optional[StudentSubscription]:
        """
        Получение активного абонемента студента на дату тренировки
        (This logic should ideally be in SubscriptionService)
        """
        return (
            session.query(StudentSubscription)
            .filter(
                and_(
                    StudentSubscription.student_id == student_id,
                    StudentSubscription.status == "active",
                    StudentSubscription.sessions_left > 0,
                    StudentSubscription.start_date <= training_date,
                    StudentSubscription.end_date >= training_date,
                    or_(
                        StudentSubscription.freeze_start_date.is_(None),
                        StudentSubscription.freeze_end_date.is_(None),
                        and_(
                            StudentSubscription.freeze_start_date.isnot(None),
                            StudentSubscription.freeze_end_date.isnot(None),
                            or_(
                                StudentSubscription.freeze_start_date > training_date,
                                StudentSubscription.freeze_end_date < training_date
                            )
                        )
                    )
                )
            )
            .first()
        )

    def _check_existing_invoice(self, session: Session, student_id: int, training_id: int) -> bool:
        """Проверка существования инвойса за тренировку"""
        return (
            session.query(Invoice)
            .filter(
                and_(
                    Invoice.student_id == student_id,
                    Invoice.training_id == training_id,
                    Invoice.status != InvoiceStatus.CANCELLED
                )
            )
            .first() is not None
        )

    def _process_student_training(
        self,
        session: Session,
        student_training: RealTrainingStudent,
        training: RealTraining
    ) -> Dict[str, Any]:
        """
        Обработка одного студента на тренировке
        """
        student = student_training.student
        result = {
            "student_id": student.id,
            "training_id": training.id,
            "action": None,
            "details": None,
            "error": None
        }

        try:
            if student_training.status == AttendanceStatus.CANCELLED_SAFE:
                result["action"] = "skip_safe_cancellation"
                result["details"] = "Безопасная отмена - пропускаем"
                return result

            if self._check_existing_invoice(session, student.id, training.id):
                result["action"] = "skip_existing_invoice"
                result["details"] = "Инвойс уже существует"
                return result

            active_subscription = self._get_active_subscription(session, student.id, training.training_date)

            if active_subscription:
                active_subscription.sessions_left -= 1
                session.flush()
                
                result["action"] = "deduct_session"
                result["details"] = f"Списано занятие с абонемента (осталось: {active_subscription.sessions_left})"
                
            else:
                training_cost = training.training_type.price if training.training_type.is_subscription_only else 0
                
                if training_cost > 0:
                    invoice_data = InvoiceCreate(
                        client_id=student.client_id,
                        student_id=student.id,
                        training_id=training.id,
                        type=InvoiceType.TRAINING,
                        amount=training_cost,
                        description=f"Тренировка: {training.training_type.name} от {training.training_date.strftime('%d.%m.%Y')} {training.start_time.strftime('%H:%M')}",
                        status=InvoiceStatus.UNPAID,
                        is_auto_renewal=False
                    )
                    
                    # Delegate to InvoiceService
                    self.financial_service.create_standalone_invoice(invoice_data, auto_pay=True)
                    
                    result["action"] = "create_invoice"
                    result["details"] = f"Создан инвойс на сумму {training_cost}р"
                else:
                    result["action"] = "skip_free_training"
                    result["details"] = "Бесплатная тренировка - инвойс не нужен"

        except Exception as e:
            logger.error(f"Ошибка обработки студента {student.id} на тренировке {training.id}: {str(e)}")
            result["error"] = str(e)

        return result

    def _process_training(self, session: Session, training: RealTraining) -> Dict[str, Any]:
        """
        Обработка одной тренировки
        """
        result = {
            "training_id": training.id,
            "training_date": training.training_date,
            "start_time": training.start_time,
            "students_processed": 0,
            "sessions_deducted": 0,
            "invoices_created": 0,
            "errors": 0,
            "student_results": []
        }

        student_trainings = (
            session.query(RealTrainingStudent)
            .filter(RealTrainingStudent.real_training_id == training.id)
            .all()
        )

        for student_training in student_trainings:
            student_result = self._process_student_training(session, student_training, training)
            result["student_results"].append(student_result)
            result["students_processed"] += 1

            if student_result["error"]:
                result["errors"] += 1
            elif student_result["action"] == "deduct_session":
                result["sessions_deducted"] += 1
            elif student_result["action"] == "create_invoice":
                result["invoices_created"] += 1

        training.processed_at = datetime.now(timezone.utc)
        session.flush()

        return result