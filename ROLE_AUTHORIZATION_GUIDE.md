# Role-Based Authorization System Implementation Guide

## Overview

This document explains the new role-based authorization system implemented for the Atlantis FastAPI backend. The system follows FastAPI best practices and provides a clean, maintainable way to handle role-based access control.

## Key Features

- **Declarative Role Dependencies**: Use simple dependency injection to enforce role requirements
- **Role Hierarchy Support**: Higher roles automatically inherit permissions of lower roles
- **Flexible Permission Checking**: Support for multiple roles, exact matching, and self-access patterns
- **Consistent Error Handling**: Standardized error messages and HTTP status codes
- **Type Safety**: Full typing support with proper enum usage
- **Performance Optimized**: Minimal overhead with efficient role checking

## Role Hierarchy

```
OWNER (highest privileges)
  ↓ inherits permissions of
ADMIN
  ↓ inherits permissions of  
TRAINER
  ↓ inherits permissions of
CLIENT (lowest privileges)
```

## Basic Usage

### 1. Simple Role Requirements

Replace manual role checking:

```python
# OLD WAY ❌
@router.get("/admins")
def get_admins(current_user = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins allowed")
    # endpoint logic...

# NEW WAY ✅
@router.get("/admins")
def get_admins(current_user = Depends(RequireAdmin), db: Session = Depends(get_db)):
    # endpoint logic... (role checking handled automatically)
```

### 2. Multiple Roles Allowed

```python
# Allow both ADMIN and OWNER
@router.get("/management-data")
def get_management_data(current_user = Depends(RequireAdminOrOwner)):
    return {"data": "management info"}

# Allow TRAINER, ADMIN, or OWNER
@router.get("/training-data") 
def get_training_data(current_user = Depends(RequireTrainerOrAdmin)):
    return {"data": "training info"}
```

### 3. Owner-Only Endpoints

```python
@router.post("/admins")
def create_admin(admin_data: AdminCreate, current_user = Depends(RequireOwner)):
    # Only OWNER can create admins
    return create_admin_logic(admin_data)
```

## Advanced Usage Patterns

### 1. Self-Access or Role-Based Access

For endpoints where users can access their own resources OR admins can access any resource:

```python
@router.get("/users/{user_id}/profile")
def get_user_profile(
    user_id: int,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    # Users can access their own profile, ADMINs can access any profile
    require_self_access_or_role(
        current_user=current_user,
        resource_user_id=user_id,
        required_roles=UserRole.ADMIN,
        error_message="You can only access your own profile"
    )
    
    return get_user_logic(user_id)
```

### 2. Complex Business Logic

For endpoints with complex authorization rules:

```python
@router.patch("/users/{user_id}/salary")
def update_salary(
    user_id: int,
    salary_data: SalaryUpdate,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    target_user = get_user_by_id(db, user_id)
    current_role = UserRole(current_user["role"])
    target_role = UserRole(target_user.role)
    
    # OWNER can update anyone's salary
    if current_role == UserRole.OWNER:
        return update_salary_logic(user_id, salary_data)
    
    # ADMIN can update trainer salaries but not other admins
    elif current_role == UserRole.ADMIN:
        if target_role in [UserRole.ADMIN, UserRole.OWNER]:
            raise HTTPException(403, "Cannot update admin/owner salaries")
        return update_salary_logic(user_id, salary_data)
    
    else:
        raise HTTPException(403, "Insufficient permissions")
```

### 3. Custom Role Dependencies

Create custom role combinations:

```python
# Custom dependency for specific use case
RequireTrainerOrOwner = create_role_dependency([UserRole.TRAINER, UserRole.OWNER])

@router.get("/training-stats")
def get_training_stats(current_user = Depends(RequireTrainerOrOwner)):
    return {"stats": "training data"}

# Exact role matching (no hierarchy)
RequireAdminOnly = create_role_dependency(UserRole.ADMIN, use_hierarchy=False)

@router.get("/admin-only-data")
def get_admin_data(current_user = Depends(RequireAdminOnly)):
    # Only ADMIN role, not OWNER
    return {"data": "admin specific"}
```

## Migration Guide

### Step 1: Update Imports

