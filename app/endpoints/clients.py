import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.entities.invoices.crud import create_invoice
from app.entities.invoices.models import InvoiceTypeEnum
from app.entities.invoices.schemas import InvoiceCreate, InvoiceRead
from app.entities.users.crud import create_user, delete_user_by_id, \
    get_all_users_by_role, update_user, create_client_subscription
from app.entities.users.models import UserRoleEnum
from app.entities.users.schemas import ClientCreate, ClientRead, ClientSubscriptionCreate, ClientSubscriptionRead

router = APIRouter()

logger = logging.getLogger(__name__)

# Получить всех клиентов
@router.get("/", response_model=List[ClientRead])
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
        client_to_update = update_user(db, client_id, client_data)
        logger.debug(client_to_update)
        return client_to_update
    else:
        raise HTTPException(status_code=403, detail="Unauthorized")


# Добавить подписку клиенту
@router.post("/{client_id}/subscriptions")
def add_subscription_to_client(client_id: int, client_subscription_data: ClientSubscriptionCreate, current_user: dict = Depends(verify_jwt_token),
                               db: Session = Depends(get_db)):
    if current_user["role"] == UserRoleEnum.ADMIN:
        logger.debug(f"Adding subscription to client with id: {client_id}")
        subscription = create_client_subscription(db, client_id, client_subscription_data)
        subscription_schema = ClientSubscriptionRead.model_validate(subscription)
        invoice_create_schema = InvoiceCreate(
            user_id=client_id,
            client_subscription_id=subscription_schema.id,
            amount=subscription_schema.subscription.price,
            invoice_type=InvoiceTypeEnum.SUBSCRIPTION.value
        )
        invoice = create_invoice(db, invoice_create_schema)
        logger.debug(
            f"Invoice for subscription with id: {subscription_schema.id} created for client with id: {client_id}"
        )
        invoice_read_schema = InvoiceRead.model_validate(invoice)

        if not subscription:
            raise HTTPException(status_code=404, detail="Client or Subscription not found")
        return {"subscription": subscription_schema, "invoice": invoice_read_schema, "client_id": client_id}
