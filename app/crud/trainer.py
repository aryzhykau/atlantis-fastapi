from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.schemas.user import TrainerCreate, TrainerUpdate


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
    for key, value in trainer_data.model_dump(exclude_unset=True).items():
        setattr(trainer, key, value)
    db.commit()
    db.refresh(trainer)
    return trainer


# Удалить тренера
def delete_trainer(db: Session, trainer_id: int):
    trainer = db.query(User).filter(User.id == trainer_id, User.role == UserRole.TRAINER).first()
    if not trainer:
        return None
    db.delete(trainer)
    db.commit()
    return trainer