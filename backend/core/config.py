from functools import lru_cache
from typing import List, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
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

    LIFECYCLE_AUTO_TRANSITIONS_ENABLED: bool = Field(default=True)
    LIFECYCLE_AUTO_INTERVAL_HOURS: int = Field(default=24)
    LIFECYCLE_SUBMITTED_TO_REVIEW_DAYS: int = Field(default=30)
    LIFECYCLE_INACTIVITY_TO_ABANDONED_DAYS: int = Field(default=90)
    LIFECYCLE_AUTO_REDIS_LOCK_TTL_SECONDS: int = Field(default=600)

    AUTH_MAGIC_LINK_TTL_SECONDS: int = Field(default=900)
    AUTH_MAGIC_LINK_SEND_PER_HOUR: int = Field(default=5)
    AUTH_MAGIC_LINK_SEND_PER_HOUR_PER_IP: int = Field(default=20)
    AUTH_MERGE_PER_HOUR: int = Field(default=5)
    AUTH_SESSION_TTL_DAYS: int = Field(default=30)
    AUTH_SESSION_COOKIE_NAME: str = Field(default="trestle_session")
    AUTH_SESSION_COOKIE_SECURE: bool = Field(default=True)
    AUTH_IP_HASH_PEPPER: SecretStr = Field(default=SecretStr(""))
    AUTH_BASE_URL: str = Field(default="http://localhost:3000")
    AUTH_MAGIC_LINK_PATH: str = Field(default="/auth/verify")

    EMAIL_PROVIDER: Literal["log", "resend"] = Field(default="log")
    EMAIL_FROM_ADDRESS: str = Field(default="no-reply@trestle.local")
    EMAIL_FROM_NAME: str = Field(default="Trestle")
    EMAIL_REPLY_TO: str | None = Field(default=None)
    EMAIL_DEV_ALLOWED_DOMAIN: str | None = Field(default=None)
    EMAIL_UNSUBSCRIBE_PATH: str = Field(default="/api/email/unsubscribe")  # full path from frontend origin
    RESEND_API_KEY: SecretStr | None = Field(default=None)

    DEEPSEEK_API_KEY: SecretStr = Field(default=SecretStr(""))
    DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com")
    DEEPSEEK_MODEL: str = Field(default="deepseek-chat")
    LLM_TIMEOUT_SECONDS: float = Field(default=30.0)
    LLM_MAX_RETRIES: int = Field(default=2)
    DEEPSEEK_INPUT_PRICE_PER_MTOK: float = Field(default=0.27)
    DEEPSEEK_OUTPUT_PRICE_PER_MTOK: float = Field(default=1.10)

    CHAT_USE_ORCHESTRATOR: bool = Field(default=True)
    ORCHESTRATOR_TIMEOUT_SECONDS: float = Field(default=60.0)

    ALERTS_ENABLED: bool = Field(default=True)
    ALERTS_DEADLINE_WINDOWS_DAYS: tuple[int, ...] = Field(default=(14, 7, 1))
    ALERTS_NEW_GRANT_MIN_SCORE: float = Field(default=0.65)
    ALERTS_CHECKIN_INACTIVITY_DAYS: int = Field(default=14)
    ALERTS_NEW_GRANT_LOOKBACK_HOURS: int = Field(default=24)
    ARQ_QUEUE_NAME: str = Field(default="trestle:alerts")
    ARQ_JOB_TIMEOUT_SECONDS: int = Field(default=60)
    ARQ_MAX_TRIES: int = Field(default=3)
    ADMIN_API_KEY: SecretStr | None = Field(default=None)

    INGEST_ENABLED: bool = Field(default=True)
    INGEST_INTERVAL_HOURS: int = Field(default=24)
    INGEST_REDIS_LOCK_TTL_SECONDS: int = Field(default=3600)
    INGEST_USER_AGENT: str = Field(default="TrestleBot/1.0 (+https://trestle.dev/bot)")
    INGEST_HTTP_TIMEOUT_SECONDS: float = Field(default=30.0)
    INGEST_HTTP_MAX_RETRIES: int = Field(default=3)

    GRANTSGOV_API_BASE: str = Field(default="https://api.grants.gov/v1/api")
    GRANTSGOV_ENABLED: bool = Field(default=True)
    GRANTSGOV_PAGE_SIZE: int = Field(default=100)
    GRANTSGOV_MAX_PAGES: int = Field(default=50)
    GRANTSGOV_DAYS_AHEAD: int = Field(default=180)

    SBIRGOV_API_BASE: str = Field(default="https://api.www.sbir.gov/public/api")
    SBIRGOV_ENABLED: bool = Field(default=True)
    SBIRGOV_PAGE_SIZE: int = Field(default=100)
    SBIRGOV_MAX_PAGES: int = Field(default=30)

    @model_validator(mode="after")
    def _check_required_secrets(self) -> "Settings":
        if not self.AUTH_IP_HASH_PEPPER.get_secret_value() and not self.is_dev:
            raise ValueError(
                "AUTH_IP_HASH_PEPPER must be set in non-development environments"
            )
        if (
            not self.is_dev
            and (
                self.ADMIN_API_KEY is None
                or not self.ADMIN_API_KEY.get_secret_value().strip()
            )
        ):
            raise ValueError("ADMIN_API_KEY must be set in non-development environments")
        if self.EMAIL_PROVIDER == "resend" and (
            self.RESEND_API_KEY is None
            or not self.RESEND_API_KEY.get_secret_value()
        ):
            raise ValueError("RESEND_API_KEY must be set when EMAIL_PROVIDER='resend'")
        return self

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
