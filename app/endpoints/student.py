from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.schemas.user import UserRole, StatusUpdate, StudentStatusResponse
from app.schemas.student import (StudentCreate, StudentResponse, StudentUpdate,
                              StudentCreateWithoutClient)
from app.schemas.payment import PaymentHistoryResponse
from app.crud.student import (create_student, get_students, get_student_by_id,
                              update_student, update_student_status, get_students_by_client_id)
from app.models.user import User
from app.models.payment_history import PaymentHistory
from app.models.student import Student
from app.models.real_training import RealTraining, RealTrainingStudent

router = APIRouter(prefix="/students", tags=["Students"])


# Создание студента
@router.post("/", response_model=StudentResponse)
def create_student_endpoint(
        student_data: StudentCreate,
        current_user=Depends(verify_jwt_token),
        db: Session = Depends(get_db),
):
    # Проверка прав доступа
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Создание студента
    try:
        new_student = create_student(db, student_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return new_student


# Получение списка студентов
@router.get("/", response_model=list[StudentResponse])
def get_students_endpoint(
        current_user=Depends(verify_jwt_token),
        db: Session = Depends(get_db),
):
    # Проверка прав доступа
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Получение списка студентов
    students = get_students(db)
    return students


# Получение студента по ID
@router.get("/{student_id}", response_model=StudentResponse)
def get_student_endpoint(
        student_id: int,
        current_user=Depends(verify_jwt_token),
        db: Session = Depends(get_db),
):
    # Проверка прав доступа
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")

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
        current_user=Depends(verify_jwt_token),
        db: Session = Depends(get_db),
):
    # Проверка прав доступа
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")

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
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Обновляет статус студента.
    При попытке активации проверяет статус родительского клиента.
    """
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Только администратор может изменять статус студентов")
    
    # Сначала проверяем существование студента
    student = get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Студент не найден")
    
    try:
        student = update_student_status(db, student_id, status_update.is_active)
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
    current_user=Depends(verify_jwt_token),
    db: Session = Depends(get_db),
):
    """Получение списка студентов для конкретного клиента"""
    # Проверка прав доступа
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")

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
    current_user=Depends(verify_jwt_token),
    db: Session = Depends(get_db),
):
    """Получение истории платежей для конкретного студента"""
    # Проверка прав доступа
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")

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
    current_user=Depends(verify_jwt_token),
    db: Session = Depends(get_db),
):
    """
    Получение всех активных студентов для регистрации платежей
    Доступно только тренерам и админам
    """
    if current_user["role"] not in [UserRole.ADMIN, UserRole.TRAINER]:
        raise HTTPException(status_code=403, detail="Forbidden")
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