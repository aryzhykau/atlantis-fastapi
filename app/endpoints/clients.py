from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.entities.pagination.schemas import PaginatedResponse
from app.entities.users.models import User
from app.entities.users.schemas import ClientCreate, ClientRead, ClientUpdate
from typing import List, Any
from app.auth.jwt_handler import verify_jwt_token
from app.entities.users.models import UserRoleEnum
from app.entities.users.crud import create_user, delete_user_by_id, \
    get_users_by_role_paginated, get_all_users_by_role, update_user
import logging

router = APIRouter()

logger = logging.getLogger(__name__)

# Получить всех клиентов
@router.get("/", response_model=List[Any])
def get_clients(current_user: dict = Depends(verify_jwt_token),db: Session = Depends(get_db)):
    if current_user["role"] == UserRoleEnum.ADMIN:
        logger.debug("Authorised for clients request")
        users =  get_all_users_by_role(db, UserRoleEnum.CLIENT)
        logger.debug(UserRoleEnum.CLIENT.value)
        return users if users else []
    else:
        raise HTTPException(status_code=401, detail="Unauthorized")


# # Получить клиента по ID
# @router.get("/clients/{client_id}", response_model=ClientRead)
# def get_client(client_id: int, db: Session = Depends(get_db)):
#     client = db.query(User).filter(User.id == client_id).first()
#     if not client:
#         raise HTTPException(status_code=404, detail="Клиент не найден")
#     return client
#
#
# Создать клиента
@router.post("/", response_model=ClientRead)
def create_client(client_data: ClientCreate, current_user: dict = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] == UserRoleEnum.ADMIN:
        logger.debug(client_data)
        client_data.google_authenticated = True
        new_client = create_user(db, client_data)
        logger.debug(new_client)
        return new_client


# Удалить клиента
@router.delete("/{client_id}")
def delete_client(client_id: int, current_user: dict = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] == UserRoleEnum.ADMIN:
        logger.debug(f"Deleting client with id: {client_id}" )
        return delete_user_by_id(db, client_id)


# Обновить данные клиента
@router.put("/{client_id}", response_model=ClientRead)
def update_client(client_id: int, client_data: ClientCreate, current_user: dict = Depends(verify_jwt_token),
                  db: Session = Depends(get_db)):
    if current_user["role"] == UserRoleEnum.ADMIN:
        client_to_update = update_user(db,client_id, client_data)
        logger.debug(client_to_update)
        return client_to_update
    else:
        raise HTTPException(status_code=403, detail="Unauthorized")
