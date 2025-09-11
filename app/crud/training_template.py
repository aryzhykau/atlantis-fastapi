from sqlalchemy.orm import Session, joinedload, selectinload
from fastapi import HTTPException
from app.models import TrainingTemplate, TrainingStudentTemplate, TrainingType
from app.schemas.training_template import (
    TrainingTemplateCreate,
    TrainingTemplateUpdate,
    TrainingStudentTemplateCreate,
    TrainingStudentTemplateUpdate,
)
from datetime import date



# Получение списка всех тренировочных шаблонов с опциональной фильтрацией по дню
def get_training_templates(db: Session, day_number: int = None):
    # By default return only non-deleted templates
    query = db.query(TrainingTemplate).filter(TrainingTemplate.is_deleted == False)
    
    if day_number is not None:
        query = query.filter(TrainingTemplate.day_number == day_number)
    
    return query.order_by(TrainingTemplate.day_number, TrainingTemplate.start_time).all()


# Получение тренировочного шаблона по ID
def get_training_template_by_id(db: Session, template_id: int):
    # Exclude soft-deleted templates from normal lookup
    return db.query(TrainingTemplate).filter(TrainingTemplate.id == template_id, TrainingTemplate.is_deleted == False).first()


# Создание нового тренировочного шаблона
def create_training_template(db: Session, training_template: TrainingTemplateCreate):
    # Проверяем, нет ли уже шаблона для этого тренера в это время в этот день
    existing_template = db.query(TrainingTemplate).filter(
        TrainingTemplate.day_number == training_template.day_number,
        TrainingTemplate.start_time == training_template.start_time,
        TrainingTemplate.responsible_trainer_id == training_template.responsible_trainer_id
    ).first()
    
    if existing_template:
        raise HTTPException(
            status_code=400,
            detail=f"Trainer conflict: Trainer with ID {training_template.responsible_trainer_id} already has a training scheduled for day {training_template.day_number} at {training_template.start_time}. A trainer cannot be in two places at the same time."
        )
    
    db_template = TrainingTemplate(
        day_number=training_template.day_number,
        start_time=training_template.start_time,
        responsible_trainer_id=training_template.responsible_trainer_id,
        training_type_id=training_template.training_type_id,
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


# Обновление тренировочного шаблона
def update_training_template(db: Session, template_id: int, update_data: TrainingTemplateUpdate):
    db_template = get_training_template_by_id(db, template_id)
    if not db_template:
        return None
    
    update_dict = update_data.model_dump(exclude_unset=True)
    
    # Если обновляется день, время или тренер, проверяем конфликты
    if any(field in update_dict for field in ['day_number', 'start_time', 'responsible_trainer_id']):
        # Получаем финальные значения после обновления
        final_day = update_dict.get('day_number', db_template.day_number)
        final_time = update_dict.get('start_time', db_template.start_time)
        final_trainer_id = update_dict.get('responsible_trainer_id', db_template.responsible_trainer_id)
        
        # Проверяем, нет ли конфликта с другими шаблонами
        existing_template = db.query(TrainingTemplate).filter(
            TrainingTemplate.id != template_id,  # Исключаем текущий шаблон
            TrainingTemplate.day_number == final_day,
            TrainingTemplate.start_time == final_time,
            TrainingTemplate.responsible_trainer_id == final_trainer_id
        ).first()
        
        if existing_template:
            raise HTTPException(
                status_code=400,
                detail=f"Trainer conflict: Trainer with ID {final_trainer_id} already has a training scheduled for day {final_day} at {final_time}. A trainer cannot be in two places at the same time."
            )
    
    for field, value in update_dict.items():
        setattr(db_template, field, value)
    
    db.commit()
    db.refresh(db_template)
    return db_template


# Удаление тренировочного шаблона
def delete_training_template(db: Session, template_id: int):
    db_template = get_training_template_by_id(db, template_id)
    if not db_template:
        return None
    # Soft-delete: mark as deleted so dependent real trainings and students keep their references
    db_template.is_deleted = True
    db.commit()
    db.refresh(db_template)
    return db_template




# Получение списка всех студент-шаблонов
def get_training_student_templates(db: Session):
    return db.query(TrainingStudentTemplate).options(joinedload(TrainingStudentTemplate.student)).all()


# Получение студент-шаблона по ID
def get_training_student_template_by_id(db: Session, student_template_id: int):
    return db.query(TrainingStudentTemplate).options(joinedload(TrainingStudentTemplate.student)).filter(TrainingStudentTemplate.id == student_template_id).first()


# Создание нового студент-шаблона
def create_training_student_template(db: Session, student_template_data: TrainingStudentTemplateCreate):
    # 1. Получаем шаблон тренировки и связанный тип тренировки
    training_template = (
        db.query(TrainingTemplate)
        .options(selectinload(TrainingTemplate.training_type))
        .filter(TrainingTemplate.id == student_template_data.training_template_id)
        .first()
    )
    if not training_template:
        raise HTTPException(status_code=404, detail=f"Training template with id {student_template_data.training_template_id} not found")
    training_type = training_template.training_type
    if not training_type:
        raise HTTPException(status_code=500, detail=f"Training type not found for template id {training_template.id}")
    max_participants = training_type.max_participants
    current_student_count = (
        db.query(TrainingStudentTemplate)
        .filter(
            TrainingStudentTemplate.training_template_id == student_template_data.training_template_id,
            TrainingStudentTemplate.is_frozen == False
        )
        .count()
    )
    if current_student_count >= max_participants:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot add student. Maximum number of participants ({max_participants}) for this training type in this template has been reached."
        )
    # Валидация убрана: start_date может быть исторической для дублирования шаблонов
    # if student_template_data.start_date < date.today():
    #     raise ValueError("Дата начала не может быть в прошлом")
    db_student_template = TrainingStudentTemplate(
        training_template_id=student_template_data.training_template_id,
        student_id=student_template_data.student_id,
        start_date=student_template_data.start_date,
        is_frozen=False
    )
    db.add(db_student_template)
    db.commit()
    db.refresh(db_student_template)
    return db_student_template


# Обновление студент-шаблона
def update_training_student_template(db: Session, student_template_id: int, update_data: TrainingStudentTemplateUpdate):
    db_student_template = get_training_student_template_by_id(db, student_template_id)
    if not db_student_template:
        return None
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(db_student_template, field, value)
    
    db.commit()
    db.refresh(db_student_template)
    return db_student_template


# Удаление студент-шаблона
def delete_training_student_template(db: Session, student_template_id: int):
    db_student_template = get_training_student_template_by_id(db, student_template_id)
    if not db_student_template:
        return None
    
    db.delete(db_student_template)
    db.commit()
    return db_student_template