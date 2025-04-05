import logging

from authlib.jose import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.config import config

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/google")


def verify_jwt_token(token: str = Depends(oauth2_scheme)):
    logger.debug("EXECUTING")
    """ Проверяет JWT access token """
    try:
        payload = jwt.decode(token, config.JWT_SECRET_KEY)

        logger.debug(f"payload = {payload}")
        return {"email": payload["sub"], "role": payload["role"], "id": payload["id"]}
    except :
        raise HTTPException(status_code=401, detail="Error")



# security = HTTPBearer()
#
# def verify_user(credentials: HTTPAuthorizationCredentials = Security(security)):
#     token = credentials.credentials
#     return verify_jwt_token(token)