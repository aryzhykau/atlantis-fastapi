from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.auth.jwt_handler import verify_jwt_token
from app.models import User, UserRole
from app.schemas.training_template import (
    TrainingStudentTemplateCreate,
    TrainingStudentTemplateUpdate,
    TrainingStudentTemplateResponse,
)
from app.crud.training_template import (
    get_training_student_templates,
    get_training_student_template_by_id,
    create_training_student_template,
    update_training_student_template,
    delete_training_student_template,
)

router = APIRouter(prefix="/training_student_templates", tags=["Training Student Templates"])


# Получение списка всех студент-шаблонов
@router.get("/", response_model=list[TrainingStudentTemplateResponse])
def read_training_student_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_jwt_token)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return get_training_student_templates(db=db)


# Получение студент-шаблона по ID
@router.get("/{student_template_id}", response_model=TrainingStudentTemplateResponse)
def read_training_student_template(
    student_template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_jwt_token)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    student_template = get_training_student_template_by_id(db=db, student_template_id=student_template_id)
    if not student_template:
        raise HTTPException(status_code=404, detail="Training student template not found")
    return student_template


# Создание нового студент-шаблона
@router.post("/", response_model=TrainingStudentTemplateResponse)
def create_training_student_template_endpoint(
    training_student_template: TrainingStudentTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_jwt_token)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return create_training_student_template(db=db, student_template=training_student_template)


# Обновление существующего студент-шаблона
@router.put("/{student_template_id}", response_model=TrainingStudentTemplateResponse)
def update_training_student_template_endpoint(
    student_template_id: int,
    training_student_template: TrainingStudentTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_jwt_token)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    updated_student_template = update_training_student_template(
        db=db, student_template_id=student_template_id, update_data=training_student_template
    )
    if not updated_student_template:
        raise HTTPException(status_code=404, detail="Training student template not found")
    return updated_student_template


# Удаление студент-шаблона
@router.delete("/{student_template_id}", response_model=TrainingStudentTemplateResponse)
def delete_training_student_template_endpoint(
    student_template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_jwt_token)
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    deleted_student_template = delete_training_student_template(db=db, student_template_id=student_template_id)
    if not deleted_student_template:
        raise HTTPException(status_code=404, detail="Training student template not found")
    return deleted_student_template