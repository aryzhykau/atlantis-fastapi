"""
Updated user endpoints using the new role-based authorization system.
This demonstrates practical migration from old role checking to new system.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.dependencies import get_db
from app.auth.permissions import get_current_user
from app.schemas.user import UserMe, UserRole, UserListResponse
from app.crud.user import get_user_by_id, get_all_users
from app.auth.jwt_handler import verify_jwt_token

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=List[UserListResponse])
def get_users_list(
    current_user = Depends(get_current_user(["ADMIN", "OWNER"])),  # ✅ Clean role dependency
    db: Session = Depends(get_db)
):
    """Get a list of users for autocomplete (admins and owners)"""
    # OLD CODE ❌:
    # if current_user["role"] != UserRole.ADMIN:
    #     raise HTTPException(status_code=403, detail="Forbidden")
    
    # Role checking is now handled by the get_current_user dependency
    return get_all_users(db)


@router.get("/me", response_model=UserMe)  
def get_current_user(
    current_user = Depends(verify_jwt_token),  # Any authenticated user
    db: Session = Depends(get_db)
):
    """Get current user's profile - any authenticated user can access"""
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
        phone_country_code=user.phone_country_code,
        phone_number=user.phone_number,
        role=user.role,
        is_authenticated_with_google=user.is_authenticated_with_google
    )


@router.get("/{user_id}/profile", response_model=UserMe)
def get_user_profile(
    user_id: int,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Get user profile by ID.
    Users can access their own profile, admins can access any profile.
    """
    from app.dependencies import require_self_access_or_role
    
    # ✅ Clean self-access or role checking
    require_self_access_or_role(
        current_user=current_user,
        resource_user_id=user_id,
        required_roles=UserRole.ADMIN,  # Admins can access any profile
        error_message="You can only access your own profile"
    )
    
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserMe(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone_country_code=user.phone_country_code,
        phone_number=user.phone_number,
        role=user.role,
        is_authenticated_with_google=user.is_authenticated_with_google
    )
