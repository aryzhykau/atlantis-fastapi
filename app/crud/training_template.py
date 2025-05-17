from sqlalchemy.orm import Session
from app.models import TrainingTemplate, TrainingStudentTemplate
from app.schemas.training_template import (
    TrainingTemplateCreate,
    TrainingTemplateUpdate,
    TrainingStudentTemplateCreate,
    TrainingStudentTemplateUpdate,
)



# Получение списка всех тренировочных шаблонов
def get_training_templates(db: Session):
    return db.query(TrainingTemplate).order_by(TrainingTemplate.day_number).all()


# Получение тренировочного шаблона по ID
def get_training_template_by_id(db: Session, template_id: int):
    return db.query(TrainingTemplate).filter(TrainingTemplate.id == template_id).first()


# Создание нового тренировочного шаблона
def create_training_template(db: Session, training_template: TrainingTemplateCreate):
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
    
    db.delete(db_template)
    db.commit()
    return db_template




# Получение списка всех студент-шаблонов
def get_training_student_templates(db: Session):
    return db.query(TrainingStudentTemplate).all()


# Получение студент-шаблона по ID
def get_training_student_template_by_id(db: Session, student_template_id: int):
    return db.query(TrainingStudentTemplate).filter(TrainingStudentTemplate.id == student_template_id).first()


# Создание нового студент-шаблона
def create_training_student_template(db: Session, student_template: TrainingStudentTemplateCreate):
    db_student_template = TrainingStudentTemplate(
        training_template_id=student_template.training_template_id,
        student_id=student_template.student_id,
        start_date=student_template.start_date,
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