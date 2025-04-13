import logging
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.entities.invoices.crud import create_invoice
from app.entities.training_types.crud import get_training_type_by_id
from app.entities.trainings.errors import (
    TrainingWithoutClientsError,
    TrainingWithoutTrainingTypeError,
    TrainingClientIdMissingError
)
from app.entities.trainings.trainings_utils import (
    check_trainer_availability,
    generate_invoice,
    check_training_client_uniqueness,
    check_client_training_time_overlap,
    check_client_subscription,
)
from .models import Training, TrainingClient
from .schemas import TrainingWithClientsCreate, TrainingWithClientsRead
from ..invoices.models import InvoiceTypeEnum

logger = logging.getLogger(__name__)


def create_training_with_clients(db: Session, training_data: TrainingWithClientsCreate):
    """
    Создаёт тренировку и привязывает к ней клиентов.
    """
    logger.debug(f"Starting training creation with data: {training_data}")

    try:
        # Проверка входных данных
        if not training_data.clients:
            raise TrainingWithoutClientsError()
        if not training_data.training_type_id or not training_data.trainer_id:
            raise TrainingWithoutTrainingTypeError()

        check_trainer_availability(db, training_data.trainer_id, training_data.training_datetime)
        training_type = get_training_type_by_id(db, training_data.training_type_id)

        # Создаём тренировку
        new_training = Training(
            trainer_id=training_data.trainer_id,
            training_datetime=training_data.training_datetime,
            training_type_id=training_data.training_type_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db.add(new_training)
        db.flush()

        # Привязываем клиентов к тренировке
        for client in training_data.clients:
            logger.debug(f"Processing client: {client}")

            if not client.client_id:
                raise TrainingClientIdMissingError()

            check_training_client_uniqueness(db, new_training.id, client.client_id)
            check_client_training_time_overlap(db, client.client_id, training_data.training_datetime)

            if training_type.require_subscription:
                check_client_subscription(db, client.client_id)


            new_invoice = None
            if client.trial_training:
                logger.debug("Creating trial invoice")
                new_invoice = generate_invoice(client.client_id, training_data.training_datetime, InvoiceTypeEnum.TRIAL, 20)
                db_invoice = create_invoice(db, new_invoice)
            elif not training_type.require_subscription:
                logger.debug("Creating single invoice")
                new_invoice = generate_invoice(client.client_id, training_data.training_datetime, InvoiceTypeEnum.SINGLE, training_type.price)
                db_invoice = create_invoice(db, new_invoice)
            else:
                logger.debug("No invoice needed")
                db_invoice = None
            db.flush()

            # Создание связи клиента с тренировкой
            training_client = TrainingClient(
                training_id=new_training.id,
                invoice_id=db_invoice.id if db_invoice else None,
                client_id=client.client_id,
                trial_training=client.trial_training,
            )
            db.add(training_client)

        # Сохраняем изменения в базе
        db.commit()
        db.refresh(new_training)  # Получаем актуальную информацию из базы данных

        return new_training

    except Exception as e:
        db.rollback()  # Откат изменений при любой ошибке
        logger.error(f"Error while creating training: {e}")
        raise



def get_training_by_id(db_session, training_id: int):
    training = db_session.query(Training).options(
        joinedload(Training.clients)  # Загрузка связанных пользователей (клиентов тренировки)
    ).filter(Training.id == training_id).first()


def get_all_trainings(db_session, trainer_id: int = None, start_week: datetime = None, end_week: datetime = None):
    query = db_session.query(Training)

    logger.debug(start_week)
    logger.debug(end_week)

    if trainer_id:
        query = query.filter(Training.trainer_id == trainer_id)

    if start_week and end_week:
        query = query.filter(Training.training_datetime >= start_week,
                             Training.training_datetime <= end_week)

    trainings = query.order_by(func.timezone('UTC', Training.training_datetime).asc(), Training.id.asc()).all()



    return trainings


def update_training(db: Session, training_id: int, updated_data: TrainingWithClientsRead):
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
