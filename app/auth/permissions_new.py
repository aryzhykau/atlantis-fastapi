"""
Simple role-based authorization for FastAPI endpoints.
"""

from typing import List, Optional
from fastapi import Depends, HTTPException, status
from app.auth.jwt_handler import verify_jwt_token


def get_current_user(allowed_roles: Optional[List[str]] = None):
    """
    Dependency factory to create a get_current_user dependency with role checking.
    
    Args:
        allowed_roles: List of role strings that are allowed to access the endpoint.
                      If None, any authenticated user can access.
                      
    Returns:
        A FastAPI dependency function
        
    Example:
        # Allow only ADMIN and OWNER
        @router.get("/admin-endpoint")
        def admin_only(current_user=Depends(get_current_user(["ADMIN", "OWNER"]))):
            return {"message": "Admin access granted"}
            
        # Allow any authenticated user
        @router.get("/user-endpoint") 
        def any_user(current_user=Depends(get_current_user())):
            return {"message": "User access granted"}
    """
    def dependency(current_user_data = Depends(verify_jwt_token)):
        if not current_user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
            
        # If no roles specified, allow any authenticated user
        if allowed_roles is None:
            return current_user_data
            
        user_role = current_user_data.get("role")
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User role not found"
            )
            
        # Check if user role is in allowed roles
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_roles}, your role: {user_role}"
            )
            
        return current_user_data
        
    return dependency
