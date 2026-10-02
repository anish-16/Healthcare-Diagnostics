from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
