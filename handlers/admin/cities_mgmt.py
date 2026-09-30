"""
Панель управления городами и районами для администратора.

Функционал:
  • Список городов с пагинацией
  • Добавление нового города (ввод названия → ввод районов)
  • Добавление районов к существующему городу
  • Переименование города
  • Переименование района
  • Удаление района (с подтверждением)
  • Удаление города (с подтверждением, удаляет и все районы)
  • Пагинация районов внутри города (по 6 шт.)

После любого изменения:
  • Кэш CITY_DISTRICTS/CITY_CODES обновляется через sync_city_districts_cache
  • Клиентский каталог немедленно видит обновлённый список городов/районов
"""

import re
from typing import Optional

from aiogram import F, Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import (
    add_district,
    create_city,
    delete_city,
    delete_district,
    get_all_cities,
    get_city_by_id,
    get_city_districts,
    get_district_by_id,
    rename_city,
    rename_district,
)
from keyboards.inline_admin import (
    InlineKeyboardButton,
    get_admin_cities_kb,
    get_admin_city_del_confirm_kb,
    get_admin_city_rename_kb,
    get_admin_city_view_kb,
    get_admin_dist_del_confirm_kb,
    get_admin_dist_rename_kb,
)
from states.admin_states import CityMgmtState
from utils.callback_parser import parse_callback_int, split_callback_suffix
from utils.formatters import DIVIDER
from utils.ui_cleaner import delete_user_message, send_or_edit_screen

router = Router(name="admin_cities_mgmt")


# ─────────────────────────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ ЭКРАНЫ
# ─────────────────────────────────────────────────────────────────────

async def show_cities_screen(
    target, session: AsyncSession, state: FSMContext, page: int = 0, bot: Optional[Bot] = None
) -> None:
    cities = await get_all_cities(session)
    text = (
        "🏙️ <b>Управление городами и районами</b>\n"
        f"{DIVIDER}\n"
        f"Активных городов: <b>{len(cities)}</b>\n\n"
        "Выберите город для управления районами или добавьте новый:"
    )
    await send_or_edit_screen(target, text, reply_markup=get_admin_cities_kb(cities, page=page), state=state, bot=bot)


async def show_city_screen(
    target, city_id: int, session: AsyncSession, state: FSMContext, page: int = 0, bot: Optional[Bot] = None
) -> None:
    city = await get_city_by_id(session, city_id)
    if not city:
        await show_cities_screen(target, session, state, page=0, bot=bot)
        return

    districts = [d for d in city.districts if d.is_active]
    dist_lines = ""
    if districts:
        dist_lines = "\n" + "\n".join(
            f"  {i}. {d.name}" for i, d in enumerate(districts[:20], 1)
        )
        if len(districts) > 20:
            dist_lines += f"\n  <i>... и ещё {len(districts) - 20}</i>"
    else:
        dist_lines = "\n<i>Районов ещё нет. Добавьте ниже.</i>"

    text = (
        f"📍 <b>Город: {city.name}</b>\n"
        f"{DIVIDER}"
        f"{dist_lines}\n\n"
        "Управление: переименуйте или удалите через кнопки ниже."
    )
    await send_or_edit_screen(
        target, text, reply_markup=get_admin_city_view_kb(city, districts, page=page), state=state, bot=bot
    )


