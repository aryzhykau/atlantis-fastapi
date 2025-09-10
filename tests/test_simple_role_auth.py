"""
Test examples for the simple role-based authorization system.
"""

import pytest
from fastapi import HTTPException
from unittest.mock import Mock
from app.auth.permissions import get_current_user


class TestSimpleRoleAuthorization:
    """Test the simple role authorization system"""
    
    def test_get_current_user_no_roles_required(self):
        """Test that any authenticated user can access when no roles specified"""
        # Mock authenticated user
        mock_user = {"id": 1, "role": "CLIENT", "email": "test@example.com"}
        
        # Create dependency with no role restrictions
        dependency = get_current_user()
        
        # Should return the user data
        result = dependency(mock_user)
        assert result == mock_user
    
    def test_get_current_user_with_correct_role(self):
        """Test that user with correct role can access"""
        # Mock admin user
        mock_user = {"id": 1, "role": "ADMIN", "email": "admin@example.com"}
        
        # Create dependency that requires ADMIN role
        dependency = get_current_user(["ADMIN"])
        
        # Should return the user data
        result = dependency(mock_user)
        assert result == mock_user
    
    def test_get_current_user_with_multiple_allowed_roles(self):
        """Test that user with one of multiple allowed roles can access"""
        # Mock owner user
        mock_user = {"id": 1, "role": "OWNER", "email": "owner@example.com"}
        
        # Create dependency that allows ADMIN or OWNER
        dependency = get_current_user(["ADMIN", "OWNER"])
        
        # Should return the user data
        result = dependency(mock_user)
        assert result == mock_user
    
    def test_get_current_user_with_wrong_role(self):
        """Test that user with wrong role gets 403 error"""
        # Mock client user
        mock_user = {"id": 1, "role": "CLIENT", "email": "client@example.com"}
        
        # Create dependency that requires ADMIN role
        dependency = get_current_user(["ADMIN"])
        
        # Should raise HTTPException with 403 status
        with pytest.raises(HTTPException) as exc_info:
            dependency(mock_user)
        
        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail
        assert "ADMIN" in exc_info.value.detail
        assert "CLIENT" in exc_info.value.detail
    
    def test_get_current_user_no_authentication(self):
        """Test that unauthenticated user gets 401 error"""
        # Create dependency
        dependency = get_current_user(["ADMIN"])
        
        # Should raise HTTPException with 401 status
        with pytest.raises(HTTPException) as exc_info:
            dependency(None)
        
        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail
    
    def test_get_current_user_missing_role(self):
        """Test that user without role field gets 401 error"""
        # Mock user without role
        mock_user = {"id": 1, "email": "test@example.com"}
        
        # Create dependency
        dependency = get_current_user(["ADMIN"])
        
        # Should raise HTTPException with 401 status
        with pytest.raises(HTTPException) as exc_info:
            dependency(mock_user)
        
        assert exc_info.value.status_code == 401
        assert "User role not found" in exc_info.value.detail


# Example of testing an endpoint that uses role-based auth
def test_admin_endpoint_with_admin_user():
    """Example of testing an endpoint that requires ADMIN role"""
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    
    # Mock JWT token that returns ADMIN user
    admin_token = "mock_admin_token"
    
    # This would depend on your JWT mocking strategy
    # response = client.get("/admin-endpoint", headers={"Authorization": f"Bearer {admin_token}"})
    # assert response.status_code == 200


def test_admin_endpoint_with_client_user():
    """Example of testing that CLIENT user gets 403 on admin endpoint"""
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    
    # Mock JWT token that returns CLIENT user  
    client_token = "mock_client_token"
    
    # This would depend on your JWT mocking strategy
    # response = client.get("/admin-endpoint", headers={"Authorization": f"Bearer {client_token}"})
    # assert response.status_code == 403
