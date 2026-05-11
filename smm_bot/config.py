from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    # Bot
    BOT_TOKEN: str
    ADMIN_IDS: str  # comma-separated string
    FORCE_CHANNELS: str  # comma-separated string

    # SMM API
    SMM_API_URL: str
    SMM_API_KEY: str

    # Virtual Number API
    NUMBER_API_URL: str
    NUMBER_API_KEY: str

    # Payment
    PAYME_MERCHANT_ID: str = ""
    PAYME_SECRET_KEY: str = ""
    CLICK_MERCHANT_ID: str = ""
    CLICK_SECRET_KEY: str = ""

    # Bot Settings
    DAILY_BONUS_AMOUNT: int = 200
    REFERRAL_BONUS_AMOUNT: int = 1000
    MIN_DEPOSIT: int = 5000
    SUPPORT_CHAT_ID: int = 0

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///smm_bot.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def admin_ids_list(self) -> List[int]:
        return [int(i.strip()) for i in self.ADMIN_IDS.split(",") if i.strip()]

    @property
    def force_channels_list(self) -> List[str]:
        return [c.strip() for c in self.FORCE_CHANNELS.split(",") if c.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()