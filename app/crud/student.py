from sqlalchemy.orm import Session
from app.models.student import Student
from app.models.user import User
from app.schemas.student import StudentCreate, StudentUpdate


# Получить студента по ID
def get_student_by_id(db: Session, student_id: int) -> Student | None:
    """Получает студента по его ID."""
    return db.query(Student).filter(Student.id == student_id).first()


# Получить всех студентов
def get_students(db: Session) -> list[Student]:
    """Получает полный список студентов."""
    return db.query(Student).all()


# Создать нового студента
def create_student(db: Session, student_data: StudentCreate) -> Student:
    """Создает нового студента."""
    # Проверяем, существует ли клиент с данным client_id
    client = db.query(User).filter(User.id == student_data.client_id).first()
    if not client:
        raise ValueError(f"Клиент с ID {student_data.client_id} не найден.")

    # Создаем объект студента
    new_student = Student(
        first_name=student_data.first_name,
        last_name=student_data.last_name,
        date_of_birth=student_data.date_of_birth,
        client_id=student_data.client_id,
    )

    # Сохраняем запись в базе данных
    db.add(new_student)
    db.commit()
    db.refresh(new_student)

    return new_student


# Обновить студента
def update_student(db: Session, student_id: int, student_data: StudentUpdate) -> Student | None:
    """Обновляет информацию о студенте по его ID."""
    # Получаем студента из базы данных
    student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        return None

    # Обновляем поля студента, если они присутствуют в student_data
    if student_data.first_name is not None:
        student.first_name = student_data.first_name
    if student_data.last_name is not None:
        student.last_name = student_data.last_name
    if student_data.date_of_birth is not None:
        student.date_of_birth = student_data.date_of_birth
    if student_data.client_id is not None:
        # Проверяем существование нового клиента
        client = db.query(User).filter(User.id == student_data.client_id).first()
        if not client:
            raise ValueError(f"Клиент с ID {student_data.client_id} не найден.")
        student.client_id = student_data.client_id

    db.commit()
    db.refresh(student)

    return student


