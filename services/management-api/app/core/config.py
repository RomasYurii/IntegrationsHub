from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .../IntegrationHub/services/management-api/app/core/config.py
# parents[0]=core, [1]=app, [2]=management-api, [3]=services, [4]=корінь репозиторію
ROOT_DIR = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    DATABASE_URL: str
    DB_ECHO: bool = False
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REDIS_URL: str
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7


    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        extra="ignore",
    )


settings = Settings()
