from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: SecretStr = Field(..., alias="TELEGRAM_BOT_TOKEN")
    llm_api_base_url: str = Field(..., alias="LLM_API_BASE_URL")
    llm_api_key: SecretStr = Field(..., alias="LLM_API_KEY")
    llm_model: str = Field(default="default", alias="LLM_MODEL")
    database_url: str = Field(default="sqlite:///storage/bondly.sqlite3", alias="DATABASE_URL")
    memory_storage_dir: str = Field(default="storage/memory", alias="MEMORY_STORAGE_DIR")
    app_timezone: str = Field(default="Europe/Moscow", alias="APP_TIMEZONE")
    reminder_poll_interval_seconds: int = Field(
        default=30,
        ge=5,
        le=3600,
        alias="REMINDER_POLL_INTERVAL_SECONDS",
    )
    daily_digest_time: str = Field(default="09:00", alias="DAILY_DIGEST_TIME")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8-sig")

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.app_timezone)


@lru_cache
def get_settings() -> Settings:
    return Settings()
