import logging
from datetime import datetime, timedelta, date, timezone
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import (
    RealTraining,
    RealTrainingStudent,
    StudentSubscription,
    Invoice,
    InvoiceStatus,
    InvoiceType,
    User,
    UserRole
)
from app.models.real_training import AttendanceStatus
from app.schemas.invoice import InvoiceCreate
from app.utils.financial_processor import create_and_pay_invoice

logger = logging.getLogger(__name__)


class TrainingProcessingService:
    def __init__(self, db: Session):
        self.db = db

    def validate_admin(self, user_id: int) -> None:
        """Проверка, что пользователь является админом"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=403,
                detail="Only admins can process trainings"
            )

    def get_tomorrow_trainings(self) -> List[RealTraining]:
        """Получение тренировок на завтра"""
        tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
        return (
            self.db.query(RealTraining)
            .filter(
                and_(
                    RealTraining.training_date == tomorrow,
                    RealTraining.processed_at.is_(None)
                )
            )
            .all()
        )

    def get_active_subscription(self, student_id: int, training_date: date) -> Optional[StudentSubscription]:
        """Получение активного абонемента студента на дату тренировки"""
        return (
            self.db.query(StudentSubscription)
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

    def check_existing_invoice(self, student_id: int, training_id: int) -> bool:
        """Проверка существования инвойса за тренировку"""
        return (
            self.db.query(Invoice)
            .filter(
                and_(
                    Invoice.student_id == student_id,
                    Invoice.training_id == training_id,
                    Invoice.status != InvoiceStatus.CANCELLED
                )
            )
            .first() is not None
        )

    def process_student_training(
        self,
        student_training: RealTrainingStudent,
        training: RealTraining
    ) -> Dict[str, Any]:
        """
        Обработка одного студента на тренировке
        
        Returns:
            Dict с результатом обработки
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
            # Проверяем статус отмены
            if student_training.status == AttendanceStatus.CANCELLED_SAFE:
                result["action"] = "skip_safe_cancellation"
                result["details"] = "Безопасная отмена - пропускаем"
                return result

            # Проверяем, есть ли уже инвойс
            if self.check_existing_invoice(student.id, training.id):
                result["action"] = "skip_existing_invoice"
                result["details"] = "Инвойс уже существует"
                return result

            # Получаем активный абонемент
            active_subscription = self.get_active_subscription(student.id, training.training_date)

            if active_subscription:
                # Есть активный абонемент - списываем занятие
                active_subscription.sessions_left -= 1
                self.db.flush()
                
                result["action"] = "deduct_session"
                result["details"] = f"Списано занятие с абонемента (осталось: {active_subscription.sessions_left})"
                
            else:
                # Нет активного абонемента - создаем инвойс
                # Определяем стоимость тренировки
                training_cost = training.training_type.price if training.training_type.is_subscription_only else 0
                
                if training_cost > 0:
                    # Создаем инвойс за тренировку через FinancialProcessor
                    invoice_data = InvoiceCreate(
                        client_id=student.client_id,
                        student_id=student.id,
                        training_id=training.id,
                        type=InvoiceType.TRAINING,
                        amount=training_cost,
                        description=f"Тренировка: {training.training_type.name} от {training.training_date.strftime('%d.%m.%Y')} {training.start_time.strftime('%H:%M')}",
                        status=InvoiceStatus.UNPAID,  # FinancialProcessor сам определит статус на основе баланса
                        is_auto_renewal=False
                    )
                    
                    invoice = create_and_pay_invoice(self.db, invoice_data, auto_pay=True)
                    
                    result["action"] = "create_invoice"
                    result["details"] = f"Создан инвойс на сумму {training_cost}р"
                else:
                    # Тренировка бесплатная
                    result["action"] = "skip_free_training"
                    result["details"] = "Бесплатная тренировка - инвойс не нужен"

        except Exception as e:
            logger.error(f"Ошибка обработки студента {student.id} на тренировке {training.id}: {str(e)}")
            result["error"] = str(e)

        return result

    def process_training(self, training: RealTraining) -> Dict[str, Any]:
        """
        Обработка одной тренировки
        
        Returns:
            Dict с результатами обработки всех студентов
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

        # Получаем всех студентов на тренировке
        student_trainings = (
            self.db.query(RealTrainingStudent)
            .filter(RealTrainingStudent.real_training_id == training.id)
            .all()
        )

        for student_training in student_trainings:
            student_result = self.process_student_training(student_training, training)
            result["student_results"].append(student_result)
            result["students_processed"] += 1

            if student_result["error"]:
                result["errors"] += 1
            elif student_result["action"] == "deduct_session":
                result["sessions_deducted"] += 1
            elif student_result["action"] == "create_invoice":
                result["invoices_created"] += 1

        # Устанавливаем флаг что тренировка была обработана
        training.processed_at = datetime.now(timezone.utc)
        self.db.flush()

        return result

    def process_tomorrow_trainings(self, admin_id: int) -> Dict[str, Any]:
        """
        Основной метод для обработки всех тренировок на завтра
        
        Args:
            admin_id: ID администратора, запустившего процесс
            
        Returns:
            Dict с общими результатами обработки
        """
        # Проверяем права
        self.validate_admin(admin_id)

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

        try:
            # Получаем тренировки на завтра
            tomorrow_trainings = self.get_tomorrow_trainings()
            
            if not tomorrow_trainings:
                overall_result["message"] = "Нет тренировок на завтра для обработки"
                return overall_result

            # Обрабатываем каждую тренировку
            for training in tomorrow_trainings:
                training_result = self.process_training(training)
                overall_result["training_results"].append(training_result)
                overall_result["trainings_processed"] += 1
                overall_result["total_students_processed"] += training_result["students_processed"]
                overall_result["total_sessions_deducted"] += training_result["sessions_deducted"]
                overall_result["total_invoices_created"] += training_result["invoices_created"]
                overall_result["total_errors"] += training_result["errors"]

            # Коммитим все изменения
            self.db.commit()

            overall_result["message"] = "Обработка завершена успешно"
            logger.info(f"Обработано {overall_result['trainings_processed']} тренировок, "
                       f"создано {overall_result['total_invoices_created']} инвойсов, "
                       f"списано {overall_result['total_sessions_deducted']} занятий")

        except Exception as e:
            self.db.rollback()
            overall_result["error"] = str(e)
            overall_result["message"] = "Ошибка при обработке тренировок"
            logger.error(f"Ошибка обработки тренировок: {str(e)}")

        return overall_result 