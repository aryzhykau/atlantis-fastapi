import logging

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.jwt_handler import create_access_token, create_refresh_token, refresh_access_token
from app.dependencies import get_db
from app.entities.users.crud import get_user_by_email  # Searching for a user in the DB
from app.utils.google import get_user_info_from_access_token  # Extract user info from Google


class RefreshTokenRequest(BaseModel):
    refresh_token: str

logger = logging.getLogger(__name__)

# Create router instance
router = APIRouter()


class TokensResponse(BaseModel):
    access_token: str
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str


@router.get("/google", response_model=TokensResponse)
async def auth_google(authorization: str = Header(...), db: Session = Depends(get_db)):
    """
    Handles Google OAuth, searches for the user in the database, and issues access & refresh tokens.
    """
    # Fetch user data from Google
    user_data = get_user_info_from_access_token(authorization)
    logger.debug(f"User data from Google: {user_data}")

    # Check if user exists in the database
    user = get_user_by_email(db, email=user_data["email"])
    if not user:
        raise HTTPException(status_code=403, detail="Access denied: user not found.")

    # Generate access and refresh tokens
    access_token = create_access_token(data={"sub": user.email, "id": user.id, "role": user.role})
    refresh_token = create_refresh_token(data={"sub": user.email, "id": user.id, "role": user.role})

    logger.debug(f"Access token: {access_token}", )
    logger.debug(f"Refresh token: {refresh_token}")

    return {"access_token": access_token, "refresh_token": refresh_token}



@router.post("/refresh-token", response_model=TokensResponse)
async def refresh_token(refresh_token_request: RefreshTokenRequest):
    """
    Refreshes access token using the provided refresh token.
    """
    new_access_token = refresh_access_token(refresh_token_request.refresh_token)
    return {"access_token": new_access_token, "refresh_token": refresh_token_request.refresh_token}
