from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.schemas.user import TrainerCreate, TrainerUpdate
from datetime import datetime


# Создание тренера
def create_trainer(db: Session, trainer_data: TrainerCreate):
    trainer = User(
        first_name=trainer_data.first_name,
        last_name=trainer_data.last_name,
        date_of_birth=trainer_data.date_of_birth,
        email=trainer_data.email,
        phone=trainer_data.phone,
        salary=trainer_data.salary,
        is_fixed_salary=trainer_data.is_fixed_salary,
        role=UserRole.TRAINER
    )
    db.add(trainer)
    db.commit()
    db.refresh(trainer)
    return trainer


# Получить тренера по ID
def get_trainer(db: Session, trainer_id: int):
    return db.query(User).filter(User.id == trainer_id, User.role == UserRole.TRAINER).first()


# Получить всех тренеров
def get_all_trainers(db: Session):
    return db.query(User).filter(User.role == UserRole.TRAINER).all()


# Обновление тренера
def update_trainer(db: Session, trainer_id: int, trainer_data: TrainerUpdate):
    trainer = db.query(User).filter(User.id == trainer_id, User.role == UserRole.TRAINER).first()
    if not trainer:
        return None
    
    # Если меняется статус на неактивный, устанавливаем дату деактивации
    if trainer_data.is_active is False and trainer.is_active:
        trainer.deactivation_date = datetime.now()
    # Если статус меняется на активный, убираем дату деактивации
    elif trainer_data.is_active is True:
        trainer.deactivation_date = None
    
    for key, value in trainer_data.model_dump(exclude_unset=True).items():
        setattr(trainer, key, value)
    
    db.commit()
    db.refresh(trainer)
    return trainer


# Обновление статуса тренера
def update_trainer_status(db: Session, trainer_id: int, is_active: bool):
    """
    Обновляет только статус тренера (активный/неактивный)
    
    Args:
        db: Сессия базы данных
        trainer_id: ID тренера
        is_active: Новый статус (True - активный, False - неактивный)
        
    Returns:
        User: Обновленный объект тренера или None, если тренер не найден
    """
    trainer = db.query(User).filter(User.id == trainer_id, User.role == UserRole.TRAINER).first()
    if not trainer:
        return None
    
    # Проверяем, изменился ли статус
    status_changed = trainer.is_active != is_active
    
    # Устанавливаем новый статус
    trainer.is_active = is_active
    
    # Если деактивируем тренера, устанавливаем дату деактивации
    if is_active is False:
        trainer.deactivation_date = datetime.now()
    # Если активируем тренера, убираем дату деактивации
    else:
        trainer.deactivation_date = None
    
    try:
        db.commit()
        db.refresh(trainer)
        return trainer
    except Exception as e:
        db.rollback()
        raise e


# Удалить тренера
def delete_trainer(db: Session, trainer_id: int):
    trainer = db.query(User).filter(User.id == trainer_id, User.role == UserRole.TRAINER).first()
    if not trainer:
        return None
    db.delete(trainer)
    db.commit()
    return trainer