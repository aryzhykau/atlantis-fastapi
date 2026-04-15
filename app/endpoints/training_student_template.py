from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.permissions import get_current_user
from app.dependencies import get_db
from app.models import User
from app.schemas.training_template import (
    TrainingStudentTemplateCreate,
    TrainingStudentTemplateUpdate,
    TrainingStudentTemplateResponse,
)
from app.schemas.subscription_v2 import TemplateAddStudentResponse
from app.crud.training_template import (
    get_training_student_templates,
    get_training_student_template_by_id,
    create_training_student_template,
    update_training_student_template,
    delete_training_student_template,
)
from app.crud.subscription_v2 import get_pending_schedule_subscription, count_student_active_templates

router = APIRouter(prefix="/training_student_templates", tags=["Training Student Templates"])


# Получение списка всех студент-шаблонов
@router.get("/", response_model=list[TrainingStudentTemplateResponse])
def read_training_student_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user(["ADMIN", "OWNER"]))
):
    return get_training_student_templates(db=db)


# Получение студент-шаблона по ID
@router.get("/{student_template_id}", response_model=TrainingStudentTemplateResponse)
def read_training_student_template(
    student_template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user(["ADMIN", "OWNER"]))
):
    student_template = get_training_student_template_by_id(db=db, student_template_id=student_template_id)
    if not student_template:
        raise HTTPException(status_code=404, detail="Training student template not found")
    return student_template


# Создание нового студент-шаблона
@router.post("/", response_model=TemplateAddStudentResponse)
def create_training_student_template_endpoint(
    training_student_template: TrainingStudentTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user(["ADMIN", "OWNER"]))
):
    student_id = training_student_template.student_id

    # Запоминаем состояние до добавления
    pending_sub_before = get_pending_schedule_subscription(db, student_id)

    result = create_training_student_template(db=db, student_template_data=training_student_template)

    # Проверяем активировался ли абонемент
    subscription_activated = False
    sessions_left_to_add = None
    if pending_sub_before:
        # Перечитываем — если schedule_confirmed_at появился, значит триггер сработал
        db.refresh(pending_sub_before)
        subscription_activated = pending_sub_before.schedule_confirmed_at is not None
        if not subscription_activated:
            sessions_per_week = pending_sub_before.subscription.sessions_per_week or 1
            templates_added = count_student_active_templates(db, student_id)
            sessions_left_to_add = max(0, sessions_per_week - templates_added)

    return TemplateAddStudentResponse(
        id=result.id,
        training_template_id=result.training_template_id,
        student_id=result.student_id,
        start_date=result.start_date,
        subscription_activated=subscription_activated,
        subscription_sessions_left_to_add=sessions_left_to_add,
    )


# Обновление существующего студент-шаблона
@router.put("/{student_template_id}", response_model=TrainingStudentTemplateResponse)
def update_training_student_template_endpoint(
    student_template_id: int,
    training_student_template: TrainingStudentTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user(["ADMIN", "OWNER"]))
):
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
    current_user: User = Depends(get_current_user(["ADMIN", "OWNER"]))
):
    deleted_student_template = delete_training_student_template(db=db, student_template_id=student_template_id)
    if not deleted_student_template:
        raise HTTPException(status_code=404, detail="Training student template not found")
    return deleted_student_template