import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.schemas.user import ClientCreate, ClientResponse, ClientUpdate, UserRole, StatusUpdate, ClientStatusResponse
from app.schemas.student import StudentResponse
from app.crud import client as crud_client
from app.crud import student as crud_student
from app.services.client_service import client_service

router = APIRouter(prefix="/clients", tags=["Clients"])

logger = logging.getLogger(__name__)

@router.post("/", response_model=ClientResponse, status_code=201)
def create_client_endpoint(client_data: ClientCreate, db: Session = Depends(get_db), current_user=Depends(verify_jwt_token)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can create clients")
    try:
        logger.info("calling create user")
        return client_service.create_client_with_students(db, client_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=list[ClientResponse])
def get_clients_endpoint(db: Session = Depends(get_db), current_user=Depends(verify_jwt_token)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can view clients")
    return crud_client.get_all_clients(db)


@router.get("/{client_id}", response_model=ClientResponse)
def get_client_endpoint(client_id: int, db: Session = Depends(get_db), current_user=Depends(verify_jwt_token)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can view client info")
    client = crud_client.get_client_by_id(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.get("/{client_id}/students", response_model=List[StudentResponse])
def get_client_students_endpoint(client_id: int, db: Session = Depends(get_db), current_user=Depends(verify_jwt_token)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can view client students")
    client = crud_client.get_client_by_id(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return crud_student.get_students_by_client_id(db, client_id)


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client_endpoint(client_id: int, client_data: ClientUpdate, db: Session = Depends(get_db), current_user=Depends(verify_jwt_token)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can update clients")
    # This should be moved to a service in the future
    updated_client = crud_client.update_client(db, client_id, client_data)
    if not updated_client:
        raise HTTPException(status_code=404, detail="Client not found")
    db.commit()
    db.refresh(updated_client)
    return updated_client


@router.delete("/{client_id}", response_model=ClientResponse)
def delete_client_endpoint(client_id: int, db: Session = Depends(get_db), current_user=Depends(verify_jwt_token)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can delete clients")
    # This should be moved to a service in the future
    deleted_client = crud_client.delete_client(db, client_id)
    if not deleted_client:
        raise HTTPException(status_code=404, detail="Client not found")
    db.commit()
    return deleted_client


@router.patch("/{client_id}/status", response_model=ClientStatusResponse)
def update_client_status_endpoint(client_id: int, status_update: StatusUpdate, db: Session = Depends(get_db), current_user=Depends(verify_jwt_token)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can change client status")
    # This should be moved to a service in the future
    client, affected_count = client_service.update_client_status(db, client_id, status_update.is_active)
    return {
        "id": client.id,
        "is_active": client.is_active,
        "deactivation_date": client.deactivation_date,
        "affected_students_count": affected_count if not status_update.is_active else None
    }
