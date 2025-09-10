# Simple Role-Based Authorization

This document explains how to use the simplified role-based authorization system in our FastAPI backend.

## Overview

Instead of complex role hierarchies and decorators, we now have a single simple `get_current_user` dependency that can accept a list of allowed roles.

## Basic Usage

### Import the dependency

```python
from app.auth.permissions import get_current_user
```

### Use in endpoints

```python
from fastapi import APIRouter, Depends
from app.auth.permissions import get_current_user

router = APIRouter()

# Any authenticated user
@router.get("/profile")
def get_profile(current_user = Depends(get_current_user())):
    return {"user_id": current_user["id"], "role": current_user["role"]}

# Only ADMIN role
@router.get("/admin-panel") 
def admin_panel(current_user = Depends(get_current_user(["ADMIN"]))):
    return {"message": "Admin access granted"}

# ADMIN or OWNER roles
@router.get("/management")
def management(current_user = Depends(get_current_user(["ADMIN", "OWNER"]))):
    return {"message": "Management access granted"}

# Multiple roles allowed
@router.get("/staff-area")
def staff_area(current_user = Depends(get_current_user(["TRAINER", "ADMIN", "OWNER"]))):
    return {"message": "Staff access granted"}
```

## Available Roles

The system supports these roles (defined in `app.schemas.user.UserRole`):
- `CLIENT` 
- `TRAINER`
- `ADMIN`
- `OWNER`

## How it works

1. **No roles specified**: `get_current_user()` - Any authenticated user can access
2. **Single role**: `get_current_user(["ADMIN"])` - Only users with ADMIN role can access  
3. **Multiple roles**: `get_current_user(["ADMIN", "OWNER"])` - Users with ADMIN OR OWNER role can access

## Error Responses

The dependency will return these HTTP errors:

- **401 Unauthorized**: If user is not authenticated or token is invalid
- **403 Forbidden**: If user is authenticated but doesn't have the required role

Error response format:
```json
{
  "detail": "Access denied. Required roles: ['ADMIN', 'OWNER'], your role: TRAINER"
}
```

## Migration from Complex System

Replace old complex dependencies with simple ones:

### Before (complex system):
```python
@router.get("/endpoint")
def endpoint(current_user = Depends(RequireAdminOrOwner)):
    pass
```

### After (simple system):
```python  
@router.get("/endpoint")
def endpoint(current_user = Depends(get_current_user(["ADMIN", "OWNER"]))):
    pass
```

## Current User Object

The `current_user` object returned contains:
```python
{
    "id": 123,           # User ID
    "email": "user@example.com", 
    "role": "ADMIN"      # User role as string
}
```

## Examples

See `app/endpoints/role_examples.py` for complete working examples of all usage patterns.
