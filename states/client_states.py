from aiogram.fsm.state import State, StatesGroup


class TopUpState(StatesGroup):
    """FSM состояния для процесса пополнения баланса."""
    waiting_for_amount = State()
    waiting_for_method = State()


class DirectBuyState(StatesGroup):
    """FSM состояния для прямой покупки."""
    waiting_for_method = State()


class PromoState(StatesGroup):
    """FSM ввода промокода."""
    waiting_for_code = State()


class CryptoTxState(StatesGroup):
    """FSM ожидания чека или хэша транзакции USDT TRC20."""
    waiting_for_tx_hash = State()
    waiting_for_receipt = State()

