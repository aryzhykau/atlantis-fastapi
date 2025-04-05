from pydantic_settings import BaseSettings


class Config(BaseSettings):

    POSTGRES_HOST: str = "localhost:5432"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "<PASSWORD>"
    POSTGRES_DB: str = "postgres"
    JWT_SECRET_KEY: str = "secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 10
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_DISCOVERY_URL: str = ""


    class Config:
        env_file = '.env'

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}/{self.POSTGRES_DB}"


# Читаем конфигурацию
config = Config()
