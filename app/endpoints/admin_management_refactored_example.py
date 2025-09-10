"""
Refactored admin_management.py using the simple role-based system.
This shows the before/after comparison.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

# NEW: Import the simple get_current_user dependency
from app.auth.permissions import get_current_user
from app.dependencies import get_db
from app.schemas.user import (
    AdminCreate, AdminUpdate, AdminResponse, AdminStatusUpdate, 
    AdminsList, UserRole
)
from app.crud.admin import (
    get_admin_by_id, get_all_admins, create_admin, update_admin,
    update_admin_status, admin_exists_by_email
)

router = APIRouter(prefix="/admin-management", tags=["Admin Management"])

# OLD WAY - Remove this helper function
# def verify_owner_access(current_user) -> None:
#     """Helper function to verify OWNER role access"""
#     if current_user["role"] != UserRole.OWNER:
#         raise HTTPException(
#             status_code=403, 
#             detail="Only OWNER can manage administrators"
#         )


# REFACTORED ENDPOINTS

@router.get("/admins", response_model=AdminsList)
def get_admins_endpoint(
    # OLD: current_user = Depends(verify_jwt_token), 
    # NEW: Use get_current_user with required roles
    current_user = Depends(get_current_user(["OWNER"])),
    db: Session = Depends(get_db)
):
    """Get all administrators (OWNER only)"""
    # OLD: verify_owner_access(current_user)  # Remove this line
    # NEW: Role check is already done by the dependency
    
    admins = get_all_admins(db)
    return AdminsList(admins=admins)


@router.get("/admins/{admin_id}", response_model=AdminResponse)
def get_admin_endpoint(
    admin_id: int,
    # OLD: current_user = Depends(verify_jwt_token),
    # NEW: Use get_current_user with required roles
    current_user = Depends(get_current_user(["OWNER"])),
    db: Session = Depends(get_db)
):
    """Get administrator by ID (OWNER only)"""
    # OLD: verify_owner_access(current_user)  # Remove this line
    # NEW: Role check is already done by the dependency
    
    admin = get_admin_by_id(db, admin_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Administrator not found")
    return admin


@router.post("/admins", response_model=AdminResponse)
def create_admin_endpoint(
    admin_data: AdminCreate,
    # NEW: Only OWNER can create admins
    current_user = Depends(get_current_user(["OWNER"])),
    db: Session = Depends(get_db)
):
    """Create new administrator (OWNER only)"""
    # No manual role check needed - dependency handles it
    
    if admin_exists_by_email(db, admin_data.email):
        raise HTTPException(
            status_code=409, 
            detail="Administrator with this email already exists"
        )
    
    admin = create_admin(db, admin_data)
    return admin


@router.put("/admins/{admin_id}", response_model=AdminResponse)
def update_admin_endpoint(
    admin_id: int,
    admin_data: AdminUpdate,
    # NEW: Only OWNER can update admins
    current_user = Depends(get_current_user(["OWNER"])),
    db: Session = Depends(get_db)
):
    """Update administrator (OWNER only)"""
    # No manual role check needed
    
    admin = update_admin(db, admin_id, admin_data)
    if not admin:
        raise HTTPException(status_code=404, detail="Administrator not found")
    return admin


# Example: If you wanted to allow both OWNER and ADMIN to view admins
@router.get("/admins-viewable", response_model=AdminsList)
def get_admins_viewable_endpoint(
    # Allow both OWNER and ADMIN to view
    current_user = Depends(get_current_user(["OWNER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Get all administrators (OWNER and ADMIN can view)"""
    admins = get_all_admins(db)
    return AdminsList(admins=admins)


# Example: Public endpoint that still needs authentication but any role
@router.get("/admin-count")
def get_admin_count_endpoint(
    # Any authenticated user can see the count
    current_user = Depends(get_current_user()),
    db: Session = Depends(get_db)
):
    """Get count of administrators (any authenticated user)"""
    admins = get_all_admins(db)
    return {"admin_count": len(admins)}
