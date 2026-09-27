from pathlib import Path
from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from config import config
from keyboards.inline_admin import get_admin_settings_kb, get_button_editor_kb
from states.admin_states import ChangeStartStickerState, EditButtonState
from utils.formatters import DIVIDER
from utils.ui_cleaner import send_or_edit_screen
from utils.button_settings import button_details, button_key_by_index, registered_buttons, save_button_override

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
        f"🎭 <b>Стартовый стикер:</b> <code>{config.START_STICKER_ID}</code>\n"
        f"👑 <b>Администраторы:</b> {_format_admin_ids()}\n"
        f"💳 <b>CryptoBot:</b> {'🟢 подключен' if config.CRYPTO_BOT_TOKEN else '⚪ не настроен'}\n"
        f"💳 <b>Банковская оплата:</b> {'🟢 подключена' if config.TELEGRAM_PAYMENT_PROVIDER_TOKEN else '⚪ не настроена'}\n"
        f"{DIVIDER}\n"
        "Для изменения параметров обновите значения в <code>.env</code> и перезапустите бота.\n"
        "Либо используйте кнопку ниже, чтобы сменить стартовый стикер прямо из чата."
    )
    await send_or_edit_screen(call, text, reply_markup=get_admin_settings_kb(), state=state)
    await call.answer()


@router.callback_query(F.data == "adm_change_start_sticker")
async def change_start_sticker_prompt(call: CallbackQuery, state: FSMContext):
    """Просит администратора отправить новый стикер для /start."""
    await state.set_state(ChangeStartStickerState.waiting_for_sticker)
    text = (
        "🎭 <b>Изменение стартового стикера</b>\n"
        f"{DIVIDER}\n"
        "Отправьте любой <b>стикер</b> в ответ на это сообщение.\n"
        "Бот сохранит его <code>file_id</code> и будет использовать его после команды /start."
    )
    await send_or_edit_screen(call, text, reply_markup=get_admin_settings_kb(), state=state)
    await call.answer()


@router.callback_query(F.data == "adm_edit_buttons")
async def show_button_editor(call: CallbackQuery, state: FSMContext):
    """Показывает кнопки, которые можно переименовать."""
    if not registered_buttons():
        await call.answer("Сначала откройте меню бота, чтобы зарегистрировать кнопки.", show_alert=True)
        return
    text = (
        "✏️ <b>Редактирование кнопок</b>\n"
        f"{DIVIDER}\n"
        "Выберите кнопку. Её подпись и custom emoji можно изменить отдельно."
    )
    await send_or_edit_screen(call, text, reply_markup=get_button_editor_kb(0), state=state)
    await call.answer()


@router.callback_query(F.data.startswith("adm_button_page_"))
async def show_button_editor_page(call: CallbackQuery, state: FSMContext):
    try:
        page = max(int(call.data.rsplit("_", 1)[-1]), 0)
    except (TypeError, ValueError):
        await call.answer("Не удалось открыть страницу.", show_alert=True)
        return
    text = (
        "✏️ <b>Редактирование кнопок</b>\n"
        f"{DIVIDER}\n"
        "Выберите кнопку главного меню для изменения текста и custom emoji."
    )
    await send_or_edit_screen(call, text, reply_markup=get_button_editor_kb(page), state=state)
    await call.answer()


@router.callback_query(F.data.startswith("adm_button_edit_"))
async def edit_button_prompt(call: CallbackQuery, state: FSMContext):
    """Запрашивает новый текст и emoji ID выбранной кнопки."""
    try:
        index = int(call.data.rsplit("_", 1)[-1])
    except (TypeError, ValueError):
        await call.answer("Не удалось определить кнопку.", show_alert=True)
        return
    key = button_key_by_index(index, "main_menu")
    if not key:
        await call.answer("Кнопка больше не зарегистрирована. Откройте список заново.", show_alert=True)
        return
    current_label, current_emoji_id = button_details(key)
    await state.update_data(button_key=key)
    await state.set_state(EditButtonState.waiting_for_settings)
    await call.message.answer(
        "✏️ <b>Изменение кнопки</b>\n"
        f"{DIVIDER}\n"
        f"Текущий текст: <code>{escape(current_label)}</code>\n"
        f"Текущий emoji ID: <code>{escape(current_emoji_id or 'по умолчанию')}</code>\n\n"
        "Отправьте двумя строками:\n"
        "1. новый текст кнопки\n"
        "2. custom emoji ID или <code>-</code>, чтобы использовать общий ID",
        parse_mode="HTML"
    )
    await call.answer()


@router.message(EditButtonState.waiting_for_settings)
async def save_button_settings(message: Message, state: FSMContext):
    """Сохраняет подпись и emoji ID кнопки в .env."""
    if not message.text:
        await message.answer("❌ Отправьте текст двумя строками: подпись и emoji ID.")
        return
    lines = [line.strip() for line in message.text.splitlines()]
    if len(lines) not in (1, 2) or not lines[0] or len(lines[0]) > 64:
        await message.answer("❌ Нужна подпись длиной 1-64 символа и, при необходимости, вторая строка с emoji ID.")
        return
    emoji_id = lines[1] if len(lines) == 2 else ""
    if emoji_id == "-":
        emoji_id = ""
    if emoji_id and not emoji_id.isdigit():
        await message.answer("❌ emoji ID должен содержать только цифры или быть <code>-</code>.", parse_mode="HTML")
        return
    data = await state.get_data()
    key = data.get("button_key")
    if not key:
        await state.clear()
        await message.answer("❌ Сессия редактирования устарела. Откройте редактор заново.")
        return
    save_button_override(key, lines[0], emoji_id)
    await state.clear()
    await message.answer(
        f"✅ Кнопка обновлена: <b>{escape(lines[0])}</b>\n"
        f"Emoji ID: <code>{escape(emoji_id or 'общий')}</code>\n\n"
        "Откройте нужное меню заново, чтобы увидеть изменения.",
        parse_mode="HTML"
    )


@router.message(ChangeStartStickerState.waiting_for_sticker)
async def save_start_sticker(message: Message, state: FSMContext):
    """Сохраняет file_id нового стартового стикера в .env и текущую конфигурацию."""
    if not message.sticker:
        await message.answer("❌ Это не стикер. Отправьте именно стикер, чтобы сменить стартовый эмодзи.")
        return

    sticker_id = message.sticker.file_id
    config.START_STICKER_ID = sticker_id

    env_path = Path(".env")
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
        updated = False
        new_lines = []
        for line in lines:
            if line.startswith("START_STICKER_ID="):
                new_lines.append(f"START_STICKER_ID={sticker_id}")
                updated = True
            else:
                new_lines.append(line)
        if not updated:
            new_lines.append(f"START_STICKER_ID={sticker_id}")
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    await message.answer(
        f"✅ <b>Стартовый стикер обновлён</b>\n"
        f"{DIVIDER}\n"
        f"<code>{sticker_id}</code>",
        parse_mode="HTML"
    )
    await state.clear()