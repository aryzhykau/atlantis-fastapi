from datetime import date, datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models import RealTraining, RealTrainingStudent, AttendanceStatus
from app.crud import training as training_crud
from app.crud import subscription as subscription_crud
from app.crud import invoice as invoice_crud
from app.validators import training_validators as training_validators
from app.validators import subscription_validators as subscription_validators
from app.validators import financial_validators as financial_validators
from app.schemas.real_training_student import RealTrainingStudentCreate, RealTrainingStudentUpdate


class TrainingService:
    """
    Сервис для работы с тренировками
    Использует CRUD операции и валидаторы для выполнения бизнес-логики
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_training_with_students(self, training_id: int) -> Optional[RealTraining]:
        """
        Получение тренировки с привязанными студентами
        """
        return training_crud.get_training_with_relations(self.db, training_id)
    
    def get_trainings_by_date(self, training_date: date) -> List[RealTraining]:
        """
        Получение всех тренировок на конкретную дату
        """
        return training_crud.get_trainings_by_date(self.db, training_date)
    
    def get_trainings_with_filters(
        self,
        *,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        trainer_id: Optional[int] = None,
        training_type_id: Optional[int] = None,
        include_cancelled: bool = False,
    ) -> List[RealTraining]:
        """
        Получение тренировок с фильтрами
        """
        return training_crud.get_trainings_with_students(
            self.db,
            start_date=start_date,
            end_date=end_date,
            trainer_id=trainer_id,
            training_type_id=training_type_id,
            include_cancelled=include_cancelled,
        )
    
    def add_student_to_training(
        self,
        training_id: int,
        student_id: int,
        status: str = AttendanceStatus.PRESENT.value,
        template_student_id: Optional[int] = None,
    ) -> Tuple[bool, str, Optional[RealTrainingStudent]]:
        """
        Добавление студента на тренировку
        
        Returns:
            (success, message, student_training)
        """
        # Валидация
        is_valid, error_message = training_validators.validate_training_for_student_registration(
            self.db, training_id, student_id
        )
        if not is_valid:
            return False, error_message, None
        
        # Проверяем доступность абонемента
        training = training_crud.get_training(self.db, training_id)
        is_subscription_valid, subscription_error, student_subscription = (
            subscription_validators.validate_subscription_for_training(
                self.db, student_id, training.training_date
            )
        )
        if not is_subscription_valid:
            return False, subscription_error, None
        
        # Создаём запись студента на тренировку
        student_data = RealTrainingStudentCreate(
            student_id=student_id,
            status=status,
            template_student_id=template_student_id,
        )
        
        with self.db.begin():
            # Добавляем студента на тренировку
            student_training = training_crud.add_student_to_training(
                self.db, training_id, student_data
            )
            
            # Списываем занятие с абонемента
            subscription_crud.deduct_session(self.db, student_subscription.id)
            
            return True, "Студент успешно добавлен на тренировку", student_training
    
    def remove_student_from_training(
        self,
        training_id: int,
        student_id: int,
        is_safe_cancellation: bool = True,
    ) -> Tuple[bool, str]:
        """
        Удаление студента с тренировки
        
        Args:
            training_id: ID тренировки
            student_id: ID студента
            is_safe_cancellation: Безопасная отмена (возврат занятия в абонемент)
        
        Returns:
            (success, message)
        """
        # Валидация
        is_valid, error_message, is_safe = training_validators.validate_training_for_student_cancellation(
            self.db, training_id, student_id
        )
        if not is_valid:
            return False, error_message
        
        # Получаем запись студента на тренировку
        student_training = training_crud.get_training_student(self.db, training_id, student_id)
        
        with self.db.begin():
            # Удаляем студента с тренировки
            success = training_crud.remove_student_from_training(self.db, training_id, student_id)
            if not success:
                return False, "Ошибка при удалении студента с тренировки"
            
            # Если это безопасная отмена, возвращаем занятие в абонемент
            if is_safe_cancellation and is_safe:
                # Находим активный абонемент студента
                training = training_crud.get_training(self.db, training_id)
                student_subscription = subscription_crud.get_active_subscription(
                    self.db, student_id, training.training_date
                )
                
                if student_subscription:
                    subscription_crud.add_session(self.db, student_subscription.id)
            
            return True, "Студент успешно удалён с тренировки"
    
    def update_student_attendance(
        self,
        training_id: int,
        student_id: int,
        new_status: str,
    ) -> Tuple[bool, str, Optional[RealTrainingStudent]]:
        """
        Обновление статуса посещаемости студента
        
        Returns:
            (success, message, student_training)
        """
        # Валидация
        is_valid, error_message = training_validators.validate_training_for_attendance_update(
            self.db, training_id, student_id, new_status
        )
        if not is_valid:
            return False, error_message, None
        
        # Обновляем статус
        update_data = RealTrainingStudentUpdate(status=new_status)
        
        with self.db.begin():
            student_training = training_crud.update_student_attendance(
                self.db, training_id, student_id, update_data
            )
            
            if student_training:
                return True, "Статус посещаемости обновлён", student_training
            else:
                return False, "Ошибка при обновлении статуса", None
    
    def cancel_training(
        self,
        training_id: int,
        cancelled_by_id: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """
        Отмена тренировки
        
        Returns:
            (success, message)
        """
        # Проверяем существование тренировки
        training = training_validators.validate_training_exists(self.db, training_id)
        if not training:
            return False, "Тренировка не найдена"
        
        # Проверяем, что тренировка не отменена
        if not training_validators.validate_training_not_cancelled(training):
            return False, "Тренировка уже отменена"
        
        with self.db.begin():
            # Отменяем тренировку
            training.cancelled_at = datetime.now(timezone.utc)
            training.cancelled_by_id = cancelled_by_id
            
            # Возвращаем занятия всем студентам
            students = training_crud.get_training_students(self.db, training_id)
            for student_training in students:
                # Находим активный абонемент студента
                student_subscription = subscription_crud.get_active_subscription(
                    self.db, student_training.student_id, training.training_date
                )
                
                if student_subscription:
                    subscription_crud.add_session(self.db, student_subscription.id)
            
            # Отменяем все инвойсы за эту тренировку
            for student_training in students:
                invoice = invoice_crud.get_training_invoice(
                    self.db, training_id, student_training.student_id
                )
                if invoice:
                    invoice_crud.cancel_invoice(self.db, invoice.id, cancelled_by_id)
            
            return True, "Тренировка успешно отменена"
    
    def get_training_attendance_summary(self, training_id: int) -> dict:
        """
        Получение сводки по посещаемости тренировки
        
        Returns:
            Словарь со статистикой посещаемости
        """
        training = training_crud.get_training_with_relations(self.db, training_id)
        if not training:
            return {}
        
        students = training_crud.get_training_students(self.db, training_id)
        
        attendance_stats = {
            'total_students': len(students),
            'present': 0,
            'absent': 0,
            'cancelled': 0,
            'unknown': 0,
        }
        
        for student in students:
            status = student.status
            if status == AttendanceStatus.PRESENT.value:
                attendance_stats['present'] += 1
            elif status == AttendanceStatus.ABSENT.value:
                attendance_stats['absent'] += 1
            elif status == AttendanceStatus.CANCELLED.value:
                attendance_stats['cancelled'] += 1
            else:
                attendance_stats['unknown'] += 1
        
        return attendance_stats
    
    def auto_mark_attendance(self, training_id: int) -> Tuple[bool, str]:
        """
        Автоматическая отметка посещаемости (все студенты как присутствующие)
        
        Returns:
            (success, message)
        """
        training = training_crud.get_training(self.db, training_id)
        if not training:
            return False, "Тренировка не найдена"
        
        # Проверяем, что тренировка прошла
        if training_validators.validate_training_date_not_passed(training):
            return False, "Тренировка ещё не прошла"
        
        students = training_crud.get_training_students(self.db, training_id)
        
        with self.db.begin():
            for student in students:
                if student.status == AttendanceStatus.UNKNOWN.value:
                    update_data = RealTrainingStudentUpdate(status=AttendanceStatus.PRESENT.value)
                    training_crud.update_student_attendance(
                        self.db, training_id, student.student_id, update_data
                    )
            
            return True, f"Автоматически отмечено {len(students)} студентов как присутствующие"
    
    def get_student_training_history(
        self,
        student_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[RealTrainingStudent]:
        """
        Получение истории тренировок студента
        
        Returns:
            Список записей студента на тренировки
        """
        return training_crud.get_student_trainings(
            self.db, student_id, start_date=start_date, end_date=end_date
        ) 