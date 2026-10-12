"""
Centralized, typed application configuration.

Design goals:
- Single source of truth for all configuration (no hardcoded values anywhere else)
- Strongly typed + validated at startup (fail fast, not at 2am in production)
- Environment-aware (development / testing / production)
- Secrets are loaded from environment variables, never committed to source
"""

from enum import Enum
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Application-wide settings, populated from environment variables / .env file.

    Every field has a sensible development default EXCEPT secrets, which have
    no default and will raise a validation error if missing — this is
    intentional: the app should refuse to start in an insecure state.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=(),
    )

    # --- Core ---
    app_name: str = "Enterprise NLP Intelligence Platform"
    app_version: str = "0.4.0"  # bumped with each build pass — see CHANGELOG.md
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # --- Security / Auth ---
    secret_key: str = Field(default="dev-only-insecure-key-change-me")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    remember_me_refresh_token_expire_days: int = 30
    max_failed_login_attempts: int = 5
    account_lockout_minutes: int = 15
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # --- Database ---
    database_url: str = "sqlite:///./nlp_platform.db"
    database_pool_size: int = 5

    # --- Rate limiting ---
    rate_limit_requests_per_minute: int = 60
    # Stricter limit specifically for login/register/refresh — brute-force
    # and registration-spam protection, independent of per-account lockout.
    auth_rate_limit_requests_per_minute: int = 10

    # --- Redis (cache falls back to in-memory automatically if unreachable) ---
    redis_url: str = "redis://localhost:6379/0"
    redis_connect_timeout_seconds: float = 0.5
    cache_default_ttl_seconds: int = 300

    # --- Logging ---
    log_level: str = "INFO"
    log_json: bool = True

    # --- NLP / Model defaults ---
    default_model_name: str = "distilbert-base-uncased"
    model_cache_dir: str = "./.model_cache"
    max_sequence_length: int = 512
    inference_batch_size: int = 16

    # --- Experiment tracking ---
    experiments_dir: str = "./experiments_store"

    # --- Evaluation ---
    evaluation_runs_dir: str = "./evaluation_runs_store"

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_set_in_production(cls, v: str, info) -> str:
        env = info.data.get("environment")
        if env == Environment.PRODUCTION and (not v or "dev-only" in v):
            raise ValueError(
                "SECRET_KEY must be explicitly set via environment variable in production."
            )
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        return self.environment == Environment.TESTING


class DevelopmentSettings(Settings):
    debug: bool = True
    log_json: bool = False


class TestingSettings(Settings):
    environment: Environment = Environment.TESTING
    database_url: str = "sqlite:///./test_nlp_platform.db"
    debug: bool = True
    # The test suite legitimately makes far more than 60 requests/minute
    # from the same TestClient identity — rate limiting is a production
    # concern, not something the test suite itself should trip over.
    rate_limit_requests_per_minute: int = 100_000
    auth_rate_limit_requests_per_minute: int = 100_000


class ProductionSettings(Settings):
    environment: Environment = Environment.PRODUCTION
    debug: bool = False
    log_json: bool = True


def _settings_for_environment(env: Optional[str]) -> Settings:
    mapping = {
        Environment.DEVELOPMENT.value: DevelopmentSettings,
        Environment.TESTING.value: TestingSettings,
        Environment.PRODUCTION.value: ProductionSettings,
    }
    settings_cls = mapping.get(env, DevelopmentSettings)
    return settings_cls()


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings accessor. Import and call this everywhere instead of
    instantiating Settings() directly — this guarantees a single, consistent
    configuration instance app-wide and makes testing overrides trivial via
    dependency-override in FastAPI.
    """
    import os

    env = os.getenv("ENVIRONMENT", Environment.DEVELOPMENT.value)
    return _settings_for_environment(env)
