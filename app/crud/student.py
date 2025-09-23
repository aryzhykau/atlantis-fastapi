import logging
from sqlalchemy.orm import Session
from app.models.student import Student
from app.schemas.student import StudentCreate, StudentUpdate

logger = logging.getLogger(__name__)

def get_student_by_id(db: Session, student_id: int) -> Student | None:
    """Retrieves a student by their ID."""
    return db.query(Student).filter(Student.id == student_id).first()


def get_students_by_client_id(db: Session, client_id: int) -> list[Student]:
    """Retrieves all students associated with a specific client ID."""
    return db.query(Student).filter(Student.client_id == client_id).order_by(Student.first_name, Student.last_name).all()


def get_all_students(db: Session) -> list[Student]:
    """Retrieves all students from the database."""
    return db.query(Student).all()


def create_student(db: Session, student_data: StudentCreate, client_id: int) -> Student:
    """Creates a new student associated with a client without committing."""
    new_student = Student(
        first_name=student_data.first_name,
        last_name=student_data.last_name,
        date_of_birth=student_data.date_of_birth,
        client_id=client_id,
        is_active=True
    )
    logger.info(f"new student name: {new_student.first_name} {new_student.last_name}, client_id: {new_student.client_id}")
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return new_student


def update_student(db: Session, student_id: int, student_data: StudentUpdate) -> Student | None:
    """Updates a student's data without committing."""
    student = get_student_by_id(db, student_id)
    if not student:
        return None

    update_data = student_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(student, key, value)

    return student


