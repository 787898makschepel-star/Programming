from typing import Dict, Any
from aiogram import Bot
from aiogram.types import LabeledPrice
from .payment_base import BasePaymentService


class TelegramStarsService(BasePaymentService):
    """
    Платежный сервис для нативной оплаты через Telegram Stars (XTR).
    Идеально подходит для покупки цифровых товаров внутри Telegram.
    """

    def __init__(self, bot: Bot):
        self.bot = bot

    async def create_invoice(
        self,
        user_id: int,
        amount: float,
        title: str = "Пополнение баланса",
        description: str = "Оплата через Telegram Stars",
        payload: str = ""
    ) -> Dict[str, Any]:
        """
        Отправляет пользователю инвойс на оплату в Telegram Stars (валюта XTR).
        1 XTR ~ эквивалент виртуальной валюты Telegram.
        """
        # В Stars сумма передается целым числом звезд
        stars_amount = max(1, int(amount))
        prices = [LabeledPrice(label=title, amount=stars_amount)]

        msg = await self.bot.send_invoice(
            chat_id=user_id,
            title=title,
            description=description,
            payload=payload,
            currency="XTR",
            prices=prices,
            provider_token=""  # Для Telegram Stars provider_token всегда пустой
        )
        return {"invoice_message_id": msg.message_id, "amount": stars_amount}

    async def verify_payment(self, invoice_id: str) -> bool:
        # Для Stars проверка происходит через PreCheckoutQuery и SuccessfulPayment хэндлеры
        return True
