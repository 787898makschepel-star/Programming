"""
services/exchange_rate.py — актуальный биржевой курс USDT/RUB с кэшированием и многоуровневым fallback.
"""

import time
import logging
import aiohttp
from typing import Tuple

logger = logging.getLogger(__name__)

# Кэш курса
_cached_rate: float = 95.0
_cache_timestamp: float = 0.0
CACHE_TTL = 300  # 5 минут


async def get_usdt_rub_rate() -> float:
    """
    Возвращает актуальный биржевой курс USDT к рублю.
    Кэширует результат на 5 минут, чтобы не спамить API.
    В случае сетевой ошибки возвращает последнее известное значение или безопасный fallback.
    """
    global _cached_rate, _cache_timestamp
    now = time.time()

    if _cached_rate > 0 and (now - _cache_timestamp) < CACHE_TTL:
        return _cached_rate

    # 1. Попытка через CoinGecko
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=rub"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=4.0)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    rate = float(data.get("tether", {}).get("rub", 0.0))
                    if rate > 10.0:
                        _cached_rate = round(rate, 2)
                        _cache_timestamp = now
                        logger.info("USDT/RUB rate updated from CoinGecko: %s", _cached_rate)
                        return _cached_rate
    except Exception as e:
        logger.debug("CoinGecko rate fetch failed: %s", e)

    # 2. Попытка через Binance ticker (USDT / RUB)
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.binance.com/api/v3/ticker/price?symbol=USDTRUB"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=4.0)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    rate = float(data.get("price", 0.0))
                    if rate > 10.0:
                        _cached_rate = round(rate, 2)
                        _cache_timestamp = now
                        logger.info("USDT/RUB rate updated from Binance: %s", _cached_rate)
                        return _cached_rate
    except Exception as e:
        logger.debug("Binance rate fetch failed: %s", e)

    # Возврат кэшированного значения или fallback
    return _cached_rate


async def convert_usdt_to_rub(usdt_amount: float) -> Tuple[float, float]:
    """
    Конвертирует USDT в рубли.
    Возвращает кортеж: (сумма_в_рублях, применённый_курс).
    """
    rate = await get_usdt_rub_rate()
    if rate <= 0:
        rate = 95.0
    rub_amount = round(usdt_amount * rate, 2)
    return rub_amount, rate


async def convert_rub_to_usdt(rub_amount: float) -> Tuple[float, float]:
    """
    Конвертирует рубли в USDT.
    Возвращает кортеж: (сумма_в_usdt, применённый_курс).
    """
    rate = await get_usdt_rub_rate()
    if rate <= 0:
        rate = 95.0
    usdt_amount = round(rub_amount / rate, 2)
    return usdt_amount, rate
