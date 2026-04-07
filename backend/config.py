"""
backend/config.py – Application settings loaded from environment / .env file.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core app settings
    app_name: str = "AgentFlow"
    app_version: str = "1.0.0"

    # GCP / Vertex AI Settings
    google_cloud_project: str = ""
    google_cloud_region: str = "us-central1"
    gemini_model: str = "gemini-2.5-flash"
    google_api_key: str = ""

    # Database settings
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "agentflow"
    db_password: str = ""
    db_name: str = "agentflow"
    # Set USE_SQLITE=true for local dev without PostgreSQL
    use_sqlite: bool = False

    cors_origins: list[str] = ["*"]


@lru_cache
def get_settings():
    return Settings()
