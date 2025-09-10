from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.auth.jwt_handler import verify_jwt_token
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


def verify_owner_access(current_user) -> None:
    """Helper function to verify OWNER role access"""
    if current_user["role"] != UserRole.OWNER:
        raise HTTPException(
            status_code=403, 
            detail="Only OWNER can manage administrators"
        )


@router.get("/admins", response_model=AdminsList)
def get_admins_endpoint(
    current_user = Depends(verify_jwt_token), 
    db: Session = Depends(get_db)
):
    """Get all administrators (OWNER only)"""
    verify_owner_access(current_user)
    
    admins = get_all_admins(db)
    return AdminsList(admins=admins)


@router.get("/admins/{admin_id}", response_model=AdminResponse)
def get_admin_endpoint(
    admin_id: int,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """Get administrator by ID (OWNER only)"""
    verify_owner_access(current_user)
    
    admin = get_admin_by_id(db, admin_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Administrator not found")
    
    return admin


@router.post("/admins", response_model=AdminResponse)
def create_admin_endpoint(
    admin_data: AdminCreate,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """Create a new administrator (OWNER only)"""
    verify_owner_access(current_user)
    
    # Check if admin with email already exists
    if admin_exists_by_email(db, admin_data.email):
        raise HTTPException(
            status_code=400, 
            detail="Administrator with this email already exists"
        )
    
    try:
        admin = create_admin(db, admin_data)
        return admin
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create admin: {str(e)}")


@router.patch("/admins/{admin_id}", response_model=AdminResponse)
def update_admin_endpoint(
    admin_id: int,
    admin_data: AdminUpdate,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """Update administrator information (OWNER only)"""
    verify_owner_access(current_user)
    
    # Check if admin exists
    existing_admin = get_admin_by_id(db, admin_id)
    if not existing_admin:
        raise HTTPException(status_code=404, detail="Administrator not found")
    
    # Check email uniqueness if email is being updated
    if admin_data.email and admin_data.email != existing_admin.email:
        if admin_exists_by_email(db, admin_data.email, exclude_id=admin_id):
            raise HTTPException(
                status_code=400,
                detail="Administrator with this email already exists"
            )
    
    try:
        admin = update_admin(db, admin_id, admin_data)
        if not admin:
            raise HTTPException(status_code=404, detail="Administrator not found")
        return admin
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update admin: {str(e)}")


@router.patch("/admins/{admin_id}/status", response_model=AdminResponse)
def update_admin_status_endpoint(
    admin_id: int,
    status_data: AdminStatusUpdate,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """Enable or disable administrator (OWNER only)"""
    verify_owner_access(current_user)
    
    # Prevent self-deactivation
    if admin_id == current_user["id"] and not status_data.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot deactivate your own account"
        )
    
    try:
        admin = update_admin_status(db, admin_id, status_data.is_active)
        if not admin:
            raise HTTPException(status_code=404, detail="Administrator not found")
        return admin
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update admin status: {str(e)}")