```python
# Add to your endpoint files
from app.dependencies import (
    RequireOwner,
    RequireAdmin,
    RequireAdminOrOwner,
    RequireTrainerOrAdmin,
    require_self_access_or_role
)
```

### Step 2: Replace Manual Role Checks

**Before:**
```python
def my_endpoint(current_user = Depends(verify_jwt_token)):
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin required")
```

**After:**
```python
def my_endpoint(current_user = Depends(RequireAdmin)):
    # Role checking handled automatically
```

### Step 3: Update Complex Authorization

**Before:**
```python
def update_resource(resource_id: int, current_user = Depends(verify_jwt_token)):
    if current_user["role"] not in [UserRole.ADMIN, UserRole.OWNER]:
        if current_user["id"] != resource.owner_id:
            raise HTTPException(403, "Access denied")
```

**After:**
```python
def update_resource(resource_id: int, current_user = Depends(verify_jwt_token)):
    require_self_access_or_role(
        current_user, 
        resource.owner_id, 
        [UserRole.ADMIN, UserRole.OWNER]
    )
```

## Available Dependencies

### Pre-defined Dependencies
- `RequireOwner` - Only OWNER role
- `RequireAdmin` - ADMIN or OWNER roles  
- `RequireAdminOrOwner` - ADMIN or OWNER roles (explicit)
- `RequireTrainer` - TRAINER, ADMIN, or OWNER roles
- `RequireTrainerOrAdmin` - TRAINER, ADMIN, or OWNER roles
- `RequireClient` - Any authenticated user
- `RequireOwnerExact` - Only OWNER (no hierarchy)
- `RequireAdminExact` - Only ADMIN (no hierarchy)

### Helper Functions
- `create_role_dependency()` - Create custom role dependencies
- `require_self_access_or_role()` - Check self-access or role permissions
- `check_self_access_or_role()` - Boolean check for access permissions

## Error Handling

The system provides consistent error responses:

```json
{
  "detail": "Access denied. Required roles: ADMIN, OWNER"
}
```

HTTP Status Codes:
- `401` - Authentication required (no valid token)
- `403` - Forbidden (insufficient permissions)

## Best Practices

1. **Use Pre-defined Dependencies**: Start with `RequireAdmin`, `RequireOwner`, etc.
2. **Leverage Role Hierarchy**: Don't explicitly check for OWNER if ADMIN access is sufficient
3. **Clear Error Messages**: Use custom error messages for complex authorization
4. **Centralize Complex Logic**: Move complex authorization to service layer
5. **Document Requirements**: Clearly document endpoint role requirements

## Performance Considerations

- Role checking is O(1) operation using enum comparison
- Hierarchy checking uses dictionary lookup (O(1))
- Minimal memory overhead per request
- No database queries for basic role validation

## Testing

Test role-based endpoints:

```python
def test_admin_endpoint_with_admin_role(client, admin_headers):
    response = client.get("/admin-data", headers=admin_headers)
    assert response.status_code == 200

def test_admin_endpoint_with_trainer_role(client, trainer_headers):
    response = client.get("/admin-data", headers=trainer_headers)
    assert response.status_code == 403

def test_self_access_allowed(client, trainer_headers):
    # Trainer accessing own data
    response = client.get("/users/123/profile", headers=trainer_headers)
    assert response.status_code == 200

def test_self_access_denied(client, trainer_headers):
    # Trainer accessing other user's data
    response = client.get("/users/456/profile", headers=trainer_headers)
    assert response.status_code == 403
```

## Troubleshooting

### Common Issues

1. **ImportError**: Make sure to import from `app.dependencies`
2. **403 Forbidden**: Check if user has correct role in JWT token
3. **Hierarchy Not Working**: Verify `use_hierarchy=True` (default)
4. **Self-Access Issues**: Ensure user ID comparison is correct type (int vs str)

### Debug Tips

```python
# Add logging to debug authorization
import logging
logger = logging.getLogger(__name__)

@router.get("/debug-auth")
def debug_endpoint(current_user = Depends(RequireAdmin)):
    logger.info(f"User {current_user['id']} with role {current_user['role']} accessed endpoint")
    return {"user": current_user}
```

This system provides a clean, maintainable, and secure way to handle role-based authorization in your FastAPI application while following best practices and maintaining type safety.
