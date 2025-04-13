import logging

from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base

logger = logging.getLogger(__name__)

class Training(Base):
    __tablename__ = "trainings"

    id = Column(Integer, primary_key=True, index=True)
    trainer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    training_datetime = Column(DateTime(timezone=True), nullable=False)
    training_type_id = Column(Integer, ForeignKey("training_types.id"), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    trainer = relationship("User", backref="trainings")
    clients = relationship("TrainingClient", back_populates="training")


    __table_args__ = (
        UniqueConstraint(
            'trainer_id', 'training_datetime', name='unique_trainer_training_datetime'
        ),
    )


class TrainingClient(Base):
    __tablename__ = "training_clients"

    id = Column(Integer, primary_key=True, index=True)
    training_id = Column(Integer, ForeignKey("trainings.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)

    trial_training = Column(Boolean, nullable=False, default=False, server_default="false")

    client = relationship("User", backref="training_clients")
    training = relationship("Training", back_populates="clients")

    @property
    def is_birthday(self) -> bool:
        """Determines if the client's birthday matches the training date."""
        if not self.client or not self.training:
            logger.warning("Either client or training is missing.")
            return False  # Client or training data is incomplete

        training_date = self.training.training_datetime
        birth_date = self.client.birth_date

        if not birth_date or not training_date:
            logger.warning("Either training_datetime or birth_date is missing.")
            return False  # Missing required fields

        if training_date.tzinfo is None or birth_date.tzinfo is None:
            logger.warning("Missing timezone information for training_datetime or birth_date.")
            return False  # Handle cases where time zone information is invalid

        try:
            # Convert training and birth dates to local time zones
            training_date_local = training_date.astimezone(training_date.tzinfo.utcoffset(training_date))
            birth_date_local = birth_date.astimezone(birth_date.tzinfo.utcoffset(birth_date))
            logger.debug(f"Birth date: {birth_date_local}, Training date: {training_date_local}")

            # Compare only day and month
            is_match = birth_date_local.date().month == training_date_local.date().month and birth_date_local.date().day == training_date_local.date().day
            logger.info(f"Is birthday: {is_match}")
            return is_match

        except Exception as e:
            logger.error(f"Не удалось проверить день рождения, он будет установлен как fasle: {e}")
            return False  # Catch any unexpected errors and fail gracefully



    __table_args__ = (
            UniqueConstraint('training_id', 'client_id', name='unique_training_client'),
        )
