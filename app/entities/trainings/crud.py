from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound
from datetime import datetime
from .schemas import TrainingCreateSchema, TrainingSchema, TrainingWithClientsCreate
from sqlalchemy.orm import Session
from .models import Training, TrainingClient


def create_training_with_clients(db: Session, training_data: TrainingWithClientsCreate):
    """
    Создаёт тренировку и привязывает к ней клиентов.
    """
    # Создаём тренировку
    new_training = Training(
        trainer_id=training_data.trainer_id,
        training_date=training_data.training_date,
        training_time=training_data.training_time,
        training_type_id=training_data.training_type_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(new_training)
    db.flush()  # Получаем ID тренировки для использования

    # Привязываем клиентов к тренировке
    for client in training_data.clients:
        training_client = TrainingClient(
            training_id=new_training.id,
            client_id=client.client_id,
            invoice_id=client.invoice_id,
            covered_by_subscription=client.covered_by_subscription,
            trial_training=client.trial_training,
        )
        db.add(training_client)

    db.commit()
    db.refresh(new_training)  # Получаем обновлённый объект тренировки
    return new_training



def get_training_by_id(db: Session, training_id: int):
    try:
        return db.query(Training).filter(Training.id == training_id).one()
    except NoResultFound:
        return None


def get_all_trainings(db: Session):
    return db.query(Training).all()


def update_training(db: Session, training_id: int, updated_data: TrainingSchema):
    db_training = db.query(Training).filter(Training.id == training_id).first()
    if db_training:
        db_training.trainer_id = updated_data.trainer_id
        db_training.training_date = updated_data.training_date
        db_training.training_time = updated_data.training_time
        db_training.training_type_id = updated_data.training_type_id
        db_training.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_training)
        return db_training
    return None


def delete_training(db: Session, training_id: int):
    db_training = db.query(Training).filter(Training.id == training_id).first()
    if db_training:
        db.delete(db_training)
        db.commit()
        return db_training
    return None
