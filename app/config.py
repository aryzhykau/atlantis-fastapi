from pydantic_settings import BaseSettings


class Config(BaseSettings):

    POSTGRES_HOST: str = "localhost:5432"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "<PASSWORD>"
    POSTGRES_DB: str = "postgres"
    JWT_SECRET_KEY: str = "secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    SQLALCHEMY_DATABASE_URI: str = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_DISCOVERY_URL: str = ""


    class Config:
        env_file = '.env'


# Читаем конфигурацию
config = Config()
