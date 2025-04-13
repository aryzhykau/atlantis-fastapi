from datetime import datetime

from sqlalchemy.orm import Session

from app.entities.invoices.models import InvoiceTypeEnum
from app.entities.invoices.schemas import InvoiceCreate
from app.entities.trainings.errors import (
    TrainerBusyError,
    ClientAlreadyInTrainingError,
    ClientTimeConflictError,
    ClientSubscriptionError
)
from app.entities.trainings.models import Training, TrainingClient
from app.entities.users.models import ClientSubscription


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



def check_client_subscription(db: Session, client_id: int):
    active_subscription = db.query(ClientSubscription).filter_by(
        client_id=client_id,
        active=True
    ).first()
    if not active_subscription:
        raise ClientSubscriptionError(client_id)




def generate_invoice(client_id: int, created_at: datetime, invoice_type: InvoiceTypeEnum, amount: float) -> InvoiceCreate:
    return InvoiceCreate(
        user_id=client_id,
        created_at=created_at,
        invoice_type=invoice_type,
        amount=amount,
    )
