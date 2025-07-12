from datetime import date
from typing import List, Optional
from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from app.models import RealTraining, RealTrainingStudent
from app.schemas.real_training import RealTrainingCreate, RealTrainingUpdate
from app.schemas.real_training_student import RealTrainingStudentCreate, RealTrainingStudentUpdate


# =============================================================================
# ПРОСТЫЕ CRUD ОПЕРАЦИИ С ТРЕНИРОВКАМИ
# =============================================================================

def get_training(db: Session, training_id: int) -> Optional[RealTraining]:
    """
    Получение тренировки по ID
    """
    return db.query(RealTraining).filter(RealTraining.id == training_id).first()


def get_training_with_relations(db: Session, training_id: int) -> Optional[RealTraining]:
    """
    Получение тренировки с загруженными связанными объектами
    """
    return db.query(RealTraining).options(
        joinedload(RealTraining.trainer),
        joinedload(RealTraining.training_type),
        joinedload(RealTraining.students),
    ).filter(RealTraining.id == training_id).first()


def get_trainings(
    db: Session,
    *,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    trainer_id: Optional[int] = None,
    training_type_id: Optional[int] = None,
    include_cancelled: bool = False,
) -> List[RealTraining]:
    """
    Получение списка тренировок с фильтрами
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


def get_trainings_with_students(
    db: Session,
    *,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    trainer_id: Optional[int] = None,
    training_type_id: Optional[int] = None,
    include_cancelled: bool = False,
) -> List[RealTraining]:
    """
    Получение списка тренировок с привязанными студентами
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


def get_trainings_by_date(db: Session, training_date: date) -> List[RealTraining]:
    """
    Получение всех тренировок на конкретную дату
    """
    return db.query(RealTraining).filter(
        RealTraining.training_date == training_date
    ).order_by(RealTraining.start_time).all()


def create_training(db: Session, training_data: RealTrainingCreate) -> RealTraining:
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
    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Получаем ID, но не коммитим
    db.refresh(db_training)
    
    return get_training_with_relations(db, db_training.id)


def update_training(
    db: Session, 
    training_id: int, 
    update_data: RealTrainingUpdate
) -> Optional[RealTraining]:
    """
    Обновление тренировки
    """
    db_training = get_training(db, training_id)
    if not db_training:
        return None

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(db_training, field, value)

    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Обновляем объект, но не коммитим
    db.refresh(db_training)
    return db_training


def delete_training(db: Session, training_id: int) -> bool:
    """
    Удаление тренировки
    """
    db_training = get_training(db, training_id)
    if not db_training:
        return False

    db.delete(db_training)
    # НЕ делаем commit здесь - это делает сервис
    return True


# =============================================================================
# ПРОСТЫЕ CRUD ОПЕРАЦИИ СО СТУДЕНТАМИ НА ТРЕНИРОВКАХ
# =============================================================================

def get_training_students(db: Session, training_id: int) -> List[RealTrainingStudent]:
    """
    Получение списка студентов на тренировке
    """
    return db.query(RealTrainingStudent).filter(
        RealTrainingStudent.real_training_id == training_id
    ).all()


def get_training_student(
    db: Session, 
    training_id: int, 
    student_id: int
) -> Optional[RealTrainingStudent]:
    """
    Получение записи студента на тренировку
    """
    return db.query(RealTrainingStudent).filter(
        and_(
            RealTrainingStudent.real_training_id == training_id,
            RealTrainingStudent.student_id == student_id
        )
    ).first()


def get_student_trainings(
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
) -> RealTrainingStudent:
    """
    Добавление студента на тренировку
    """
    student_training = RealTrainingStudent(
        real_training_id=training_id,
        student_id=student_data.student_id,
        status=student_data.status,
        template_student_id=student_data.template_student_id,
    )
    db.add(student_training)
    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Получаем ID, но не коммитим
    db.refresh(student_training)
    return student_training


def update_student_attendance(
    db: Session,
    training_id: int,
    student_id: int,
    update_data: RealTrainingStudentUpdate,
) -> Optional[RealTrainingStudent]:
    """
    Обновление статуса посещаемости студента
    """
    student_training = get_training_student(db, training_id, student_id)
    if not student_training:
        return None

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(student_training, field, value)

    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Обновляем объект, но не коммитим
    db.refresh(student_training)
    return student_training


def remove_student_from_training(
    db: Session, 
    training_id: int, 
    student_id: int
) -> bool:
    """
    Удаление студента с тренировки
    """
    student_training = get_training_student(db, training_id, student_id)
    if not student_training:
        return False

    db.delete(student_training)
    # НЕ делаем commit здесь - это делает сервис
    return True


def get_training_student_count(db: Session, training_id: int) -> int:
    """
    Получение количества студентов на тренировке
    """
    return db.query(RealTrainingStudent).filter(
        RealTrainingStudent.real_training_id == training_id
    ).count()


def is_student_on_training(db: Session, training_id: int, student_id: int) -> bool:
    """
    Проверка, записан ли студент на тренировку
    """
    return get_training_student(db, training_id, student_id) is not None 