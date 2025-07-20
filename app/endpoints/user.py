from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.schemas.user import UserMe, UserRole, UserListResponse
from app.crud.user import get_user_by_id, get_all_users

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=List[UserListResponse])
def get_users_list(current_user=Depends(verify_jwt_token), db: Session = Depends(get_db)):
    """Get a list of users for autocomplete (admins only)"""
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    return get_all_users(db)


@router.get("/me", response_model=UserMe)
def get_current_user(current_user=Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not Authenticated")
    user = get_user_by_id(db, current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserMe(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone=user.phone,
        role=user.role
    )
