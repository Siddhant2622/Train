from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """All configuration loaded from environment variables / .env file.
    
    Pydantic-settings validates types on startup — a missing required var
    raises at import time, not at runtime when a request hits that code path.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Database ----
    database_url: str

    # ---- Redis ----
    redis_url: str = "redis://localhost:6379"

    # ---- JWT ----
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # ---- CORS ----
    # Comma-separated list; parsed into a list by the property below.
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ---- Environment ----
    environment: str = "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    # ---- Sentry ----
    sentry_dsn: str = ""

    # ---- Internal service auth (simulator → API) ----
    internal_api_key: str = "dev-internal-key-change-in-production"

    # ---- API ----
    api_port: int = 8000



@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance.
    
    Use FastAPI's Depends(get_settings) pattern in route handlers so tests
    can override this easily via app.dependency_overrides.
    """
    return Settings()
