from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import User, UserRole
from app.schemas import UserUpdate, ClientCreate


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Get a user by email
    """
    return db.query(User).filter(User.email == email).first()


def get_all_users(db: Session) -> List[User]:
    """
    Get all users for autocomplete
    """
    return db.query(User).order_by(User.first_name, User.last_name).all()


def get_active_users(db: Session) -> List[User]:
    """
    Get active users
    """
    return db.query(User).filter(User.is_active == True).order_by(User.first_name, User.last_name).all()


def get_users_by_role(db: Session, role: str) -> List[User]:
    """
    Get users by role
    """
    return db.query(User).filter(User.role == role).order_by(User.first_name, User.last_name).all()


def create_user(db: Session, user: ClientCreate) -> User:
    db_user = User(
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=UserRole.CLIENT,
        phone_country_code=user.phone_country_code,
        phone_number=user.phone_number,
        date_of_birth=user.date_of_birth,
        whatsapp_country_code=user.whatsapp_country_code,
        whatsapp_number=user.whatsapp_number,
        is_authenticated_with_google=True,
        balance=0
    )
    db.add(db_user)
    return db_user


def update_user(db: Session, user_id: int, user_in: UserUpdate) -> Optional[User]:
    """
    Update an existing user
    """
    user = get_user_by_id(db, user_id)
    if not user:
        return None

    update_data = user_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    return user


def delete_user(db: Session, user_id: int) -> Optional[User]:
    """
    Delete a user by ID
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)
    return user
