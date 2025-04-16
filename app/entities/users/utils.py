import email
from datetime import datetime

from sqlalchemy.orm import Session

from app.entities.users.errors import UserEmailAlreadyExistError, UserPhoneAlreadyExistError
from app.entities.users.models import  User


def check_existing_user_email(db: Session, email: str):
    existing_user = db.query(User).filter(email=email).first()
    if existing_user:
        raise UserEmailAlreadyExistError

def check_existing_user_phone(db: Session, phone: str):
    existing_user = db.query(User).filter(phone=phone).first()
    if existing_user:
        raise UserPhoneAlreadyExistError




