from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini
    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Postgres URIs
    postgres_uri: str = "postgresql+asyncpg://admin:password@localhost:5432/aegis_bgv"
    postgres_uri_sync: str = "postgresql://admin:password@localhost:5432/aegis_bgv"

    # App
    secret_key: str = "dev-secret"
    upload_dir: str = "./uploads"
    frontend_origin: str = "http://localhost:5173"

    @property
    def get_postgres_uri(self) -> str:
        # Render/Heroku provide postgres:// but SQLAlchemy requires postgresql://
        uri = self.postgres_uri
        if uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql+asyncpg://", 1)
        return uri
        
    @property
    def get_postgres_uri_sync(self) -> str:
        uri = self.postgres_uri_sync
        if uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://", 1)
        return uri


settings = Settings()

# Ensure upload directory exists
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
