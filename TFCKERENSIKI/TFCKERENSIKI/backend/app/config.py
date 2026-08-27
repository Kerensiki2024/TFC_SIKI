"""
Configuration chargée depuis les variables d’environnement (et optionnellement .env).
Les noms en snake_case correspondent aux clés UPPER_SNAKE en env (ex. DATABASE_URL).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Chaîne SQLAlchemy async (driver asyncpg).
    database_url: str = "postgresql+asyncpg://horaires:horaires_secret@localhost:5432/horaires"
    # Webhook n8n déclenché après certaines actions (ex. annulation cours).
    n8n_webhook_edit: str = "http://localhost:5678/webhook/edit-schedule"
    # Si défini, les routes /n8n/* exigent l'en-tête X-N8N-Secret: <valeur>
    n8n_internal_secret: str | None = None
    app_name: str = "Chatbot horaires — UNIKIN / FPoly (L3GIN)"
    # Secret HS256 : doit être fort et secret en prod (voir docker-compose JWT_SECRET).
    jwt_secret: str = "dev-super-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_exp_hours: int = 8


settings = Settings()
