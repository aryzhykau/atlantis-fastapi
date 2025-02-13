from sqlalchemy.orm import Session
from pydantic import EmailStr
from app.entities.users.models import User

def get_user_by_email(db: Session, email: EmailStr):
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, id: int):
    return db.query(User).filter(User.id == id).first()










