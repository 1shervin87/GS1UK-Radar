from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "GS1 UK Regulatory Radar"
    environment: Literal["development", "production"] = "development"
    database_url: str = "sqlite:///./data/radar.db"
    static_dir: str = "static"

    # Scheduling ---------------------------------------------------------
    schedule_enabled: bool = True
    schedule_timezone: str = "Europe/London"
    schedule_day_of_week: str = "mon"
    schedule_hour: int = 8
    schedule_minute: int = 0
    run_on_startup: bool = False
    lookback_days: int = 7

    # LLM ----------------------------------------------------------------
    llm_provider: Literal["anthropic", "openai"] = "anthropic"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-20250514"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    # Any OpenAI-compatible endpoint, e.g. Google Gemini's free tier:
    #   OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/  OPENAI_MODEL=gemini-2.5-flash
    openai_base_url: str | None = None
    llm_max_items_to_analyse: int = 40
    llm_triage_batch_size: int = 20
    relevance_threshold: int = Field(default=55, ge=0, le=100)

    # Search connectors --------------------------------------------------
    tavily_api_key: str | None = None
    enable_govuk_search: bool = True
    enable_legislation_feed: bool = True
    enable_web_search: bool = True
    max_results_per_query: int = 8
    fetch_concurrency: int = 6
    fetch_timeout_seconds: float = 20.0
    max_article_chars: int = 9000

    # Security -----------------------------------------------------------
    admin_token: str | None = None
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def llm_configured(self) -> bool:
        if self.llm_provider == "anthropic":
            return bool(self.anthropic_api_key)
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
