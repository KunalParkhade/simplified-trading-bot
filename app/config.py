"""App configuration via pydantic-settings.

All settings are read from environment variables (or a `.env` file at the
project root).  A single cached ``Settings`` instance is created once at
startup via :func:`get_settings` and shared across the process.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings resolved from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Binance
    # ------------------------------------------------------------------
    binance_api_key: str = ""
    binance_api_secret: str = ""
    binance_base_url: str = "https://testnet.binancefuture.com"

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    app_name: str = "Trading Bot API"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    cors_origins: list[str] = ["*"]


@lru_cache
def get_settings() -> Settings:
    """Return (and cache) the application settings singleton."""
    return Settings()
