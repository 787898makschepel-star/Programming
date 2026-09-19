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
    ADMIN_IDS: List[int] = []
    DB_URL: str = "sqlite+aiosqlite:///data/bot.db"
    
    SUPPORT_USERNAME: str = "@williwonka_operator"
    REVIEWS_CHANNEL: str = "@mwaves_reviews"
    FAQ_URL: str = "https://telegra.ph/FAQ-Mwaves-Shop"
    USDT_TRC20_WALLET: str = "TN5cCxeGdhW5rtAJqhyG9ZMthUUTSwyGNQ"
    USDT_BEP20_WALLET: str = "0x8fC4a10D01E7ed24AF14dBC78A134A88785853f8"
    BNB_BEP20_WALLET: str = "0x52908400098527886E0F7030069857D2E4169EE7"
    BTC_WALLET: str = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
    ETH_ERC20_WALLET: str = "0x8fC4a10D01E7ed24AF14dBC78A134A88785853f8"
    LTC_WALLET: str = "ltc1qg4n8f5k8z8j2m7w3s6r9p0v4c2x6y8t5d7f9a"
    
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
