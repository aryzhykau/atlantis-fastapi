from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.schemas.user import UserRole
from app.schemas.student import StudentCreate, StudentResponse, StudentUpdate
from app.crud.student import (create_student, get_students, get_student_by_id,
                              update_student)

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