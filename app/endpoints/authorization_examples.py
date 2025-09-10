"""
Example endpoint demonstrating various role-based authorization patterns.
This shows different ways to use the new authorization system.
"""

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import List

from app.dependencies import (
    get_db, 
    RequireOwner, 
    RequireAdmin, 
    RequireAdminOrOwner,
    RequireTrainerOrAdmin,
    create_role_dependency,
    create_self_or_role_dependency,
    require_self_access_or_role
)
from app.schemas.user import UserRole, UserMe, TrainerResponse
from app.crud.user import get_user_by_id
from app.auth.jwt_handler import verify_jwt_token

router = APIRouter(prefix="/examples", tags=["Authorization Examples"])


# Example 1: Simple role requirement (OWNER only)
@router.get("/owner-only")
def owner_only_endpoint(current_user = Depends(RequireOwner)):
    """Only OWNER can access this endpoint"""
    return {"message": "This is OWNER only content"}


# Example 2: Multiple roles allowed (ADMIN or OWNER)
@router.get("/admin-or-owner")
def admin_or_owner_endpoint(current_user = Depends(RequireAdminOrOwner)):
    """ADMIN or OWNER can access this endpoint"""
    return {"message": "This is for ADMIN or OWNER"}


# Example 3: Custom role combination
RequireTrainerOrOwner = create_role_dependency([UserRole.TRAINER, UserRole.OWNER])

@router.get("/trainer-or-owner")
def trainer_or_owner_endpoint(current_user = Depends(RequireTrainerOrOwner)):
    """TRAINER or OWNER can access this endpoint"""
    return {"message": "This is for TRAINER or OWNER"}


# Example 4: Exact role matching (no hierarchy)
RequireAdminExactMatch = create_role_dependency(UserRole.ADMIN, use_hierarchy=False)

@router.get("/admin-exact")
def admin_exact_endpoint(current_user = Depends(RequireAdminExactMatch)):
    """Only ADMIN (not OWNER) can access this endpoint"""
    return {"message": "This is for ADMIN only, OWNER cannot access"}


# Example 5: Self-access or role-based access
@router.get("/users/{user_id}/profile")
def get_user_profile(
    user_id: int = Path(...),
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Users can access their own profile, or ADMINs can access any profile
    """
    # Check if user can access this profile (self-access or admin role)
    require_self_access_or_role(
        current_user=current_user,
        resource_user_id=user_id,
        required_roles=UserRole.ADMIN,  # ADMINs can access any profile
        error_message="You can only access your own profile"
    )
    
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


# Example 6: Complex business logic with role checking
@router.patch("/users/{user_id}/salary")
def update_user_salary(
    user_id: int = Path(...),
    salary_data: dict,  # Simplified for example
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    - OWNERs can update anyone's salary
    - ADMINs can update trainers' salaries but not other admins
    - TRAINERs cannot update salaries
    """
    target_user = get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_user_role = UserRole(current_user["role"])
    target_user_role = UserRole(target_user.role)
    
    # OWNER can update anyone's salary
    if current_user_role == UserRole.OWNER:
        # Update salary logic here
        return {"message": f"Salary updated for user {user_id}"}
    
    # ADMIN can update trainer salaries but not other admins or owners
    elif current_user_role == UserRole.ADMIN:
        if target_user_role in [UserRole.ADMIN, UserRole.OWNER]:
            raise HTTPException(
                status_code=403, 
                detail="ADMINs cannot update salaries for other ADMINs or OWNERs"
            )
        # Update salary logic here
        return {"message": f"Salary updated for trainer {user_id}"}
    
    else:
        raise HTTPException(
            status_code=403, 
            detail="Only ADMINs and OWNERs can update salaries"
        )


# Example 7: Role hierarchy demonstration
@router.get("/hierarchy-demo/{level}")
def hierarchy_demo(
    level: str = Path(...),
    current_user = Depends(verify_jwt_token)
):
    """
    Demonstrates role hierarchy:
    - /hierarchy-demo/client - Any authenticated user can access
    - /hierarchy-demo/trainer - TRAINER, ADMIN, OWNER can access  
    - /hierarchy-demo/admin - ADMIN, OWNER can access
    - /hierarchy-demo/owner - Only OWNER can access
    """
    
    user_role = UserRole(current_user["role"])
    
    role_requirements = {
        "client": UserRole.CLIENT,
        "trainer": UserRole.TRAINER,
        "admin": UserRole.ADMIN,
        "owner": UserRole.OWNER
    }
    
    if level not in role_requirements:
        raise HTTPException(status_code=400, detail="Invalid level")
    
    required_role = role_requirements[level]
    
    # Use our helper function to check hierarchy
    from app.auth.permissions import RoleHierarchy
    
    if not RoleHierarchy.has_permission(user_role, required_role):
        raise HTTPException(
            status_code=403, 
            detail=f"Access denied. Required role: {required_role.value} or higher"
        )
    
    return {
        "message": f"Access granted to {level} level",
        "your_role": user_role.value,
        "required_role": required_role.value
    }


# Example 8: Dynamic role dependency
def create_dynamic_role_check(resource_type: str):
    """Create role dependency based on resource type"""
    
    role_mapping = {
        "financial": [UserRole.OWNER],  # Only OWNER can access financial data
        "trainer_data": [UserRole.ADMIN, UserRole.OWNER],  # ADMIN+ can access trainer data
        "client_data": [UserRole.TRAINER, UserRole.ADMIN, UserRole.OWNER],  # TRAINER+ can access
        "public": [UserRole.CLIENT, UserRole.TRAINER, UserRole.ADMIN, UserRole.OWNER]  # Anyone
    }
    
    required_roles = role_mapping.get(resource_type, [UserRole.OWNER])
    return create_role_dependency(required_roles)


@router.get("/resources/{resource_type}/{resource_id}")
def get_resource(
    resource_type: str = Path(...),
    resource_id: int = Path(...),
    # This would need to be implemented differently in practice
    # but demonstrates the concept
    db: Session = Depends(get_db)
):
    """
    Dynamically check roles based on resource type
    """
    # In practice, you'd use dependency_overrides or similar FastAPI features
    # This is just a conceptual example
    
    if resource_type == "financial":
        # Only show this example pattern
        return {"message": "This would require dynamic role checking"}
    
    return {"resource_type": resource_type, "resource_id": resource_id}
