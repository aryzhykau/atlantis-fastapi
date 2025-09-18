import logging
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.database import transactional
from app.models import RealTraining, RealTrainingStudent, InvoiceStatus, AttendanceStatus, StudentSubscription, Student, Invoice, InvoiceType
from app.schemas.invoice import InvoiceCreate
from app.services.financial import FinancialService

logger = logging.getLogger(__name__)

class DailyOperationsService:
    def __init__(self, db: Session):
        self.db = db
        self.financial_service = FinancialService(db)
    def _auto_mark_todays_attendance(self) -> None:
        """
        Automatically marks attendance for today's trainings.
        Finds all of today's trainings and marks students with
        a 'REGISTERED' status as 'PRESENT'.
        """
        logger.info("Starting auto-marking attendance for today's trainings...")
        today = date.today()
        
        todays_trainings = self.db.query(RealTraining).filter(
            RealTraining.training_date == today
        ).all()

        marked_students = 0
        for training in todays_trainings:
            for student_training in training.students:
                if student_training.status == AttendanceStatus.REGISTERED:
                    student_training.status = AttendanceStatus.PRESENT
                    self.db.add(student_training)
                    marked_students += 1
        
        if marked_students > 0:
            logger.info(f"Auto-marked {marked_students} students as PRESENT.")
        else:
            logger.info("No students to auto-mark for today's trainings.")

    def process_daily_operations(self) -> dict:
        """
        Main entry point for daily operations.
        1. Auto-marks attendance for today's trainings.
        2. Processes trainings for the next day for financial purposes.
        """
        logger.info("Starting daily operations...")

        # 1. Auto-mark attendance for today's trainings
        self._auto_mark_todays_attendance()

        # 2. Process tomorrow's trainings
        processing_date = date.today() + timedelta(days=1)
        logger.info(f"Processing trainings for date: {processing_date}")
        
        trainings_to_process = self.db.query(RealTraining).filter(
            RealTraining.training_date == processing_date,
            RealTraining.processed_at.is_(None),
            RealTraining.cancelled_at.is_(
                None
            ),
        ).all()

        students_updated = 0
        for training in trainings_to_process:
            logger.info(
                f"Processing training {training.id} for date {training.training_date}"
            )
            for student_training in training.students:
                self._process_student(student_training)
                students_updated += 1
            training.processed_at = date.today()
            self.db.add(training)

        self.db.commit()

        logger.info("Daily operations completed.")
        return {
            "students_updated_financial": students_updated,
            "trainings_processed_financial": len(trainings_to_process),
            "processing_date_financial": processing_date.isoformat(),
        }

    

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
        Processes a subscription user, deducting a session based on priority.
        If no sessions are available:
        - If auto-renew is OFF, an invoice is created for PRESENT/ABSENT students.
        - If auto-renew is ON, the session is considered 'borrowed' from the next subscription.
        ABSENT students are treated like PRESENT students for deduction purposes.
        """
        if student_training.session_deducted:
            logger.info(f"Session already deducted for student {student_training.student_id} in training {student_training.real_training_id}")
            return

        # Determine if a session should be deducted or a penalty applied
        should_deduct_or_penalize = student_training.status in [
            AttendanceStatus.REGISTERED,
            AttendanceStatus.PRESENT,
            AttendanceStatus.ABSENT
        ]

        if not should_deduct_or_penalize:
            logger.info(f"Student {student_training.student_id} status is {student_training.status}, not deducting session or applying penalty.")
            return

        # Get the student's subscription
        subscription = self.db.query(StudentSubscription).filter(
            StudentSubscription.id == student_training.subscription_id
        ).first()

        if not subscription:
            logger.error(f"No subscription found for student_training {student_training.id}")
            return

        deducted = False
        if subscription.sessions_left > 0:
            subscription.sessions_left -= 1
            logger.info(f"Deducted from main sessions for student {student_training.student_id}. Sessions left: {subscription.sessions_left}")
            deducted = True
        elif subscription.transferred_sessions > 0:
            subscription.transferred_sessions -= 1
            logger.info(f"Deducted from transferred sessions for student {student_training.student_id}. Transferred sessions left: {subscription.transferred_sessions}")
            deducted = True
        elif subscription.skipped_sessions > 0:
            # Only deduct from skipped sessions if the student is PRESENT or ABSENT
            if student_training.status in [AttendanceStatus.PRESENT, AttendanceStatus.ABSENT]:
                subscription.skipped_sessions -= 1
                logger.info(f"Deducted from skipped sessions for student {student_training.student_id}. Skipped sessions left: {subscription.skipped_sessions}")
                deducted = True
            else:
                logger.warning(f"Skipped sessions available but not used for status {student_training.status} for student {student_training.student_id}.")
        
        if deducted:
            student_training.session_deducted = True
            self.db.add(student_training)
            self.db.add(subscription)
            logger.info(f"Session successfully deducted for student {student_training.student_id} in training {student_training.real_training_id}")
        else:
            # If no sessions available
            if subscription.is_auto_renew:
                # If auto-renew is ON, the session is considered 'borrowed' from the next subscription.
                # No invoice is generated. Increment borrowed_sessions_count.
                subscription.borrowed_sessions_count += 1
                self.db.add(subscription) # Persist the change to borrowed_sessions_count
                student_training.session_deducted = True # Mark as deducted to prevent re-processing
                self.db.add(student_training)
                logger.warning(f"Session for student {student_training.student_id} in training {student_training.real_training_id} is borrowed from next auto-renewed subscription. Borrowed count: {subscription.borrowed_sessions_count}.")
            else:
                # If auto-renew is OFF, create an invoice penalty for ABSENT or PRESENT students
                if student_training.status in [AttendanceStatus.PRESENT, AttendanceStatus.ABSENT]:
                    student = self.db.query(Student).filter(Student.id == student_training.student_id).first()
                    training = self.db.query(RealTraining).filter(RealTraining.id == student_training.real_training_id).first()
                    if student and training and training.training_type:
                        penalty_amount = training.training_type.price if training.training_type.price is not None else 100.0
                        description = f"Счет за тренировку {training.training_type.name} {training.training_date}" # Default for PRESENT
                        if student_training.status == AttendanceStatus.ABSENT:
                            description = f"Штраф за неявку {training.training_type.name} {training.training_date}"

                        invoice_data = InvoiceCreate(
                            student_id=student.id,
                            client_id=student.client_id,
                            amount=penalty_amount,
                            training_id=training.id,
                            type=InvoiceType.TRAINING,
                            description=description,
                            status=InvoiceStatus.UNPAID
                        )
                        new_invoice = self.financial_service.create_standalone_invoice(invoice_data, auto_pay=True)
                        logger.warning(f"Penalty: New UNPAID invoice {new_invoice.id} created for student {student.id} due to no available sessions and status {student_training.status} (auto-renew OFF).")
                        student_training.session_deducted = True # Mark as deducted to prevent re-processing
                        self.db.add(student_training)
                    else:
                        logger.error(f"Could not create penalty invoice for student {student_training.student_id} in training {student_training.real_training_id}: missing student, training, or training_type info.")
                else:
                    logger.warning(f"No sessions available for student {student_training.student_id} in training {student_training.real_training_id}. Session not deducted and no penalty applied for status {student_training.status} (auto-renew OFF).")

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

        if student_training.status in [AttendanceStatus.REGISTERED, AttendanceStatus.PRESENT, AttendanceStatus.CANCELLED_PENALTY, AttendanceStatus.ABSENT]:
            invoice.status = InvoiceStatus.UNPAID
            self.db.add(invoice)
            self.db.flush()
            self.financial_service.attempt_auto_payment(self.db, invoice.id)
        elif student_training.status == AttendanceStatus.CANCELLED_SAFE:
            invoice.status = InvoiceStatus.CANCELLED
            self.db.add(invoice)