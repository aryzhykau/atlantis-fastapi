"""
Example showing how to use the simple role-based get_current_user dependency.
"""

from fastapi import APIRouter, Depends
from app.auth.permissions import get_current_user

router = APIRouter(prefix="/example", tags=["example"])


@router.get("/public")
def public_endpoint():
    """Public endpoint - no authentication required"""
    return {"message": "This is public"}


@router.get("/authenticated")  
def authenticated_endpoint(current_user = Depends(get_current_user())):
    """Requires authentication but any role is allowed"""
    return {
        "message": "You are authenticated", 
        "user_id": current_user["id"],
        "role": current_user["role"]
    }


@router.get("/admin-only")
def admin_only_endpoint(current_user = Depends(get_current_user(["ADMIN"]))):
    """Only ADMIN role can access"""
    return {
        "message": "Admin access granted",
        "user_id": current_user["id"]
    }


@router.get("/owner-only") 
def owner_only_endpoint(current_user = Depends(get_current_user(["OWNER"]))):
    """Only OWNER role can access"""
    return {
        "message": "Owner access granted", 
        "user_id": current_user["id"]
    }


@router.get("/admin-or-owner")
def admin_or_owner_endpoint(current_user = Depends(get_current_user(["ADMIN", "OWNER"]))):
    """Both ADMIN and OWNER roles can access"""
    return {
        "message": "Admin or Owner access granted",
        "user_id": current_user["id"],
        "role": current_user["role"]
    }


@router.get("/trainer-admin-owner")
def multiple_roles_endpoint(current_user = Depends(get_current_user(["TRAINER", "ADMIN", "OWNER"]))):
    """TRAINER, ADMIN, and OWNER roles can access"""
    return {
        "message": "Multiple role access granted",
        "user_id": current_user["id"], 
        "role": current_user["role"]
    }


@router.post("/admin-action")
def admin_action_endpoint(
    current_user = Depends(get_current_user(["ADMIN", "OWNER"]))
):
    """Example of a POST endpoint with role requirements"""
    return {
        "message": f"Action performed by {current_user['role']}",
        "performed_by": current_user["id"]
    }
