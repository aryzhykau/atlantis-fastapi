from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload, selectinload
import logging
from datetime import timezone

from app.models import (
    RealTraining,
    RealTrainingStudent,
    TrainingTemplate,
    TrainingStudentTemplate,
    User,
    TrainingType,
    Student,
    StudentSubscription,
    Invoice,
    InvoiceType,
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

logger = logging.getLogger(__name__)


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


def add_student_to_training_db(
    db: Session,
    training_id: int,
    student_data: RealTrainingStudentCreate,
) -> RealTrainingStudent:
    """
    Простое добавление студента на тренировку в БД.
    Предполагается, что все бизнес-проверки уже выполнены в сервисном слое.
    """
    from app.models.real_training import AttendanceStatus
    
    db_student = RealTrainingStudent(
        real_training_id=training_id,
        student_id=student_data.student_id,
        template_student_id=student_data.template_student_id,
        status=AttendanceStatus.PRESENT  # По умолчанию - присутствовал
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student


def get_real_training_student(
    db: Session, training_id: int, student_id: int
) -> Optional[RealTrainingStudent]:
    return db.query(RealTrainingStudent).filter(
        RealTrainingStudent.real_training_id == training_id,
        RealTrainingStudent.student_id == student_id
    ).first()


def update_student_attendance_db(
    db: Session,
    db_student: RealTrainingStudent,
    update_dict: dict,
    marker_id: int,
) -> RealTrainingStudent:
    """
    Простое обновление статуса посещения в БД.
    Предполагается, что все бизнес-проверки уже выполнены в сервисном слое.
    """
    if "status" in update_dict:
        update_dict["attendance_marked_at"] = datetime.utcnow()
        update_dict["attendance_marked_by_id"] = marker_id

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
    
    # Получаем все шаблоны с активными тренерами и типами тренировок
    templates = db.query(TrainingTemplate).join(
        User, TrainingTemplate.responsible_trainer_id == User.id
    ).join(
        TrainingType, TrainingTemplate.training_type_id == TrainingType.id
    ).options(
        selectinload(TrainingTemplate.training_type)
    ).filter(
        and_(
            User.is_active.is_(True),
            TrainingType.is_active.is_(True)
        )
    ).all()
    
    created_trainings_details = []
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
            if not template.training_type:
                logger.error(f"Skipping template ID {template.id} due to missing training_type.")
                continue

            max_participants = template.training_type.max_participants

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
            
            # Копируем студентов из шаблона, учитывая start_date и max_participants
            template_students_query = db.query(TrainingStudentTemplate).options(
                joinedload(TrainingStudentTemplate.student)
            ).filter(
                and_(
                    TrainingStudentTemplate.training_template_id == template.id,
                    TrainingStudentTemplate.is_frozen.is_(False),
                    TrainingStudentTemplate.start_date <= template_date
                )
            ).order_by(
                TrainingStudentTemplate.start_date.asc(),
                TrainingStudentTemplate.id.asc()
            )
            
            potential_students = template_students_query.all()
            
            added_students_count = 0
            for template_student in potential_students:
                if added_students_count >= max_participants:
                    logger.warning(
                        f"Student ID {template_student.student_id} from template_student_id {template_student.id} "
                        f"was not added to RealTraining ID {new_training.id} (date: {new_training.training_date}) "
                        f"for Template ID {template.id} because max_participants ({max_participants}) was reached."
                    )
                    continue

                can_add_student = False
                if not template.training_type.is_subscription_only:
                    can_add_student = True
                else:
                    # Ищем активный абонемент у студента на дату будущей тренировки
                    active_subscription = db.query(StudentSubscription).filter(
                        StudentSubscription.student_id == template_student.student_id,
                        StudentSubscription.status == 'active',
                        StudentSubscription.start_date <= template_date,
                        StudentSubscription.end_date >= template_date,
                    ).first()

                    if active_subscription and (active_subscription.sessions_left > 0 or active_subscription.is_auto_renew):
                        can_add_student = True
                    else:
                         logger.warning(
                            f"Student ID {template_student.student_id} was not added to RealTraining ID {new_training.id} "
                            f"for Template ID {template.id}. Reason: No active subscription with sessions left or auto-renew enabled."
                        )

                if can_add_student:
                    student_training = RealTrainingStudent(
                        real_training_id=new_training.id,
                        student_id=template_student.student_id,
                        template_student_id=template_student.id,
                        status=AttendanceStatus.PRESENT  # По умолчанию - присутствовал
                    )
                    db.add(student_training)
                    added_students_count += 1
            
            created_trainings_details.append(new_training)
            created_count += 1
    
    if created_count > 0:
        db.commit()
    
    return created_count, created_trainings_details 


def mark_attendance(
    db: Session,
    training_id: int,
    student_id: int,
    attendance_status: str,
    marked_by_id: int
) -> Optional[RealTrainingStudent]:
    """
    Отметка посещаемости студента на тренировке
    """
    training_student = get_real_training_student(db, training_id, student_id)
    if not training_student:
        return None

    training_student.attendance_status = attendance_status
    training_student.attendance_marked_by_id = marked_by_id
    training_student.attendance_marked_at = datetime.now(timezone.utc)
    # НЕ делаем commit здесь - это делает сервис
    db.flush()  # Обновляем объект, но не коммитим
    db.refresh(training_student)
    return training_student 