from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import current_user
from typing import List

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.schemas.user import ClientCreate, ClientResponse, ClientUpdate, UserRole, StatusUpdate, ClientStatusResponse
from app.schemas.student import StudentResponse
from app.crud.client import (create_client, get_client, get_all_clients,
                             update_client, delete_client, update_client_status)
from app.crud.student import get_students_by_client_id

router = APIRouter(prefix="/clients", tags=["Clients"])


# Создание клиента
@router.post("/", response_model=ClientResponse, status_code=201,
            description="Создание нового клиента с возможностью автоматического создания студента из данных клиента "
                      "и добавления дополнительных студентов")
def create_client_endpoint(
    client_data: ClientCreate,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Создает нового клиента с возможностью:
    - Автоматического создания студента из данных клиента (если is_student=True)
    - Добавления дополнительных студентов через поле students
    """
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Только администратор может создавать клиентов")
    try:
        new_client = create_client(db, client_data)
        return new_client
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Получение списка клиентов
@router.get("/", response_model=list[ClientResponse])
def get_clients_endpoint(
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """Получает список всех клиентов."""
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Только администратор может просматривать список клиентов")
    return get_all_clients(db)


# Получение клиента по ID
@router.get("/{client_id}", response_model=ClientResponse)
def get_client_endpoint(
    client_id: int,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """Получает информацию о конкретном клиенте по его ID."""
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Только администратор может просматривать информацию о клиенте")
    client = get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    return client


# Получение студентов клиента
@router.get("/{client_id}/students", response_model=List[StudentResponse])
def get_client_students_endpoint(
    client_id: int,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """Получает список всех студентов, связанных с данным клиентом."""
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Только администратор может просматривать студентов клиента")
    client = get_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    return get_students_by_client_id(db, client_id)


# Обновление клиента
@router.patch("/{client_id}", response_model=ClientResponse)
def update_client_endpoint(
    client_id: int,
    client_data: ClientUpdate,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """Обновляет информацию о клиенте."""
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Только администратор может обновлять информацию о клиенте")
    try:
        client = update_client(db, client_id, client_data)
        if not client:
            raise HTTPException(status_code=404, detail="Клиент не найден")
        return client
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Удаление клиента
@router.delete("/{client_id}", response_model=ClientResponse)
def delete_client_endpoint(
    client_id: int,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """Удаляет клиента и всех связанных с ним студентов."""
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Только администратор может удалять клиентов")
    client = delete_client(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    return client


@router.patch("/{client_id}/status", response_model=ClientStatusResponse,
            description="Обновление статуса клиента с каскадным обновлением статусов связанных студентов")
def update_client_status_endpoint(
    client_id: int,
    status_update: StatusUpdate,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Обновляет статус клиента и каскадно обновляет статусы всех связанных студентов.
    При деактивации клиента все его студенты также становятся неактивными.
    """
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Только администратор может изменять статус клиентов")
    
    try:
        client, affected_count = update_client_status(db, client_id, status_update.is_active)
        return {
            "id": client.id,
            "is_active": client.is_active,
            "deactivation_date": client.deactivation_date,
            "affected_students_count": affected_count if not status_update.is_active else None
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))