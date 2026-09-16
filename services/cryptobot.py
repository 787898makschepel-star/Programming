import aiohttp
from typing import Dict, Any, Optional
from config import config
from .payment_base import BasePaymentService


class CryptoBotService(BasePaymentService):
    """
    Сервис приема криптовалюты через официальный API @CryptoBot (@send).
    Поддерживает USDT, TON, BTC, NOT, TRX и фиатные эквиваленты.
    """

    BASE_URL = "https://pay.crypt.bot/api"

    def __init__(self, token: Optional[str] = None):
        self.token = token or config.CRYPTO_BOT_TOKEN

    async def create_invoice(
        self,
        user_id: int,
        amount: float,
        title: str = "Пополнение баланса",
        description: str = "Оплата через CryptoBot",
        payload: str = ""
    ) -> Dict[str, Any]:
        """
        Создает инвойс в CryptoBot и возвращает pay_url.
        """
        if not self.token:
            return {"error": "CRYPTO_BOT_TOKEN не настроен в .env"}

        headers = {"Crypto-Pay-API-Token": self.token}
        data = {
            "amount": str(amount),
            "currency_type": "fiat",
            "fiat": "RUB",
            "description": description,
            "payload": payload,
            "expires_in": 3600
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.BASE_URL}/createInvoice", json=data, headers=headers) as response:
                result = await response.json()
                if result.get("ok"):
                    invoice = result["result"]
                    return {
                        "invoice_id": invoice["invoice_id"],
                        "pay_url": invoice["pay_url"],
                        "status": invoice["status"]
                    }
                return {"error": result.get("description", "Ошибка создания инвойса в CryptoBot")}

    async def verify_payment(self, invoice_id: str) -> bool:
        """Проверить, оплачен ли инвойс."""
        if not self.token:
            return False

        headers = {"Crypto-Pay-API-Token": self.token}
        params = {"invoice_ids": invoice_id}

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.BASE_URL}/getInvoices", params=params, headers=headers) as response:
                result = await response.json()
                if result.get("ok") and result.get("result", {}).get("items"):
                    item = result["result"]["items"][0]
                    return item.get("status") == "paid"
                return False
