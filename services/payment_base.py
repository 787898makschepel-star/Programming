from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BasePaymentService(ABC):
    """
    Абстрактный базовый класс для подключения любых платежных шлюзов
    (Telegram Stars, CryptoPay, ЮKassa, Stripe, Qiwi и т.д.).
    """

    @abstractmethod
    async def create_invoice(
        self,
        user_id: int,
        amount: float,
        title: str,
        description: str,
        payload: str
    ) -> Dict[str, Any]:
        """
        Создание счета на оплату.
        Возвращает словарь с параметрами инвойса или ссылкой на оплату.
        """
        pass

    @abstractmethod
    async def verify_payment(self, invoice_id: str) -> bool:
        """
        Проверка статуса оплаты по идентификатору инвойса.
        """
        pass
