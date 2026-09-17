"""Application configuration via environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "dev-secret-change-me-in-production"
MIN_JWT_SECRET_LEN = 32


def validate_jwt_config(env: str, secret: str) -> None:
    """Fail fast on unsafe JWT config in production.

    Pure function (no settings access) so the smoke suite can pin the
    matrix directly: dev tolerates anything, production requires a
    non-default secret of at least MIN_JWT_SECRET_LEN chars.
    """
    if env.strip().lower() != "production":
        return
    if not secret or secret == DEFAULT_JWT_SECRET or len(secret) < MIN_JWT_SECRET_LEN:
        raise RuntimeError(
            "Refusing to boot: set a unique JWT_SECRET (>= 32 chars) "
            "when ENV=production."
        )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    APP_NAME: str = "Second Brain OS"
    ENV: str = "development"  # development | production
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/secondbrain"

    # Vector store
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "knowledge_chunks"

    # Auth
    JWT_SECRET: str = DEFAULT_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # AI
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"

    # Misc
    CORS_ORIGINS: str = "http://localhost:3000"
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 100
    CHUNK_SIZE: int = 900        # characters per chunk
    CHUNK_OVERLAP: int = 150

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def llm_enabled(self) -> bool:
        return bool(self.OPENAI_API_KEY)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