# ─────────────────────────────────────────────────────────────────────
# СПИСОК ГОРОДОВ
# ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_cities")
async def open_cities_mgmt(call: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    await show_cities_screen(call, session, state, page=0)
    await call.answer()


@router.callback_query(F.data.startswith("adm_cities_page_"))
async def open_cities_page(call: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    page = parse_callback_int(call.data, "adm_cities_page_") or 0
    await state.clear()
    await show_cities_screen(call, session, state, page=page)
    await call.answer()


@router.callback_query(F.data == "adm_noop")
async def cb_noop(call: CallbackQuery) -> None:
    """Пустой обработчик для кнопок-индикаторов (страница X/Y)."""
    await call.answer()


# ─────────────────────────────────────────────────────────────────────
# ПРОСМОТР ГОРОДА И ПАГИНАЦИЯ РАЙОНОВ
# ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_city_view_"))
async def open_city_view(call: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    city_id = parse_callback_int(call.data, "adm_city_view_")
    if city_id is None:
        await call.answer("Город не найден.", show_alert=True)
        return
    await state.clear()
    await show_city_screen(call, city_id, session, state, page=0)
    await call.answer()


@router.callback_query(F.data.startswith("adm_dist_page_"))
async def open_districts_page(call: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    parts = split_callback_suffix(call.data, "adm_dist_page_")
    if not parts or len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await call.answer("Ошибка страницы.", show_alert=True)
        return
    city_id, page = int(parts[0]), int(parts[1])
    await state.clear()
    await show_city_screen(call, city_id, session, state, page=page)
    await call.answer()


# ─────────────────────────────────────────────────────────────────────
# ДОБАВЛЕНИЕ НОВОГО ГОРОДА
# ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm_city_add")
async def start_add_city(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(CityMgmtState.waiting_for_city_name)
    await send_or_edit_screen(
        call,
        f"➕ <b>Добавление нового города</b>\n{DIVIDER}\n"
        "Введите название города (например: <code>Сочи</code>, <code>Калининград</code>):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="adm_cities")]
        ]),
        state=state,
    )
    await call.answer()


@router.message(CityMgmtState.waiting_for_city_name)
async def process_city_name_input(message: Message, session: AsyncSession, state: FSMContext, bot: Bot) -> None:
    await delete_user_message(message)
    raw = (message.text or "").strip()

    if not raw or len(raw) < 2 or len(raw) > 64:
        await send_or_edit_screen(
            message,
            "⚠️ Название города должно быть от 2 до 64 символов. Попробуйте ещё раз:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="adm_cities")]
            ]),
            state=state, bot=bot,
        )
        return

    city = await create_city(session, raw)
    await state.set_state(CityMgmtState.waiting_for_districts)
    await state.update_data(current_city_id=city.id, current_city_name=city.name)

    await send_or_edit_screen(
        message,
        f"✅ <b>Город «{city.name}» добавлен!</b>\n{DIVIDER}\n"
        f"Теперь добавьте районы для <b>{city.name}</b>.\n\n"
        "Отправьте названия через запятую или с новой строки:\n"
        "<code>Центральный, Адлер, Хоста</code>\n"
        "или\n"
        "<code>Центральный\nАдлер\nХоста</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🏙️ Перейти к «{city.name}»", callback_data=f"adm_city_view_{city.id}")],
            [InlineKeyboardButton(text="🔙 К списку городов", callback_data="adm_cities")],
        ]),
        state=state, bot=bot,
    )


# ─────────────────────────────────────────────────────────────────────
# ДОБАВЛЕНИЕ РАЙОНОВ К ГОРОДУ
# ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_dist_add_"))
async def start_add_districts(call: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    city_id = parse_callback_int(call.data, "adm_dist_add_")
    if city_id is None:
        await call.answer("Город не найден.", show_alert=True)
        return
    city = await get_city_by_id(session, city_id)
    if not city:
        await call.answer("Город не найден.", show_alert=True)
        return

    await state.clear()
    await state.set_state(CityMgmtState.waiting_for_districts)
    await state.update_data(current_city_id=city.id, current_city_name=city.name)

    await send_or_edit_screen(
        call,
        f"➕ <b>Добавление районов — «{city.name}»</b>\n{DIVIDER}\n"
        "Отправьте названия через запятую или с новой строки:\n"
        "<code>Центральный, Заречный, Северный</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Отмена", callback_data=f"adm_city_view_{city.id}")]
        ]),
        state=state,
    )
    await call.answer()


@router.message(CityMgmtState.waiting_for_districts)
async def process_districts_input(message: Message, session: AsyncSession, state: FSMContext, bot: Bot) -> None:
    await delete_user_message(message)
    data = await state.get_data()
    city_id: Optional[int] = data.get("current_city_id")
    city_name: str = data.get("current_city_name", "")

    if not city_id:
        await state.clear()
        await show_cities_screen(message, session, state, page=0, bot=bot)
        return

    raw_text = (message.text or "").strip()
    if not raw_text:
        return

    raw_names = re.split(r"[,\n]+", raw_text)
    clean_names = [n.strip() for n in raw_names if 1 <= len(n.strip()) <= 64]

    if not clean_names:
        await send_or_edit_screen(
            message,
            "⚠️ Не удалось распознать названия. Введите хотя бы один район:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Отмена", callback_data=f"adm_city_view_{city_id}")]
            ]),
            state=state, bot=bot,
        )
        return

    added = []
    for name in clean_names:
        dist = await add_district(session, city_id, name)
        added.append(dist.name)

    all_dists = await get_city_districts(session, city_id)
    added_str = ", ".join(f"<b>{n}</b>" for n in added)

    await send_or_edit_screen(
        message,
        f"✅ <b>Районы сохранены в «{city_name}»!</b>\n{DIVIDER}\n"
        f"Добавлено: <b>{len(added)}</b> ({added_str})\n"
        f"Итого районов: <b>{len(all_dists)}</b>\n\n"
        "Можете добавить ещё или перейти к городу:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить ещё", callback_data=f"adm_dist_add_{city_id}")],
            [InlineKeyboardButton(text=f"🏙️ К «{city_name}»", callback_data=f"adm_city_view_{city_id}")],
            [InlineKeyboardButton(text="🔙 К списку городов", callback_data="adm_cities")],
        ]),
        state=state, bot=bot,
    )


