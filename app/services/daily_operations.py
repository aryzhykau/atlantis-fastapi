import logging
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.database import transactional
from app.models import RealTraining, RealTrainingStudent, InvoiceStatus, AttendanceStatus
from app.services.financial import FinancialService

logger = logging.getLogger(__name__)

class DailyOperationsService:
    def __init__(self, db: Session):
        self.db = db
        self.financial_service = FinancialService(db)

    def process_tomorrows_trainings(self) -> None:
        """
        Processes all trainings scheduled for the next day.
        """
        tomorrow = date.today() + timedelta(days=1)
        trainings_to_process = self.db.query(RealTraining).filter(
            RealTraining.training_date == tomorrow,
            RealTraining.processed_at.is_(None)
        ).all()

        for training in trainings_to_process:
            self._process_training(training)

    @transactional
    def _process_training(self, training: RealTraining) -> None:
        """
        Processes a single training and all its students within a transaction.
        """
        logger.info(f"Processing training {training.id} for date {training.training_date}")

        for student_training in training.students:
            self._process_student(student_training)

        training.processed_at = date.today()
        self.db.add(training)

    def _process_student(self, student_training: RealTrainingStudent) -> None:
        """
        Processes a single student in a training.
        """
        if student_training.subscription_id:
            self._process_subscription_user(student_training)
        else:
            self._process_pay_per_session_user(student_training)

    def _process_subscription_user(self, student_training: RealTrainingStudent) -> None:
        """
        Processes a subscription user.
        """
        if not student_training.session_deducted:
            if student_training.status in [AttendanceStatus.REGISTERED, AttendanceStatus.PRESENT]:
                # This is where you would deduct a session from the subscription
                # For now, we'll just log it
                logger.info(f"Deducting session for student {student_training.student_id} in training {student_training.real_training_id}")
                student_training.session_deducted = True
                self.db.add(student_training)

    def _process_pay_per_session_user(self, student_training: RealTrainingStudent) -> None:
        """
        Processes a pay-per-session user.
        """
        invoice = self.db.query(Invoice).filter(
            Invoice.student_id == student_training.student_id,
            Invoice.training_id == student_training.real_training_id,
            Invoice.status == InvoiceStatus.PENDING
        ).first()

        if not invoice:
            return

        if student_training.status in [AttendanceStatus.REGISTERED, AttendanceStatus.PRESENT, AttendanceStatus.LATE_CANCEL, AttendanceStatus.NO_SHOW]:
            invoice.status = InvoiceStatus.UNPAID
            self.db.add(invoice)
            self.db.flush()
            self.financial_service.attempt_auto_payment(self.db, invoice.id)
        elif student_training.status == AttendanceStatus.CANCELLED_SAFE:
            invoice.status = InvoiceStatus.CANCELLED
            self.db.add(invoice)