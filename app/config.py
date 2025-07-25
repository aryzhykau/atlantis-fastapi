import os

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "dev")
    DEV_ADMIN_EMAIL: str = os.getenv("DEV_ADMIN_EMAIL", "rorychan0697@gmail.com")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost:5432")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "<PASSWORD>")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "postgres")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "secret")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 10))
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", 30))
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_DISCOVERY_URL: str = os.getenv("GOOGLE_DISCOVERY_URL", "")
    CRON_API_KEY: str = os.getenv("CRON_API_KEY", "test-cron-api-key-12345")

    model_config = ConfigDict(env_file=os.getenv("ENV_FILE", ".env"))

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}/{self.POSTGRES_DB}"


# Читаем конфигурацию
config = Config()
