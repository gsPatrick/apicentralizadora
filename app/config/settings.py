from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Central Auth Hub"
    DATABASE_URL: str = "sqlite:///./centralizador.db" # Default to SQLite for simplicity, can be changed
    SECRET_KEY: str = "supersecretkey" # Change in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    TRANSFER_TOKEN_EXPIRE_SECONDS: int = 60
    SERVER_NAME: Optional[str] = None
    ROOT_PATH: Optional[str] = None
    COOKIE_DOMAIN: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
