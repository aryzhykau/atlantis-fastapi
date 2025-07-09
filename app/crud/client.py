from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime

from app.models import Student
from app.models.user import User, UserRole
from app.schemas.user import ClientCreate, ClientUpdate
from app.schemas.student import StudentCreateWithoutClient


# Создание клиента
def create_client(db: Session, client_data: ClientCreate):
    try:
        client = User(
            first_name=client_data.first_name,
            last_name=client_data.last_name,
            date_of_birth=client_data.date_of_birth,
            email=client_data.email,
            phone=client_data.phone,
            whatsapp_number=client_data.whatsapp_number,
            balance=0,
            role=UserRole.CLIENT,
            is_authenticated_with_google=True
        )

        db.add(client)
        db.flush()
        if client_data.is_student:
            student = Student(
                client_id=client.id,
                is_active=True,
                first_name=client_data.first_name,
                last_name=client_data.last_name,
                date_of_birth=client_data.date_of_birth,
            )
            db.add(student)
        if client_data.students:
            for student_data in client_data.students:
                student = Student(
                    client_id=client.id,
                    is_active=True,
                    first_name=student_data.first_name,
                    last_name=student_data.last_name,
                    date_of_birth=student_data.date_of_birth,
                )
                db.add(student)
        db.commit()
        db.refresh(client)
        return client
    except ValueError as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        print(f"Error occurred: {e}")
        raise e


# Получить клиента по ID
def get_client(db: Session, client_id: int):
    return db.query(User).filter(User.id == client_id, User.role == UserRole.CLIENT).first()


# Получить всех клиентов
def get_all_clients(db: Session):
    return db.query(User).filter(User.role == UserRole.CLIENT).order_by(User.first_name, User.last_name).all()


# Обновление клиента
def update_client(db: Session, client_id: int, client_data: ClientUpdate):
    try:
        client = db.query(User).filter(User.id == client_id, User.role == UserRole.CLIENT).first()
        if not client:
            return None
        for key, value in client_data.model_dump(exclude_unset=True).items():
            setattr(client, key, value)
        db.commit()
        db.refresh(client)
        return client
    except ValueError as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise e


# Удалить клиента
def delete_client(db: Session, client_id: int):
    client = db.query(User).filter(User.id == client_id, User.role == UserRole.CLIENT).first()
    if not client:
        return None
    db.delete(client)
    db.commit()
    return client


def update_client_status(db: Session, client_id: int, is_active: bool) -> tuple[User, int]:
    """
    Обновляет статус клиента и каскадно обновляет статусы связанных студентов.
    Возвращает кортеж (client, affected_students_count).
    """
    client = db.query(User).filter(User.id == client_id).first()
    if not client:
        raise ValueError("Клиент не найден")
    
    client.is_active = is_active
    client.deactivation_date = datetime.now() if not is_active else None
    
    affected_students_count = 0
    if not is_active:
        # Каскадное обновление студентов
        students = db.query(Student).filter(Student.client_id == client_id).all()
        for student in students:
            student.is_active = False
            student.deactivation_date = datetime.now()
            affected_students_count += 1
    
    try:
        db.commit()
        db.refresh(client)
        return client, affected_students_count
    except Exception as e:
        db.rollback()
        raise e