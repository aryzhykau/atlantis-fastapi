from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import current_user

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.schemas.user import ClientCreate, ClientResponse, ClientUpdate, UserRole
from app.crud.client import (create_client, get_client, get_all_clients,
                             update_client, delete_client)

router = APIRouter(prefix="/clients", tags=["Clients"])


# Создание клиента
@router.post("/", response_model=ClientResponse)
def create_client_endpoint(client_data: ClientCreate, current_user = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    new_client = create_client(db, client_data)
    return new_client


# Получение списка клиентов
@router.get("/", response_model=list[ClientResponse])
def get_clients_endpoint(current_user = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    return get_all_clients(db)


# Получение клиента по ID
@router.get("/{client_id}", response_model=ClientResponse)
def get_client_endpoint(client_id: int, current_user = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    client = get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


# Обновление клиента
@router.patch("/{client_id}", response_model=ClientResponse)
def update_client_endpoint(client_id: int, client_data: ClientUpdate,current_user = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    client = update_client(db, client_id, client_data)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


# Удаление клиента
@router.delete("/{client_id}", response_model=ClientResponse)
def delete_client_endpoint(client_id: int, current_user = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    client = delete_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client