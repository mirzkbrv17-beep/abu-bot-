from decimal import Decimal
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str = "0:test"
    bot_username: str = ""
    admin_ids: str = ""
    database_url: str = "sqlite+aiosqlite:///./abu.db"
    webhook_base_url: str = ""
    webhook_secret: str = "change-me"
    referral_bonus_abu_f: Decimal = Decimal("50")
    market_fee_percent: Decimal = Decimal("5")
    admin_panel_token: str = ""

    @field_validator("database_url")
    @classmethod
    def _fix_db_url(cls, v: str) -> str:
        # Render "postgres://" yoki "postgresql://" beradi, SQLAlchemy async uchun moslaymiz
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            v = "postgresql+asyncpg://" + v[len("postgresql://"):]
        return v

    @property
    def admin_id_set(self) -> set[int]:
        return {int(x) for x in self.admin_ids.replace(" ", "").split(",") if x.isdigit()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
