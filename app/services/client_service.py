import logging
from sqlalchemy.orm import Session
from app.crud import client as crud_client
from app.crud import student as crud_student
from app.crud import user as crud_user
from app.schemas.user import ClientCreate
from app.schemas.student import StudentCreate
from sqlalchemy.orm import Session
from app.crud import client as crud_client
from app.crud import student as crud_student
from app.crud import user as crud_user
from app.schemas.user import ClientCreate
from app.schemas.student import StudentCreate
from app.models.user import User
from app.models.student import Student
from datetime import datetime

logger = logging.getLogger(__name__)

class ClientService:



    def create_client_with_students(self, db: Session, client_data: ClientCreate) -> User:
        # 1. Check for existing user
        existing_user = crud_user.get_user_by_email(db, email=client_data.email)
        if existing_user:
            raise ValueError("User with this email already exists")

        # 2. Create the client (User)
        client = crud_client.create_client(db, client_data)
        logger.info(f'client is_Student value: {client_data.is_student}')

        # 3. If client is also a student, create a student record for them
        if client_data.is_student:
            student_for_client_data = StudentCreate(
                first_name=client.first_name,
                last_name=client.last_name,
                date_of_birth=client.date_of_birth,
                client_id=client.id
            )
            logger.info("Calling create student crud function")
            crud_student.create_student(db, student_data=student_for_client_data, client_id=client.id)

        # 4. Create student records for dependent students (children)
        if client_data.students:
            for student_data in client_data.students:
                crud_student.create_student(db, student_data=student_data, client_id=client.id)

        # 5. Commit the transaction
        db.commit()
        db.refresh(client)
        return client

    def update_client_status(self, db: Session, client_id: int, is_active: bool) -> tuple[User, int]:
        client = crud_client.get_client_by_id(db, client_id)
        if not client:
            raise ValueError("Клиент не найден")
        
        client.is_active = is_active
        client.deactivation_date = datetime.now() if not is_active else None
        
        affected_students_count = 0
        if not is_active:
            students = db.query(Student).filter(Student.client_id == client_id).all()
            for student in students:
                student.is_active = False
                student.deactivation_date = datetime.now()
                affected_students_count += 1
        
        db.commit()
        db.refresh(client)
        return client, affected_students_count

client_service = ClientService()
