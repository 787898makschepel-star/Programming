from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from config import config
from keyboards.inline_admin import get_admin_settings_kb
from utils.formatters import DIVIDER
from utils.ui_cleaner import send_or_edit_screen

router = Router(name="admin_settings")


def _format_admin_ids() -> str:
    """Форматирует список администраторов без лишних деталей."""
    return ", ".join(f"<code>{admin_id}</code>" for admin_id in config.ADMIN_IDS) or "<i>не заданы</i>"


def _format_setting(value: str) -> str:
    return f"<code>{value or 'не задано'}</code>"


@router.callback_query(F.data == "adm_settings")
async def show_admin_settings(call: CallbackQuery, state: FSMContext):
    """Показывает текущую конфигурацию бота только администраторам."""
    text = (
        "⚙️ <b>Настройки бота</b>\n"
        f"{DIVIDER}\n"
        "Текущая конфигурация загружается из файла <code>.env</code>.\n\n"
        f"🛟 <b>Поддержка:</b> {_format_setting(config.SUPPORT_USERNAME)}\n"
        f"💠 <b>Канал отзывов:</b> {_format_setting(config.REVIEWS_CHANNEL)}\n"
        f"📖 <b>FAQ:</b> {_format_setting(config.FAQ_URL)}\n"
        f"🧾 <b>Группа чеков:</b> <code>{config.RECEIPTS_GROUP_ID}</code>\n"
        f"👑 <b>Администраторы:</b> {_format_admin_ids()}\n"
        f"💳 <b>CryptoBot:</b> {'🟢 подключен' if config.CRYPTO_BOT_TOKEN else '⚪ не настроен'}\n"
        f"💳 <b>Банковская оплата:</b> {'🟢 подключена' if config.TELEGRAM_PAYMENT_PROVIDER_TOKEN else '⚪ не настроена'}\n"
        f"{DIVIDER}\n"
        "Для изменения параметров обновите значения в <code>.env</code> и перезапустите бота."
    )
    await send_or_edit_screen(call, text, reply_markup=get_admin_settings_kb(), state=state)
    await call.answer()