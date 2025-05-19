from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.models import (
    RealTraining,
    RealTrainingStudent,
    TrainingTemplate,
    TrainingStudentTemplate,
    User,
    TrainingType,
    Student,
)
from app.models.real_training import SAFE_CANCELLATION_HOURS, AttendanceStatus
from app.schemas.real_training import (
    RealTrainingCreate,
    RealTrainingUpdate,
)
from app.schemas.real_training_student import (
    RealTrainingStudentCreate,
    RealTrainingStudentUpdate,
)


def get_real_trainings_with_students(
    db: Session,
    *,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    trainer_id: Optional[int] = None,
    training_type_id: Optional[int] = None,
    include_cancelled: bool = False,
) -> List[RealTraining]:
    """
    Получение списка реальных тренировок с привязанными студентами за период
    Использует joinedload для оптимизации запросов к БД
    """
    query = db.query(RealTraining).options(
        joinedload(RealTraining.students),
        joinedload(RealTraining.training_type),
        joinedload(RealTraining.trainer),
    )

    if start_date:
        query = query.filter(RealTraining.training_date >= start_date)
    if end_date:
        query = query.filter(RealTraining.training_date <= end_date)
    if trainer_id:
        query = query.filter(RealTraining.responsible_trainer_id == trainer_id)
    if training_type_id:
        query = query.filter(RealTraining.training_type_id == training_type_id)
    if not include_cancelled:
        query = query.filter(RealTraining.cancelled_at.is_(None))

    return query.order_by(RealTraining.training_date, RealTraining.start_time).all()


# Операции с реальными тренировками

def get_real_trainings(
    db: Session,
    *,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    trainer_id: Optional[int] = None,
    training_type_id: Optional[int] = None,
    include_cancelled: bool = False,
) -> List[RealTraining]:
    """
    Получение списка реальных тренировок с фильтрами
    """
    query = db.query(RealTraining)

    if start_date:
        query = query.filter(RealTraining.training_date >= start_date)
    if end_date:
        query = query.filter(RealTraining.training_date <= end_date)
    if trainer_id:
        query = query.filter(RealTraining.responsible_trainer_id == trainer_id)
    if training_type_id:
        query = query.filter(RealTraining.training_type_id == training_type_id)
    if not include_cancelled:
        query = query.filter(RealTraining.cancelled_at.is_(None))

    return query.order_by(RealTraining.training_date, RealTraining.start_time).all()


def get_real_training(db: Session, training_id: int) -> Optional[RealTraining]:
    """
    Получение тренировки по ID
    """
    return db.query(RealTraining).filter(RealTraining.id == training_id).first()


def get_real_trainings_by_date(db: Session, date: date) -> List[RealTraining]:
    """
    Получение всех тренировок на конкретную дату
    """
    return db.query(RealTraining).filter(RealTraining.training_date == date).order_by(RealTraining.start_time).all()


def create_real_training(
    db: Session, training_data: RealTrainingCreate
) -> RealTraining:
    """
    Создание новой тренировки
    """
    db_training = RealTraining(
        training_date=training_data.training_date,
        start_time=training_data.start_time,
        responsible_trainer_id=training_data.responsible_trainer_id,
        training_type_id=training_data.training_type_id,
        template_id=training_data.template_id,
        is_template_based=bool(training_data.template_id),
    )
    db.add(db_training)
    db.commit()
    db.refresh(db_training)
    
    # Загружаем связанные объекты
    db.refresh(db_training)
    return db.query(RealTraining).options(
        joinedload(RealTraining.trainer),
        joinedload(RealTraining.training_type),
    ).filter(RealTraining.id == db_training.id).first()


def update_real_training(
    db: Session, training_id: int, update_data: RealTrainingUpdate
) -> Optional[RealTraining]:
    """
    Обновление тренировки
    """
    db_training = get_real_training(db, training_id)
    if not db_training:
        return None

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(db_training, field, value)

    db.commit()
    db.refresh(db_training)
    return db_training


def delete_real_training(db: Session, training_id: int) -> bool:
    """
    Удаление тренировки
    """
    db_training = get_real_training(db, training_id)
    if not db_training:
        return False

    db.delete(db_training)
    db.commit()
    return True


# Операции со студентами на тренировках

def get_real_training_students(
    db: Session, training_id: int
) -> List[RealTrainingStudent]:
    """
    Получение списка студентов на тренировке
    """
    return db.query(RealTrainingStudent).filter(
        RealTrainingStudent.real_training_id == training_id
    ).all()


