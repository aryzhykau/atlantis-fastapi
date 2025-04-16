from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.entities.invoices.models import InvoiceTypeEnum
from app.entities.invoices.schemas import InvoiceCreate
from app.entities.trainings.errors import (
    TrainerBusyError,
    ClientAlreadyInTrainingError,
    ClientTimeConflictError,
    ClientSubscriptionError, ClientSubscriptionSessionsError
)
from app.entities.trainings.models import Training, TrainingClient
from app.entities.users.models import  User


def check_trainer_availability(db: Session, trainer_id: int, training_datetime: datetime):
    existing_training = db.query(Training).filter_by(
        trainer_id=trainer_id,
        training_datetime=training_datetime
    ).first()
    if existing_training:
        raise TrainerBusyError


def check_training_client_uniqueness(db: Session, training_id: int, client_id: int):
    existing_client = db.query(TrainingClient).filter_by(
        training_id=training_id,
        client_id=client_id
    ).first()
    if existing_client:
        raise ClientAlreadyInTrainingError


def check_client_training_time_overlap(db: Session, client_id: int, training_datetime: datetime):
    overlapping_training = db.query(Training).join(TrainingClient).filter(
        TrainingClient.client_id == client_id,
        Training.training_datetime == training_datetime
    ).first()
    if overlapping_training:
        raise ClientTimeConflictError(client_id)



def check_client_subscription_and_trial(db: Session, client_id: int):
    active_subscription = db.query(ClientSubscription).filter_by(
        client_id=client_id,
        active=True,
    ).first()
    trial = db.query(User).filter_by(has_trial=True, id=client_id).first()
    if not active_subscription and not trial:
        raise ClientSubscriptionError(client_id)
    if active_subscription.sessions_left < 0:
        raise ClientSubscriptionSessionsError(client_id)





def generate_invoice(client_id: int, created_at: datetime, invoice_type: InvoiceTypeEnum, amount: float) -> InvoiceCreate:
    return InvoiceCreate(
        user_id=client_id,
        created_at=created_at,
        invoice_type=invoice_type,
        amount=amount,
    )

def check_client_training_same_day(db: Session, client_id: int, training_datetime: datetime):
    """
    Проверяет, есть ли у клиента тренировочная запись на тот же день.
    """
    # Приведение даты тренировки к дню
    training_date = training_datetime.date()

    # Запрос, проверяющий тренировки клиента на тот же день
    existing_training = db.query(Training).join(TrainingClient).filter(
        TrainingClient.client_id == client_id,
        func.date(Training.training_datetime) == training_date  # Сравнить только даты
    ).first()

    if existing_training:
        raise ClientTimeConflictError(
            f"Client {client_id} already has a training on {training_date}."
        )