# ─────────────────────────────────────────────────────────────────────
# ПЕРЕИМЕНОВАНИЕ ГОРОДА
# ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_city_rename_"))
async def start_rename_city(call: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    city_id = parse_callback_int(call.data, "adm_city_rename_")
    if city_id is None:
        await call.answer("Город не найден.", show_alert=True)
        return
    city = await get_city_by_id(session, city_id)
    if not city:
        await call.answer("Город не найден.", show_alert=True)
        return

    await state.clear()
    await state.set_state(CityMgmtState.waiting_for_new_city_name)
    await state.update_data(rename_city_id=city.id, rename_city_old_name=city.name)

    await send_or_edit_screen(
        call,
        f"✏️ <b>Переименование города «{city.name}»</b>\n{DIVIDER}\n"
        "Введите новое название города сообщением:",
        reply_markup=get_admin_city_rename_kb(city.id),
        state=state,
    )
    await call.answer()


@router.message(CityMgmtState.waiting_for_new_city_name)
async def process_rename_city(message: Message, session: AsyncSession, state: FSMContext, bot: Bot) -> None:
    await delete_user_message(message)
    data = await state.get_data()
    city_id: Optional[int] = data.get("rename_city_id")
    old_name: str = data.get("rename_city_old_name", "")

    if not city_id:
        await state.clear()
        await show_cities_screen(message, session, state, page=0, bot=bot)
        return

    raw = (message.text or "").strip()
    if not raw or len(raw) < 2 or len(raw) > 64:
        await send_or_edit_screen(
            message,
            "⚠️ Название должно быть от 2 до 64 символов. Попробуйте ещё раз:",
            reply_markup=get_admin_city_rename_kb(city_id),
            state=state, bot=bot,
        )
        return

    city = await rename_city(session, city_id, raw)
    if city is None:
        await send_or_edit_screen(
            message,
            f"❌ Город с названием <b>«{raw}»</b> уже существует. Введите другое имя:",
            reply_markup=get_admin_city_rename_kb(city_id),
            state=state, bot=bot,
        )
        return

    await state.clear()
    await send_or_edit_screen(
        message,
        f"✅ <b>Город переименован:</b> «{old_name}» → «{city.name}»",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🏙️ К «{city.name}»", callback_data=f"adm_city_view_{city.id}")],
            [InlineKeyboardButton(text="🔙 К списку городов", callback_data="adm_cities")],
        ]),
        state=state, bot=bot,
    )


