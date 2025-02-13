# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from app.dependencies import get_db
# from app.entities.users.models import User
# from app.entities.users.schemas import ClientCreate, ClientRead
# from typing import List
#
# router = APIRouter()
#
#
# # Получить всех клиентов
# @router.get("/clients", response_model=List[ClientRead])
# def get_clients(db: Session = Depends(get_db)):
#     return db.query(User).all()
#
#
# # Получить клиента по ID
# @router.get("/clients/{client_id}", response_model=ClientRead)
# def get_client(client_id: int, db: Session = Depends(get_db)):
#     client = db.query(User).filter(User.id == client_id).first()
#     if not client:
#         raise HTTPException(status_code=404, detail="Клиент не найден")
#     return client
#
#
# # Создать клиента
# @router.post("/clients", response_model=ClientRead)
# def create_client(client_data: ClientCreate, db: Session = Depends(get_db)):
#     client = User(**client_data.dict())
#     db.add(client)
#     db.commit()
#     db.refresh(client)
#     return client
#
#
# # Удалить клиента
# @router.delete("/clients/{client_id}")
# def delete_client(client_id: int, db: Session = Depends(get_db)):
#     client = db.query(Client).filter(Client.id == client_id).first()
#     if not client:
#         raise HTTPException(status_code=404, detail="Клиент не найден")
#
#     db.delete(client)
#     db.commit()
#     return {"message": "Клиент удалён"}
#
