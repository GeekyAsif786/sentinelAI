from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://sentinel:sentinel@localhost:5432/sentinel"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "sentinelpassword"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: str = Field(default="local-development-change-me", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    ai_enabled: bool = False
    ai_provider: str = "disabled"
    cors_origins: list[str] = ["http://localhost:5173"]
    nvd_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

