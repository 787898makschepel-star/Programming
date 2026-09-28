import json
import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """
    Класс конфигурации проекта. Загружает переменные из файла .env.
    """
    BOT_TOKEN: str = ""
    BOT_TOKEN_2: str = ""
    ADMIN_IDS: List[int] = []
    DB_URL: str = "sqlite+aiosqlite:///data/bot.db"
    
    START_STICKER_ID: str = "CAACAgIAAxkBAAEHFCRqrGcwLKCbKyZpF__HJ9KnVhpwfAACMWoAAi38IEs5Qp_3NDiFkz0E"
    BUTTON_EMOJI_ID: str = "5404573776253825754"
    BUTTON_LABELS: str = "{}"
    BUTTON_EMOJI_IDS: str = "{}"
    SUPPORT_USERNAME: str = "@williwonka_operator"
    REVIEWS_CHANNEL: str = "@mwaves_reviews"
    FAQ_URL: str = "https://telegra.ph/FAQ-Mwaves-Shop"
    USDT_TRC20_ADDRESS: str = "TFxNg46apWAirutFCKPTrntWyjvzmkzV9m"
    USDT_ERC20_ADDRESS: str = "0x8782dFC5801D1ce09d9BC38d125FE7FDb4A1534A"
    USDT_BEP20_ADDRESS: str = "0x8782dFC5801D1ce09d9BC38d125FE7FDb4A1534A"
    
    RECEIPTS_GROUP_ID: int = -5458584510
    CRYPTO_BOT_TOKEN: str = ""
    TELEGRAM_PAYMENT_PROVIDER_TOKEN: str = ""

    @field_validator("ADMIN_IDS", mode="before")
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            value = v.strip()
            if not value:
                return []
            if value.startswith("["):
                parsed = json.loads(value)
                if not isinstance(parsed, list):
                    raise ValueError("ADMIN_IDS должен быть списком ID")
                return [int(item) for item in parsed]
            return [int(item.strip()) for item in value.split(",") if item.strip().isdigit()]
        elif isinstance(v, (list, set, tuple)):
            return [int(x) for x in v]
        elif isinstance(v, int):
            return [v]
        return []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Экземпляр настроек
config = Settings()


def get_receipts_chat_ids() -> List[int]:
    """Возвращает список возможных ID для группы чеков (обычный и supergroup)."""
    raw_id = config.RECEIPTS_GROUP_ID
    ids = [raw_id]
    s = str(raw_id)
    if not s.startswith("-100"):
        cleaned = s.lstrip("-")
        ids.append(int(f"-100{cleaned}"))
    return ids