def get_student_real_trainings(
    db: Session,
    student_id: int,
    *,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[RealTrainingStudent]:
    """
    Получение истории тренировок студента
    """
    query = db.query(RealTrainingStudent).join(RealTraining).filter(
        RealTrainingStudent.student_id == student_id
    )

    if start_date:
        query = query.filter(RealTraining.training_date >= start_date)
    if end_date:
        query = query.filter(RealTraining.training_date <= end_date)

    return query.order_by(RealTraining.training_date, RealTraining.start_time).all()


def add_student_to_training(
    db: Session,
    training_id: int,
    student_data: RealTrainingStudentCreate,
) -> Optional[RealTrainingStudent]:
    """
    Добавление студента на тренировку
    """
    # Проверяем активность студента
    student = db.query(Student).filter(Student.id == student_data.student_id).first()
    if not student or not student.is_active:
        raise ValueError("Cannot add inactive student to training")

    db_student = RealTrainingStudent(
        real_training_id=training_id,
        student_id=student_data.student_id,
        template_student_id=student_data.template_student_id,
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student


def update_student_attendance(
    db: Session,
    training_id: int,
    student_id: int,
    update_data: RealTrainingStudentUpdate,
    trainer_id: int,
) -> Optional[RealTrainingStudent]:
    """
    Обновление статуса посещения или отмена записи студента
    """
    db_student = db.query(RealTrainingStudent).filter(
        and_(
            RealTrainingStudent.real_training_id == training_id,
            RealTrainingStudent.student_id == student_id,
        )
    ).first()
    if not db_student:
        return None

    # Получаем тренировку для проверки времени отмены
    db_training = get_real_training(db, training_id)
    if not db_training:
        return None

    update_dict = update_data.model_dump(exclude_unset=True)

    # Если устанавливается статус
    if update_data.status:
        update_dict["attendance_marked_at"] = datetime.utcnow()
        update_dict["attendance_marked_by_id"] = trainer_id

        # Если отмена, проверяем необходимость оплаты
        if update_data.status == AttendanceStatus.CANCELLED:
            # Используем фиксированное значение для безопасной отмены
            # Если указано время уведомления, используем его
            notification_time = update_data.notification_time or datetime.utcnow()
            training_datetime = datetime.combine(db_training.training_date, db_training.start_time)
            
            # Если отмена произошла позже безопасного периода
            hours_before = (training_datetime - notification_time).total_seconds() / 3600
            update_dict["requires_payment"] = hours_before < SAFE_CANCELLATION_HOURS

    for field, value in update_dict.items():
        setattr(db_student, field, value)

    db.commit()
    db.refresh(db_student)
    return db_student


def remove_student_from_training(
    db: Session, training_id: int, student_id: int
) -> bool:
    """
    Удаление студента с тренировки
    """
    db_student = db.query(RealTrainingStudent).filter(
        and_(
            RealTrainingStudent.real_training_id == training_id,
            RealTrainingStudent.student_id == student_id,
        )
    ).first()
    if not db_student:
        return False

    db.delete(db_student)
    db.commit()
    return True


def generate_next_week_trainings(db: Session) -> Tuple[int, List[RealTraining]]:
    """
    Генерирует тренировки на следующую неделю на основе шаблонов.
    Возвращает кортеж: (количество созданных тренировок, список созданных тренировок)
    """
    # Получаем даты следующей недели
    today = date.today()
    next_monday = today + timedelta(days=(7 - today.weekday()))
    next_sunday = next_monday + timedelta(days=6)
    
    # Получаем все шаблоны с активными тренерами и типами тренировок
    templates = db.query(TrainingTemplate).join(
        TrainingTemplate.responsible_trainer
    ).join(
        TrainingTemplate.training_type
    ).filter(
        and_(
            User.is_active.is_(True),
            TrainingType.is_active.is_(True)
        )
    ).all()
    
    created_trainings = []
    created_count = 0
    
    for template in templates:
        # Определяем дату следующей тренировки по этому шаблону
        template_date = next_monday + timedelta(days=template.day_number - 1)
        
        # Проверяем, не создана ли уже тренировка по этому шаблону
        existing_training = db.query(RealTraining).filter(
            and_(
                RealTraining.template_id == template.id,
                RealTraining.training_date == template_date
            )
        ).first()
        
        if not existing_training:
            # Создаем новую тренировку
            new_training = RealTraining(
                training_date=template_date,
                start_time=template.start_time,
                responsible_trainer_id=template.responsible_trainer_id,
                training_type_id=template.training_type_id,
                template_id=template.id,
                is_template_based=True
            )
            db.add(new_training)
            db.flush()  # Получаем ID новой тренировки
            
            # Копируем студентов из шаблона
            template_students = db.query(TrainingStudentTemplate).filter(
                and_(
                    TrainingStudentTemplate.training_template_id == template.id,
                    TrainingStudentTemplate.is_frozen.is_(False)
                )
            ).all()
            
            for template_student in template_students:
                student_training = RealTrainingStudent(
                    real_training_id=new_training.id,
                    student_id=template_student.student_id,
                    template_student_id=template_student.id
                )
                db.add(student_training)
            
            created_trainings.append(new_training)
            created_count += 1
    
    if created_count > 0:
        db.commit()
    
    return created_count, created_trainings 