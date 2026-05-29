from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from the environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "info"

    # PostgreSQL connection string, e.g.
    # postgresql+psycopg2://user:password@host:5432/dbname
    database_url: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/ai_code_review"
    )

    # Shared secret configured on the GitHub webhook; used to verify the
    # HMAC-SHA256 signature of incoming payloads.
    github_webhook_secret: str = ""


settings = Settings()
