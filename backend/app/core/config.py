from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Polytech Schedule Chatbot API"
    DEBUG: bool = True
    SECRET_KEY: str = "change-this-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    DATABASE_URL: str
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    N8N_INGESTION_WEBHOOK_URL: str | None = None
    N8N_EDITION_WEBHOOK_URL: str | None = None
    N8N_NOTIFICATION_WEBHOOK_URL: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
