import logging
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from app.config import config

logger = logging.getLogger(__name__)

# Define OAuth2 schemes for access and refresh tokens
oauth2_scheme_access = OAuth2PasswordBearer(tokenUrl="auth/google")
oauth2_scheme_refresh = OAuth2PasswordBearer(tokenUrl="auth/refresh-token")


def verify_jwt_token(token: str = Depends(oauth2_scheme_access)):
    """
    Verify JWT access token for correctness and expiration time.
    """
    print("Verify JWT token:")
    try:
        if config.ENVIRONMENT == "dev":
            if token == "dev_token":
                print("returning dev_token")
                return {"email": config.DEV_ADMIN_EMAIL, "role": "ADMIN", "id": 1}
        # Decode the JWT token
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM])


        # Check expiration
        exp = payload.get("exp")

        if exp is None:
            print("exp is None")
            raise HTTPException(status_code=401, detail="Missing 'exp' field in token")

        current_time = datetime.now(tz=timezone.utc)
        token_exp_time = datetime.fromtimestamp(exp, tz=timezone.utc)
        logger.debug(f"Token expiration time: {token_exp_time}")
        logger.debug(f"Current time: {current_time}")
        if token_exp_time < current_time:
            raise HTTPException(status_code=401, detail="Token has expired")

        logger.debug(f"Token payload: {payload}")
        # Return payload details (like email, role, id) on success
        # Handle both "sub" and "email" fields for backward compatibility
        email = payload.get("sub") or payload.get("email")
        return {"email": email, "role": payload["role"], "id": payload["id"]}

    except JWTError as e:
        print("JWTError exception:")
        logger.error(f"JWT verification error: {str(e)}")
        raise HTTPException(status_code=401, detail="Token is invalid or expired")


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Create a new JWT access token.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Create a new JWT refresh token.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=config.JWT_REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)
    return encoded_jwt


def refresh_access_token(token: str) -> str:
    """
    Use a refresh token to generate a new access token.
    """
    try:
        # Decode the refresh token
        logger.debug(f"Received refresh token: {token}")
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
        logger.debug(f"Refresh token payload: {payload}")
        exp = payload.get("exp")

        # Ensure refresh token has not expired
        if exp is None or datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(tz=timezone.utc):
            raise HTTPException(status_code=401, detail="Refresh token has expired")

        # Extract user-specific information and create new access token
        new_access_token = create_access_token(
            data={"sub": payload.get("sub"), "id": payload.get("id"), "role": payload.get("role")}
        )
        return new_access_token

    except JWTError as e:
        logger.error(f"Error during refresh token validation: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")


def is_admin_or_owner(user_role: str) -> bool:
    """Helper function to check if user has admin or owner privileges"""
    from app.schemas.user import UserRole
    return user_role in (UserRole.ADMIN, UserRole.OWNER)