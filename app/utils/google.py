import logging
import requests

from fastapi import HTTPException

from app.config import config

logger = logging.getLogger(__name__)

def get_user_info_from_access_token(authorization: str):
    try:
        # Проверка токена с использованием Google API
        access_token = authorization.replace("Bearer ", "").strip()
        logger.debug(config.POSTGRES_DB)
        response = requests.get(config.GOOGLE_DISCOVERY_URL, headers={"Authorization": f"Bearer {access_token}"})

        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid access token")

        user_info = response.json()  # Преобразуем ответ в JSON
        return {"email": user_info["email"], "name": user_info["name"], "picture": user_info["picture"]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user info: {str(e)}")