# ─────────────────────────────────────────────────────────────────────
# ПЕРЕИМЕНОВАНИЕ РАЙОНА
# ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_dist_rename_"))
async def start_rename_district(call: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    district_id = parse_callback_int(call.data, "adm_dist_rename_")
    if district_id is None:
        await call.answer("Район не найден.", show_alert=True)
        return
    district = await get_district_by_id(session, district_id)
    if not district:
        await call.answer("Район не найден.", show_alert=True)
        return

    await state.clear()
    await state.set_state(CityMgmtState.waiting_for_new_district_name)
    await state.update_data(
        rename_district_id=district.id,
        rename_district_old_name=district.name,
        rename_district_city_id=district.city_id,
    )

    await send_or_edit_screen(
        call,
        f"✏️ <b>Переименование района «{district.name}»</b>\n{DIVIDER}\n"
        "Введите новое название района сообщением:",
        reply_markup=get_admin_dist_rename_kb(district.id, district.city_id),
        state=state,
    )
    await call.answer()


@router.message(CityMgmtState.waiting_for_new_district_name)
async def process_rename_district(message: Message, session: AsyncSession, state: FSMContext, bot: Bot) -> None:
    await delete_user_message(message)
    data = await state.get_data()
    district_id: Optional[int] = data.get("rename_district_id")
    old_name: str = data.get("rename_district_old_name", "")
    city_id: Optional[int] = data.get("rename_district_city_id")

    if not district_id or not city_id:
        await state.clear()
        await show_cities_screen(message, session, state, page=0, bot=bot)
        return

    raw = (message.text or "").strip()
    if not raw or len(raw) < 1 or len(raw) > 64:
        await send_or_edit_screen(
            message,
            "⚠️ Название района должно быть от 1 до 64 символов. Попробуйте ещё раз:",
            reply_markup=get_admin_dist_rename_kb(district_id, city_id),
            state=state, bot=bot,
        )
        return

    district = await rename_district(session, district_id, raw)
    if district is None:
        await send_or_edit_screen(
            message,
            f"❌ Район <b>«{raw}»</b> уже существует в этом городе. Введите другое имя:",
            reply_markup=get_admin_dist_rename_kb(district_id, city_id),
            state=state, bot=bot,
        )
        return

    await state.clear()
    await send_or_edit_screen(
        message,
        f"✅ <b>Район переименован:</b> «{old_name}» → «{district.name}»",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🏙️ К городу", callback_data=f"adm_city_view_{city_id}")],
            [InlineKeyboardButton(text="🔙 К списку городов", callback_data="adm_cities")],
        ]),
        state=state, bot=bot,
    )


# ─────────────────────────────────────────────────────────────────────
# УДАЛЕНИЕ РАЙОНА (с подтверждением)
# ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_dist_del_"))
async def confirm_delete_district(call: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    district_id = parse_callback_int(call.data, "adm_dist_del_")
    if district_id is None:
        await call.answer("Район не найден.", show_alert=True)
        return
    district = await get_district_by_id(session, district_id)
    if not district:
        await call.answer("Район не найден.", show_alert=True)
        return

    await send_or_edit_screen(
        call,
        f"⚠️ <b>Удаление района «{district.name}»</b>\n{DIVIDER}\n"
        "Вы уверены? Пользователи с этим районом потеряют привязку.",
        reply_markup=get_admin_dist_del_confirm_kb(district_id, district.city_id),
        state=state,
    )
    await call.answer()


@router.callback_query(F.data.startswith("adm_dist_confirm_del_"))
async def execute_delete_district(call: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    district_id = parse_callback_int(call.data, "adm_dist_confirm_del_")
    if district_id is None:
        await call.answer("Район не найден.", show_alert=True)
        return

    district = await get_district_by_id(session, district_id)
    if not district:
        await call.answer("Район уже удалён.", show_alert=False)
        await show_cities_screen(call, session, state, page=0)
        return

    city_id = district.city_id
    name = district.name
    await delete_district(session, district_id)
    await call.answer(f"Район «{name}» удалён.", show_alert=False)
    await show_city_screen(call, city_id, session, state, page=0)


# ─────────────────────────────────────────────────────────────────────
# УДАЛЕНИЕ ГОРОДА (с подтверждением)
# ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm_city_del_"))
async def confirm_delete_city(call: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    city_id = parse_callback_int(call.data, "adm_city_del_")
    if city_id is None:
        await call.answer("Город не найден.", show_alert=True)
        return
    city = await get_city_by_id(session, city_id)
    if not city:
        await call.answer("Город не найден.", show_alert=True)
        return

    dist_count = len([d for d in city.districts if d.is_active])
    await send_or_edit_screen(
        call,
        f"⚠️ <b>Удаление города «{city.name}»</b>\n{DIVIDER}\n"
        f"Будет удалён город и все {dist_count} его район(а).\n"
        "Пользователи потеряют привязку. Продолжить?",
        reply_markup=get_admin_city_del_confirm_kb(city_id),
        state=state,
    )
    await call.answer()


@router.callback_query(F.data.startswith("adm_city_confirm_del_"))
async def execute_delete_city(call: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    city_id = parse_callback_int(call.data, "adm_city_confirm_del_")
    if city_id is None:
        await call.answer("Город не найден.", show_alert=True)
        return

    city = await get_city_by_id(session, city_id)
    city_name = city.name if city else "?"
    success = await delete_city(session, city_id)
    if success:
        await call.answer(f"Город «{city_name}» удалён.", show_alert=False)
    else:
        await call.answer("Город не найден.", show_alert=True)

    await show_cities_screen(call, session, state, page=0)
