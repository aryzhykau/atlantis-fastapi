from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.auth.permissions import get_current_user
from app.dependencies import get_db
from app.schemas.user import UserRole, StatusUpdate, StudentStatusResponse
from app.schemas.student import (StudentCreate, StudentResponse, StudentUpdate)
from app.schemas.payment import PaymentHistoryResponse
from app.crud.student import (create_student, get_all_students, get_student_by_id,
                              update_student, get_students_by_client_id)
from app.services.student_service import student_service
from app.models.user import User
from app.models.payment_history import PaymentHistory
from app.models.student import Student

router = APIRouter(prefix="/students", tags=["Students"])


# Создание студента
@router.post("/", response_model=StudentResponse)
def create_student_endpoint(
        student_data: StudentCreate,
        current_user=Depends(get_current_user(["ADMIN", "OWNER"])),
        db: Session = Depends(get_db),
):

    # Создание студента
    try:
        new_student = create_student(db, student_data, student_data.client_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return new_student


# Получение списка студентов
@router.get("/", response_model=list[StudentResponse])
def get_students_endpoint(
        current_user=Depends(get_current_user(["ADMIN", "OWNER", "TRAINER"])),
        db: Session = Depends(get_db),
):

    # Получение списка студентов
    students = get_all_students(db)
    return students


# Получение студента по ID
@router.get("/{student_id}", response_model=StudentResponse)
def get_student_endpoint(
        student_id: int,
        current_user=Depends(get_current_user(["ADMIN", "OWNER"])),
        db: Session = Depends(get_db),
):
    # Получение студента
    student = get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


# Обновление информации о студенте
@router.patch("/{student_id}", response_model=StudentResponse)
def update_student_endpoint(
        student_id: int,
        student_data: StudentUpdate,
        current_user=Depends(get_current_user(["ADMIN", "OWNER"])),
        db: Session = Depends(get_db),
):

    # Обновление данных студента
    try:
        student = update_student(db, student_id, student_data)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return student


@router.patch("/{student_id}/status", response_model=StudentStatusResponse,
            description="Обновление статуса студента")
def update_student_status_endpoint(
    student_id: int,
    status_update: StatusUpdate,
    current_user = Depends(get_current_user(["ADMIN", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Обновляет статус студента.
    При попытке активации проверяет статус родительского клиента.
    """
    
    try:
        student = student_service.update_student_status(db, student_id, status_update.is_active)
        client = db.query(User).filter(User.id == student.client_id).first()
        
        return StudentStatusResponse(
            id=student.id,
            is_active=student.is_active,
            deactivation_date=student.deactivation_date,
            client_status=client.is_active if client else False
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Получение студентов по ID клиента
@router.get("/client/{client_id}", response_model=list[StudentResponse])
def get_students_by_client_endpoint(
    client_id: int,
    current_user=Depends(get_current_user(["ADMIN", "OWNER"])),
    db: Session = Depends(get_db),
):
    """Получение списка студентов для конкретного клиента"""

    # Проверяем существование клиента
    client = db.query(User).filter(User.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail=f"Client with ID {client_id} not found")

    # Получение списка студентов
    students = get_students_by_client_id(db, client_id)
    return students


# Получение истории платежей студента
@router.get("/{student_id}/payments", response_model=list[PaymentHistoryResponse])
def get_student_payments_endpoint(
    student_id: int,
    current_user=Depends(get_current_user(["ADMIN", "OWNER"])),
    db: Session = Depends(get_db),
):
    """Получение истории платежей для конкретного студента"""

    # Проверяем существование студента
    student = get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student with ID {student_id} not found")

    # Получаем историю платежей
    payments = db.query(PaymentHistory).filter(
        PaymentHistory.client_id == student.client_id
    ).order_by(desc(PaymentHistory.created_at)).all()

    return payments


@router.get("/trainer/{trainer_id}", response_model=list[StudentResponse])
def get_students_by_trainer_endpoint(
    trainer_id: int,
    current_user=Depends(get_current_user(["ADMIN", "TRAINER", "OWNER"])),
    db: Session = Depends(get_db),
):
    """
    Получение всех активных студентов для регистрации платежей
    Доступно только тренерам и админам
    """
    if current_user["role"] == UserRole.TRAINER and current_user["id"] != trainer_id:
        raise HTTPException(status_code=403, detail="Можно смотреть только своих студентов")
    
    # Получаем всех активных студентов
    students = (
        db.query(Student)
        .filter(Student.is_active == True)
        .filter(Student.deactivation_date.is_(None))
        .order_by(Student.first_name, Student.last_name)
        .all()
    )
    
    # Отладка: смотрим структуру данных
    print(f"Found {len(students)} students")
    if students:
        first_student = students[0]
        print(f"First student: {first_student}")
        print(f"First student client: {first_student.client}")
        print(f"First student client_id: {first_student.client_id}")
    
    return students