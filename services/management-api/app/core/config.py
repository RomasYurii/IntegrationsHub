from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .../IntegrationHub/services/management-api/app/core/config.py
# parents[0]=core, [1]=app, [2]=management-api, [3]=services, [4]=корінь репозиторію
ROOT_DIR = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    DATABASE_URL: str
    DB_ECHO: bool = False

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        extra="ignore",
    )


settings = Settings()
