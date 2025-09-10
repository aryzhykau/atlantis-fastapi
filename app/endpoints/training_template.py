from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.auth.permissions import get_current_user
from app.models import User, UserRole
from app.schemas.training_template import (
    TrainingTemplateCreate,
    TrainingTemplateUpdate,
    TrainingTemplateResponse,
)
from app.crud.training_template import (
    get_training_templates,
    get_training_template_by_id,
    create_training_template,
    update_training_template,
    delete_training_template,
)

router = APIRouter(prefix="/training_templates", tags=["Training Templates"])


# Получение списка всех тренировочных шаблонов с опциональной фильтрацией по дню
@router.get("/", response_model=list[TrainingTemplateResponse])
def read_training_templates(
    day_number: int = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user(["ADMIN", "OWNER"]))
):
    return get_training_templates(db=db, day_number=day_number)


# Получение тренировочного шаблона по ID
@router.get("/{template_id}", response_model=TrainingTemplateResponse)
def read_training_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user(["ADMIN", "OWNER"]))
):
    template = get_training_template_by_id(db=db, template_id=template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Training template not found")
    return template


# Создание нового тренировочного шаблона
@router.post("/", response_model=TrainingTemplateResponse)
def create_training_template_endpoint(
    training_template: TrainingTemplateCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user(["ADMIN", "OWNER"]))
):
    return create_training_template(db=db, training_template=training_template)


# Обновление тренировочного шаблона
@router.put("/{template_id}", response_model=TrainingTemplateResponse)
def update_training_template_endpoint(
    template_id: int,
    training_template: TrainingTemplateUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user(["ADMIN", "OWNER"]))
):
    updated_template = update_training_template(db=db, template_id=template_id, update_data=training_template)
    if not updated_template:
        raise HTTPException(status_code=404, detail="Training template not found")
    return updated_template


# Удаление тренировочного шаблона
@router.delete("/{template_id}")
def delete_training_template_endpoint(
    template_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user(["ADMIN", "OWNER"]))
):
    deleted_template = delete_training_template(db=db, template_id=template_id)
    if not deleted_template:
        raise HTTPException(status_code=404, detail="Training template not found")
    return {"success": True, "id": template_id, "message": "Training template deleted successfully"}