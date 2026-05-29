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

    # Personal access token used to fetch PR diffs from the GitHub API.
    # Required for private repos and to lift rate limits.
    github_token: str = ""

    # OpenAI credentials and model used by the review pipeline.
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # Maximum tokens per diff chunk sent to the model.
    review_chunk_max_tokens: int = 3000


settings = Settings()
