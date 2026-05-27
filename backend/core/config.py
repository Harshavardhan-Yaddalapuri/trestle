from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://trestle:trestle@localhost:5432/trestle"
    )
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    SESSION_COOKIE_NAME: str = Field(default="trestle_anon_session")
    SESSION_COOKIE_MAX_AGE: int = Field(default=60 * 60 * 24 * 30)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_dev(self) -> bool:
        return self.ENVIRONMENT.lower() in {"dev", "development", "local"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
