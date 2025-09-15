from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import User, UserRole
from app.models.client_contact_task import (
    ClientContactReason,
    ClientContactStatus,
    ClientContactTask,
)


DEFAULT_INACTIVITY_DAYS = 30


class ClientContactService:
    def __init__(self, db: Session):
        self.db = db

    def create_task(
        self,
        *,
        client_id: int,
        reason: ClientContactReason,
        note: Optional[str] = None,
        assigned_to_id: Optional[int] = None,
        last_activity_at: Optional[datetime] = None,
    ) -> ClientContactTask:
        task = ClientContactTask(
            client_id=client_id,
            reason=reason,
            status=ClientContactStatus.PENDING,
            note=note,
            assigned_to_id=assigned_to_id,
            last_activity_at=last_activity_at,
        )
        self.db.add(task)
        self.db.flush()
        return task

    def mark_done(
        self, task_id: int, *, note: Optional[str] = None, assigned_to_id: Optional[int] = None
    ) -> Optional[ClientContactTask]:
        task = self.db.query(ClientContactTask).get(task_id)
        if not task:
            return None
        task.status = ClientContactStatus.DONE
        task.done_at = datetime.now(timezone.utc)
        if note is not None:
            task.note = note
        if assigned_to_id is not None:
            task.assigned_to_id = assigned_to_id
        self.db.flush()
        return task

    def list_tasks(
        self,
        *,
        status: Optional[ClientContactStatus] = None,
        reason: Optional[ClientContactReason] = None,
        assigned_to_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ClientContactTask]:
        q = self.db.query(ClientContactTask)
        if status is not None:
            q = q.filter(ClientContactTask.status == status)
        if reason is not None:
            q = q.filter(ClientContactTask.reason == reason)
        if assigned_to_id is not None:
            q = q.filter(ClientContactTask.assigned_to_id == assigned_to_id)
        return q.order_by(ClientContactTask.created_at.desc()).offset(offset).limit(limit).all()

    def create_task_on_new_client(self, client_id: int) -> ClientContactTask:
        return self.create_task(client_id=client_id, reason=ClientContactReason.NEW_CLIENT)

    def detect_and_create_returned_clients_tasks(self, *, inactivity_days: int = DEFAULT_INACTIVITY_DAYS) -> int:
        now_utc = datetime.now(timezone.utc)
        cutoff = now_utc - timedelta(days=inactivity_days)
        created = 0

        # Клиенты
        clients = self.db.query(User).filter(User.role == UserRole.CLIENT).all()
        for client in clients:
            last_two = self._get_client_last_two_activities(client.id)
            if not last_two:
                continue
            last_activity = last_two[0]
            prev_activity = last_two[1] if len(last_two) > 1 else None

            # Создаём задачу только если предыдущее событие было давно (или его не было вообще),
            # а последнее событие свежее порога неактивности.
            if last_activity >= cutoff and (prev_activity is None or prev_activity < cutoff):
                exists = (
                    self.db.query(ClientContactTask)
                    .filter(
                        ClientContactTask.client_id == client.id,
                        ClientContactTask.reason == ClientContactReason.RETURNED,
                        ClientContactTask.status == ClientContactStatus.PENDING,
                    )
                    .first()
                )
                if not exists:
                    self.create_task(
                        client_id=client.id,
                        reason=ClientContactReason.RETURNED,
                        last_activity_at=last_activity,
                    )
                    created += 1
        self.db.flush()
        return created

    def _get_client_last_two_activities(self, client_id: int) -> list[datetime]:
        from app.models.payment import Payment
        from app.models.real_training import RealTraining, RealTrainingStudent, AttendanceStatus
        from app.models.student import Student

        # Payments: last two
        payments = (
            self.db.query(Payment)
            .filter(Payment.client_id == client_id, Payment.cancelled_at.is_(None))
            .order_by(Payment.payment_date.desc())
            .limit(2)
            .all()
        )
        payment_times = [p.payment_date for p in payments if p.payment_date is not None]

        # Attendances: last two training dates for student's trainings marked PRESENT
        attendances = (
            self.db.query(RealTraining.training_date)
            .join(RealTrainingStudent, RealTraining.id == RealTrainingStudent.real_training_id)
            .join(Student, Student.id == RealTrainingStudent.student_id)
            .filter(
                Student.client_id == client_id,
                RealTrainingStudent.status == AttendanceStatus.PRESENT,
            )
            .order_by(RealTraining.training_date.desc())
            .limit(2)
            .all()
        )
        attendance_times = [
            datetime.combine(a.training_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            for a in attendances
            if a.training_date is not None
        ]

        # Merge and return top 2
        merged = sorted(payment_times + attendance_times, reverse=True)
        return merged[:2]


def get_client_contact_service(db: Session) -> ClientContactService:
    return ClientContactService(db)


