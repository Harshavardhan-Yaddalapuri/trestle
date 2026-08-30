from functools import lru_cache
from typing import List, Literal
from urllib.parse import quote_plus, urlparse

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _supabase_project_ref(supabase_url: str) -> str:
    host = urlparse(supabase_url).netloc
    if not host.endswith(".supabase.co"):
        raise ValueError(f"Invalid SUPABASE_URL host: {host}")
    return host.removesuffix(".supabase.co")


def normalize_database_url(url: str) -> str:
    """Ensure SQLAlchemy async URL uses the asyncpg driver."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def build_supabase_database_url(
    supabase_url: str,
    password: str,
    *,
    region: str = "us-east-1",
    use_pooler: bool = True,
    pooler_host: str | None = None,
) -> str:
    """Build a Postgres URL for Supabase-hosted databases.

    Uses the IPv4-compatible Supavisor pooler by default — the direct
    ``db.<ref>.supabase.co`` host is IPv6-only and fails DNS inside Docker.
    """
    ref = _supabase_project_ref(supabase_url)
    encoded = quote_plus(password)
    if pooler_host:
        host = pooler_host
        user = f"postgres.{ref}"
    elif use_pooler:
        host = f"aws-0-{region}.pooler.supabase.com"
        user = f"postgres.{ref}"
    else:
        host = f"db.{ref}.supabase.co"
        user = "postgres"
    return f"postgresql+asyncpg://{user}:{encoded}@{host}:5432/postgres"


def database_connection_hint(exc: BaseException) -> str:
    """Actionable hint for common Supabase Postgres connection failures."""
    msg = str(exc).lower()
    if "name or service not known" in msg or "gaierror" in msg:
        return (
            "Database host did not resolve. Use the Supabase pooler host "
            "(SUPABASE_DB_REGION or SUPABASE_DB_POOLER_HOST), not db.<ref>.supabase.co."
        )
    if "certificate verify failed" in msg or "sslcertverificationerror" in msg:
        return "SSL verification failed — ensure ca-certificates is installed in the backend image."
    if "tenant/user" in msg and "not found" in msg:
        return (
            "Supabase pooler rejected this project. Restore/unpause the project in "
            "the Supabase dashboard, then set SUPABASE_DB_REGION from Connect → Pooler."
        )
    if "password authentication failed" in msg:
        return "Check SUPABASE_DB_PASSWORD in .env (Dashboard → Database, not the API key)."
    return "Verify DATABASE_URL or SUPABASE_URL + SUPABASE_DB_PASSWORD in .env."


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

    # Supabase (auth + hosted Postgres)
    SUPABASE_URL: str = Field(default="")
    SUPABASE_SERVICE_KEY: SecretStr = Field(default=SecretStr(""))
    SUPABASE_ANON_KEY: SecretStr | None = Field(default=None)
    # Database password from Supabase Dashboard → Project Settings → Database
    SUPABASE_DB_PASSWORD: SecretStr | None = Field(default=None)
    # AWS region shown in Supabase Dashboard → Connect → Pooler
    SUPABASE_DB_REGION: str = Field(default="us-east-1")
    # Optional full pooler host override (e.g. aws-0-us-east-1.pooler.supabase.com)
    SUPABASE_DB_POOLER_HOST: str | None = Field(default=None)
    # Direct db.<ref>.supabase.co is IPv6-only; keep pooler enabled for Docker
    SUPABASE_DB_USE_POOLER: bool = Field(default=True)

    # Optional override; otherwise derived from SUPABASE_URL + SUPABASE_DB_PASSWORD
    DATABASE_URL: str | None = Field(default=None)
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    CORS_ORIGINS: List[str] | str = Field(default_factory=lambda: ["http://localhost:3000"])

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
    LLM_PRIMARY: str = Field(default="deepseek")
    LLM_FALLBACKS: str = Field(default="")
    GEMINI_API_KEY: SecretStr = Field(default=SecretStr(""))
    GEMINI_MODEL: str = Field(default="gemini-2.0-flash")
    NVIDIA_API_KEY: SecretStr = Field(default=SecretStr(""))
    NVIDIA_MODEL: str = Field(default="meta/llama-3.1-70b-instruct")
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

    EVENTS_ENABLED: bool = Field(default=False)
    EVENTS_HTTP_TIMEOUT_SECONDS: float = Field(default=20.0)
    EVENTS_DISCOVERY_INTERVAL_HOURS: int = Field(default=12)
    EVENTS_REDIS_LOCK_TTL_SECONDS: int = Field(default=1800)
    EVENTS_SOURCE_URLS: str = Field(default="")
    EVENTS_GENERIC_LLM_ENABLED: bool = Field(default=False)
    EVENTS_GENERIC_BROWSER_ENABLED: bool = Field(default=False)

    @model_validator(mode="after")
    def _resolve_database_url(self) -> "Settings":
        if self.DATABASE_URL:
            object.__setattr__(
                self, "DATABASE_URL", normalize_database_url(self.DATABASE_URL)
            )
            return self

        if self.SUPABASE_URL and self.SUPABASE_DB_PASSWORD:
            password = self.SUPABASE_DB_PASSWORD.get_secret_value()
            if password:
                object.__setattr__(
                    self,
                    "DATABASE_URL",
                    build_supabase_database_url(
                        self.SUPABASE_URL,
                        password,
                        region=self.SUPABASE_DB_REGION,
                        use_pooler=self.SUPABASE_DB_USE_POOLER,
                        pooler_host=self.SUPABASE_DB_POOLER_HOST,
                    ),
                )
                return self

        raise ValueError(
            "Database not configured: set DATABASE_URL or "
            "SUPABASE_URL + SUPABASE_DB_PASSWORD (Supabase Dashboard → Database)"
        )

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

    @property
    def EVENT_SOURCE_URLS_LIST(self) -> list[str]:
        if not self.EVENTS_SOURCE_URLS.strip():
            return []
        return [
            url.strip()
            for url in self.EVENTS_SOURCE_URLS.split(",")
            if url.strip()
        ]

    @property
    def llm_fallback_list(self) -> list[str]:
        if not self.LLM_FALLBACKS.strip():
            return []
        return [
            value.strip()
            for value in self.LLM_FALLBACKS.split(",")
            if value.strip()
        ]

    def database_connect_args(self) -> dict:
        """Driver kwargs for create_async_engine (SSL required for Supabase)."""
        args: dict = {}
        if self.DATABASE_URL and self.DATABASE_URL.startswith("postgresql+asyncpg"):
            args["statement_cache_size"] = 0
        if self.DATABASE_URL and (
            "supabase.co" in self.DATABASE_URL
            or "pooler.supabase.com" in self.DATABASE_URL
        ):
            # asyncpg: 'require' encrypts without strict cert verification issues
            # seen with ssl=True in slim Docker images talking to Supavisor.
            args["ssl"] = "require"
        return args


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
