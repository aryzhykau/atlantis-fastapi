from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.permissions import get_current_user
from app.dependencies import get_db
from app.schemas.user import UserRole
from app.models.client_contact_task import ClientContactReason as ModelReason, ClientContactStatus as ModelStatus
from app.schemas.client_contact_task import (
    ClientContactTaskCreate,
    ClientContactTaskUpdate,
    ClientContactTaskResponse,
    ClientContactReason as SchemaReason,
    ClientContactStatus as SchemaStatus,
)
from app.services.client_contact import ClientContactService


router = APIRouter(prefix="/client-contacts", tags=["ClientContacts"])


def _to_model_reason(reason: Optional[SchemaReason]) -> Optional[ModelReason]:
    return ModelReason(reason.value) if reason is not None else None


def _to_model_status(status: Optional[SchemaStatus]) -> Optional[ModelStatus]:
    return ModelStatus(status.value) if status is not None else None


@router.get("/", response_model=list[ClientContactTaskResponse])
def list_client_contact_tasks(
    status: Optional[SchemaStatus] = None,
    reason: Optional[SchemaReason] = None,
    assigned_to_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user(["ADMIN", "OWNER"])),
):
    service = ClientContactService(db)
    items = service.list_tasks(
        status=_to_model_status(status),
        reason=_to_model_reason(reason),
        assigned_to_id=assigned_to_id,
        limit=limit,
        offset=offset,
    )
    return items


@router.post("/", response_model=ClientContactTaskResponse, status_code=201)
def create_client_contact_task(
    data: ClientContactTaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user(["ADMIN", "OWNER"])),
):
    service = ClientContactService(db)
    task = service.create_task(
        client_id=data.client_id,
        reason=ModelReason(data.reason.value),
        note=data.note,
        assigned_to_id=data.assigned_to_id,
        last_activity_at=data.last_activity_at,
    )
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=ClientContactTaskResponse)
def update_client_contact_task(
    task_id: int,
    data: ClientContactTaskUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user(["ADMIN", "OWNER"])),
):
    service = ClientContactService(db)

    task = None
    if data.status is not None:
        if data.status == SchemaStatus.DONE:
            task = service.mark_done(task_id, note=data.note, assigned_to_id=data.assigned_to_id)
        elif data.status == SchemaStatus.PENDING:
            # Простое обновление к PENDING
            from app.models.client_contact_task import ClientContactTask
            task = db.query(ClientContactTask).get(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            task.status = ModelStatus.PENDING
            task.done_at = None
            if data.note is not None:
                task.note = data.note
            if data.assigned_to_id is not None:
                task.assigned_to_id = data.assigned_to_id
            db.flush()
    else:
        from app.models.client_contact_task import ClientContactTask
        task = db.query(ClientContactTask).get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if data.note is not None:
            task.note = data.note
        if data.assigned_to_id is not None:
            task.assigned_to_id = data.assigned_to_id
        db.flush()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.commit()
    db.refresh(task)
    return task


