from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models import User, UserRole
from app.schemas.user import AdminCreate, AdminUpdate, AdminStatusUpdate


def get_admin_by_id(db: Session, admin_id: int) -> Optional[User]:
    """Get an admin by ID"""
    return db.query(User).filter(
        User.id == admin_id,
        User.role == UserRole.ADMIN
    ).first()


def get_all_admins(db: Session) -> List[User]:
    """Get all active and inactive admins"""
    return db.query(User).filter(User.role == UserRole.ADMIN).all()


def get_active_admins(db: Session) -> List[User]:
    """Get only active admins"""
    return db.query(User).filter(
        User.role == UserRole.ADMIN,
        User.is_active == True
    ).all()


def create_admin(db: Session, admin: AdminCreate) -> User:
    """Create a new admin user"""
    db_admin = User(
        first_name=admin.first_name,
        last_name=admin.last_name,
        date_of_birth=admin.date_of_birth,
        email=admin.email,
        phone_country_code=admin.phone_country_code,
        phone_number=admin.phone_number,
        role=UserRole.ADMIN,
        is_active=True,
        is_authenticated_with_google=True
    )
    
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    
    return db_admin


def update_admin(db: Session, admin_id: int, admin_in: AdminUpdate) -> Optional[User]:
    """Update an existing admin"""
    db_admin = get_admin_by_id(db, admin_id)
    if not db_admin:
        return None
    
    update_data = admin_in.model_dump(exclude_unset=True)
    
    # Directly update the fields without concatenation/splitting
    for field, value in update_data.items():
        setattr(db_admin, field, value)
    
    db.commit()
    db.refresh(db_admin)
    
    return db_admin


def update_admin_status(db: Session, admin_id: int, is_active: bool) -> Optional[User]:
    """Enable or disable an admin (instead of deleting)"""
    db_admin = get_admin_by_id(db, admin_id)
    if not db_admin:
        return None
    
    db_admin.is_active = is_active
    if not is_active:
        db_admin.deactivation_date = datetime.now(timezone.utc)
    else:
        db_admin.deactivation_date = None
    
    db.commit()
    db.refresh(db_admin)
    
    return db_admin


def admin_exists_by_email(db: Session, email: str, exclude_id: Optional[int] = None) -> bool:
    """Check if admin with email already exists"""
    query = db.query(User).filter(
        User.email == email,
        User.role == UserRole.ADMIN
    )
    
    if exclude_id:
        query = query.filter(User.id != exclude_id)
    
    return query.first() is not None
