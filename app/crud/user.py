from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import User
from app.schemas.user import UserUpdate


# Get user by ID
def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


# Get user by email
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Get a user by email
    """
    return db.query(User).filter(User.email == email).first()


# Get all users for autocomplete
def get_all_users(db: Session) -> List[User]:
    """
    Get all users for autocomplete
    """
    return db.query(User).order_by(User.first_name, User.last_name).all()


# Get active users
def get_active_users(db: Session) -> List[User]:
    """
    Get active users
    """
    return db.query(User).filter(User.is_active == True).order_by(User.first_name, User.last_name).all()


# Get users by role
def get_users_by_role(db: Session, role: str) -> List[User]:
    """
    Get users by role
    """
    return db.query(User).filter(User.role == role).order_by(User.first_name, User.last_name).all()


# Update user balance
def update_user(db: Session, user_id: int, user_in: UserUpdate) -> Optional[User]:
    """
    Update an existing user
    """
    user = get_user(db, user_id)
    if not user:
        return None

    update_data = user_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    return user





# Delete user
def delete_user(db: Session, user_id: int) -> Optional[User]:
    """
    Delete a user by ID
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        db.delete(user)
        return user
    return None