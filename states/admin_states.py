from aiogram.fsm.state import State, StatesGroup


class AddCategoryState(StatesGroup):
    """FSM создания категории/подкатегории."""
    waiting_for_name = State()
    waiting_for_parent = State()


class UploadStockState(StatesGroup):
    """FSM залива позиций (аккаунтов, ключей) в товар."""
    waiting_for_product = State()
    waiting_for_file_or_text = State()


class EditPriceState(StatesGroup):
    """FSM редактирования цены товара."""
    waiting_for_product = State()
    waiting_for_new_price = State()


class ShowcaseProductState(StatesGroup):
    """FSM редактирования товара клиентской витрины."""
    waiting_for_title = State()
    waiting_for_price = State()
    waiting_for_unit = State()
    waiting_for_quantity = State()
    waiting_for_image = State()


class UserSearchState(StatesGroup):
    """FSM поиска пользователя."""
    waiting_for_query = State()


class UserBalanceState(StatesGroup):
    """FSM изменения баланса пользователя админом."""
    waiting_for_user_id = State()
    waiting_for_amount = State()


class BroadcastState(StatesGroup):
    """FSM создания и отправки рассылки."""
    waiting_for_content = State()
    waiting_for_confirmation = State()


class AdminReceiptState(StatesGroup):
    """FSM ожидания суммы в рублях от администратора для чека."""
    waiting_for_amount = State()

