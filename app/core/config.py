from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_db_url(url: str) -> str:
    """Accept postgres:// or postgresql:// URLs and pin the psycopg driver.

    Hosted providers (Neon, Supabase, Vercel Postgres) hand out
    postgres:// URLs; SQLAlchemy needs the explicit driver scheme.
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Application
    app_name: str = "EVE Healthcare API"
    debug: bool = False

    # Database
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/eve_health"
    test_database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/eve_health_test"

    # JWT
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # Password hashing cost; tests use a low value for speed.
    bcrypt_rounds: int = 12

    @field_validator("database_url", "test_database_url", mode="before")
    @classmethod
    def _normalize_scheme(cls, v: str) -> str:
        return _normalize_db_url(v)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
