from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.student import Student
from app.models.subscription import StudentSubscription
from app.models.user import User
from datetime import datetime
from app.crud.student import get_student_by_id

class StudentService:
    def update_active_subscription_id(self, db: Session, student: Student) -> None:
        """
        Updates the active_subscription_id of a student by checking the status of their subscriptions.
        If the current active subscription has expired or is frozen, it searches for a new active one.
        This method commits the changes to the database.
        """
        if not student.active_subscription_id:
            return

        current_subscription = (
            db.query(StudentSubscription)
            .filter(
                and_(
                    StudentSubscription.student_id == student.id,
                    StudentSubscription.subscription_id == student.active_subscription_id
                )
            )
            .first()
        )

        if not current_subscription or current_subscription.status in ["expired", "frozen"]:
            active_subscription = (
                db.query(StudentSubscription)
                .filter(
                    and_(
                        StudentSubscription.student_id == student.id,
                        StudentSubscription.status == "active"
                    )
                )
                .order_by(StudentSubscription.end_date.desc())
                .first()
            )

            student.active_subscription_id = active_subscription.subscription_id if active_subscription else None
            db.commit()

    # def update_student_active_subscription(self, db: Session, student_id: int, subscription_id: Optional[int]) -> None:
    #     student = get_student_by_id(db, student_id)
    #     if student:
    #         student.active_subscription_id = subscription_id
    #         db.flush() # Use flush as commit is handled by the calling service

    def update_student_status(self, db: Session, student_id: int, is_active: bool) -> Student:
        student = get_student_by_id(db, student_id)
        if not student:
            raise ValueError("Студент не найден")
        
        if is_active:
            client = db.query(User).filter(User.id == student.client_id).first()
            if not client:
                raise ValueError("Клиент не найден")
            if not client.is_active:
                raise ValueError("Невозможно активировать студента: родительский клиент неактивен")
        
        student.is_active = is_active
        student.deactivation_date = datetime.now() if not is_active else None
        
        db.commit()
        db.refresh(student)
        return student

student_service = StudentService()
