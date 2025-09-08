from datetime import date, timedelta
from logging import getLogger

from sqlalchemy.orm import Session

from app.crud.real_training import get_real_trainings_by_date
from app.models import RealTrainingStudent
from app.models.real_training import AttendanceStatus
from app.services.training_processing import TrainingProcessingService

logger = getLogger(__name__)


class DailyOperationsService:
    def __init__(self, db: Session):
        self.db = db
        self.training_processing_service = TrainingProcessingService(db)

    def process_daily_operations(self):
        """
        Выполняет две основные операции:
        1. Обработка посещаемости за СЕГОДНЯШНИЙ день (статус REGISTERED -> PRESENT).
        2. Финансовая обработка СЕГОДНЯШНИХ тренировок.
        """
        today = date.today()

        logger.info("Starting daily operations...")

        # --- Этап 1: Обработка посещаемости за сегодня ---
        students_updated = self._process_today_attendance(today)

        # --- Этап 2: Финансовая обработка за сегодня ---
        trainings_processed = self._process_today_finances(today)

        logger.info("Daily operations completed.")
        self.db.commit()
        
        return {
            "students_updated": students_updated,
            "trainings_processed": trainings_processed,
            "processing_date": today.isoformat()
        }

    def _process_today_attendance(self, processing_date: date):
        """
        Меняет статус с REGISTERED на PRESENT для всех студентов
        на тренировках в указанный день.
        Финансовые операции здесь НЕ производятся.
        """
        logger.info(f"Processing attendance for date: {processing_date}...")
        trainings_today = get_real_trainings_by_date(self.db, processing_date)
        students_updated = 0

        for training in trainings_today:
            students_to_update = (
                self.db.query(RealTrainingStudent)
                .filter(
                    RealTrainingStudent.real_training_id == training.id,
                    RealTrainingStudent.status == AttendanceStatus.REGISTERED,
                )
                .all()
            )

            for student_training in students_to_update:
                student_training.status = AttendanceStatus.PRESENT
                students_updated += 1
                logger.debug(
                    f"Student {student_training.student_id} in training {training.id} "
                    f"marked as PRESENT."
                )

        logger.info(
            f"Attendance processing for {processing_date} finished. "
            f"Updated {students_updated} students."
        )
        
        return students_updated

    def _process_today_finances(self, processing_date: date):
        """
        Выполняет финансовую обработку (списание занятий/создание инвойсов)
        для всех тренировок на указанную дату, которые еще не были обработаны.
        """
        logger.info(f"Processing finances for date: {processing_date}...")
        trainings_today = get_real_trainings_by_date(self.db, processing_date)
        processed_count = 0

        for training in trainings_today:
            if training.processed_at is None:
                logger.info(f"Processing training ID: {training.id}")
                self.training_processing_service._process_training(self.db, training)
                processed_count += 1
            else:
                logger.info(
                    f"Skipping already processed training ID: {training.id}"
                )

        logger.info(
            f"Financial processing for {processing_date} finished. "
            f"Processed {processed_count} trainings."
        )
        
        return processed_count 