from functools import lru_cache
from typing import List

from pydantic import Field, SecretStr, field_validator
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

    URL_VERIFY_ENABLED: bool = Field(default=True)
    URL_VERIFY_INTERVAL_HOURS: int = Field(default=168)  # weekly
    URL_VERIFY_TIMEOUT_SECONDS: float = Field(default=10.0)
    URL_VERIFY_USER_AGENT: str = Field(default="TrestleBot/1.0 (+https://trestle.dev/bot)")
    URL_VERIFY_CONCURRENCY: int = Field(default=5)
    URL_VERIFY_GONE_THRESHOLD: int = Field(default=3)
    URL_VERIFY_REDIS_LOCK_TTL_SECONDS: int = Field(default=1800)

    DEEPSEEK_API_KEY: SecretStr = Field(default=SecretStr(""))
    DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com")
    DEEPSEEK_MODEL: str = Field(default="deepseek-chat")
    LLM_TIMEOUT_SECONDS: float = Field(default=30.0)
    LLM_MAX_RETRIES: int = Field(default=2)
    DEEPSEEK_INPUT_PRICE_PER_MTOK: float = Field(default=0.27)
    DEEPSEEK_OUTPUT_PRICE_PER_MTOK: float = Field(default=1.10)

    CHAT_USE_ORCHESTRATOR: bool = Field(default=True)
    ORCHESTRATOR_TIMEOUT_SECONDS: float = Field(default=60.0)

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
