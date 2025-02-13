# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from app.dependencies import get_db
# from app.entities.users.models import Admin
# from app.entities.users.schemas import AdminCreate, AdminRead
# from app.entities.users import crud
# from typing import List
#
# router = APIRouter()
#
#
# @router.get("/admins", response_model=List[AdminRead])
# def get_admins(db: Session = Depends(get_db)):
#     return crud.get_admins(db)
#
#
# @router.get("/admins/{admin_id}", response_model=AdminRead)
# def get_admin(admin_id: int, db: Session = Depends(get_db)):
#     admin = crud.get_admin_by_id(db,admin_id)
#     if not admin:
#         raise HTTPException(status_code=404, detail="Админ не найден")
#     return admin
#
# @router.get("/admin/email/{email}", response_model=AdminRead)
# def get_admin_by_email(email: str, db: Session = Depends(get_db)):
#     db_admin = crud.get_admin_by_email(db, email=email)
#     if db_admin is None:
#         raise HTTPException(status_code=404, detail="Admin not found")
#     return db_admin
#
# @router.post("/admins", response_model=AdminRead)
# def create_admin(admin_data: AdminCreate, db: Session = Depends(get_db)):
#     admin = crud.create_admin(db, admin_data)
#     return admin
#
#
#
