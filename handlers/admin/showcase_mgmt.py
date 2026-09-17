from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import (
    create_showcase_product,
    delete_showcase_product,
    get_showcase_product,
    get_showcase_products,
    update_showcase_product,
)
from keyboards.inline_admin import (
    get_showcase_admin_kb,
    get_showcase_delete_confirm_kb,
    get_showcase_unit_kb,
)
from states.admin_states import ShowcaseProductState
from utils.formatters import DIVIDER
from utils.ui_cleaner import delete_user_message, send_or_edit_screen

router = Router(name="admin_showcase_mgmt")


async def show_showcase_screen(call_or_message, session: AsyncSession, state: FSMContext, bot=None):
    products = await get_showcase_products(session)
    text = (
        "🛍️ <b>Товары клиентского каталога</b>\n"
        f"{DIVIDER}\n"
        "Здесь администратор добавляет и удаляет товары,\n"
        "которые видит пользователь после выбора района."
    )
    await send_or_edit_screen(
        call_or_message,
        text,
        reply_markup=get_showcase_admin_kb(products),
        state=state,
        bot=bot,
    )


@router.callback_query(F.data == "adm_showcase")
async def open_showcase(call: CallbackQuery, session: AsyncSession, state: FSMContext):
    await state.clear()
    await show_showcase_screen(call, session, state)
    await call.answer()


@router.callback_query(F.data == "adm_showcase_add")
async def start_add_showcase(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(ShowcaseProductState.waiting_for_title)
    await send_or_edit_screen(
        call,
        "➕ <b>Добавление товара</b>\n"
        f"{DIVIDER}\n"
        "Шаг 1 из 4. Введите название товара:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="adm_showcase")]
        ]),
        state=state,
    )
    await call.answer()


@router.callback_query(F.data.startswith("adm_showcase_edit_"))
async def start_edit_showcase(call: CallbackQuery, session: AsyncSession, state: FSMContext):
    product_id = int(call.data.rsplit("_", 1)[1])
    product = await get_showcase_product(session, product_id)
    if not product:
        await call.answer("Товар не найден.", show_alert=True)
        return

    await state.clear()
    await state.set_state(ShowcaseProductState.waiting_for_title)
    await state.update_data(
        editing_product_id=product_id,
        title=product.title,
        price=product.price,
        image_file_id=product.image_file_id,
        unit=product.unit,
        start_quantity=product.start_quantity,
    )
    await send_or_edit_screen(
        call,
        "✏️ <b>Редактирование карточки товара</b>\n"
        f"{DIVIDER}\n"
        f"Текущий товар: <b>{product.title}</b>\n"
        f"💵 Цена: <b>{product.price:g} ₽</b>\n"
        f"⚖️ Ед. изм.: <b>{product.unit}</b>\n"
        f"🔢 Минимальный заказ: <b>{product.start_quantity:g} {product.unit}</b>\n\n"
        "Шаг 1 из 5. Введите новое название товара:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="adm_showcase")]
        ]),
        state=state,
    )
    await call.answer()


@router.message(ShowcaseProductState.waiting_for_title)
async def add_showcase_title(message: Message, state: FSMContext, bot):
    title = (message.text or "").strip()
    await delete_user_message(message)
    if not title or len(title) > 255:
        await send_or_edit_screen(message, "⚠️ Введите название от 1 до 255 символов.", state=state, bot=bot)
        return
    await state.update_data(title=title)
    await state.set_state(ShowcaseProductState.waiting_for_price)
    await send_or_edit_screen(message, "💵 <b>Шаг 2 из 5.</b> Введите цену минимального заказа:", state=state, bot=bot)


@router.message(ShowcaseProductState.waiting_for_price)
async def add_showcase_price(message: Message, state: FSMContext, bot):
    raw = (message.text or "").strip().replace(",", ".")
    await delete_user_message(message)
    try:
        price = float(raw)
        if price <= 0:
            raise ValueError
    except ValueError:
        await send_or_edit_screen(message, "⚠️ Цена должна быть положительным числом.", state=state, bot=bot)
        return
    await state.update_data(price=price)
    await state.set_state(ShowcaseProductState.waiting_for_image)
    await send_or_edit_screen(
        message,
        "🖼️ <b>Шаг 3 из 5.</b> Отправьте фотокарточку товара:",
        state=state,
        bot=bot,
    )


@router.message(ShowcaseProductState.waiting_for_image, F.photo)
async def add_showcase_image(message: Message, state: FSMContext, session: AsyncSession, bot):
    await state.update_data(image_file_id=message.photo[-1].file_id)
    await delete_user_message(message)
    await state.set_state(ShowcaseProductState.waiting_for_unit)
    await send_or_edit_screen(
        message,
        "⚖️ <b>Шаг 4 из 5.</b> Выберите единицу цены:\n"
        "Укажите, за какую единицу указана введённая стоимость:",
        reply_markup=get_showcase_unit_kb(),
        state=state,
        bot=bot,
    )


@router.callback_query(ShowcaseProductState.waiting_for_unit, F.data.startswith("showcase_unit_"))
async def add_showcase_unit(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    unit = "г" if call.data == "showcase_unit_g" else "шт."
    await state.update_data(unit=unit)
    await state.set_state(ShowcaseProductState.waiting_for_quantity)
    quantity_label = "грамм" if unit == "г" else "штук"
    await send_or_edit_screen(
        call,
        f"🔢 <b>Минимальное количество заказа</b>\n{DIVIDER}\n"
        f"Введите минимальное количество в {quantity_label}:\n"
        f"Например: <code>{'0.5' if unit == 'г' else '3'}</code>",
        state=state,
    )
    await call.answer(f"Выбрано: {unit}")


@router.message(ShowcaseProductState.waiting_for_quantity)
async def add_showcase_quantity(message: Message, state: FSMContext, session: AsyncSession, bot):
    data = await state.get_data()
    raw = (message.text or "").strip().replace(",", ".")
    await delete_user_message(message)
    try:
        quantity = float(raw)
    except ValueError:
        quantity_label = "грамм, кратное 0.5" if data.get("unit") == "г" else "целое количество штук, минимум 3"
        example = "0.5" if data.get("unit") == "г" else "3"
        await send_or_edit_screen(
            message,
            f"⚠️ Введите корректное минимальное количество ({quantity_label}), например: <code>{example}</code>.",
            state=state,
            bot=bot,
        )
        return

    if data.get("unit") == "г":
        if not (0.5 <= quantity <= 500) or quantity % 0.5 != 0:
            await send_or_edit_screen(
                message,
                "⚠️ Для граммов введите значение от <b>0.5</b> до <b>500</b> грамм с шагом <b>0.5</b>.",
                state=state,
                bot=bot,
            )
            return
    else:
        if quantity < 3 or not quantity.is_integer():
            await send_or_edit_screen(
                message,
                "⚠️ Для штук минимальный заказ — целое число не менее <b>3</b>.",
                state=state,
                bot=bot,
            )
            return

    editing_product_id = data.get("editing_product_id")
    if editing_product_id:
        product = await update_showcase_product(
            session=session,
            product_id=editing_product_id,
            title=data["title"],
            price=data["price"],
            image_file_id=data["image_file_id"],
            unit=data["unit"],
            start_quantity=quantity,
        )
        success_title = "✅ <b>Товар обновлён</b>"
    else:
        product = await create_showcase_product(
            session=session,
            title=data["title"],
            price=data["price"],
            image_file_id=data["image_file_id"],
            unit=data["unit"],
            start_quantity=quantity,
        )
        success_title = "✅ <b>Товар добавлен</b>"

    await state.clear()
    quantity_text = f"{quantity:.1f}" if product.unit == "г" else f"{int(quantity)}"
    await send_or_edit_screen(
        message,
        f"{success_title}\n{DIVIDER}\n"
        f"🏷 {product.title}\n"
        f"💵 {product.price:g} ₽\n"
        f"🔢 Минимальный заказ: <b>{quantity_text} {product.unit}</b>\n"
        "🖼️ Фотокарточка сохранена.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить товар ещё", callback_data="adm_showcase_add")],
            [InlineKeyboardButton(text="✏️ Изменить", callback_data=f"adm_showcase_edit_{product.id}")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="adm_main")]
        ]),
        state=state,
        bot=bot,
    )


@router.message(ShowcaseProductState.waiting_for_image)
async def add_showcase_image_required(message: Message, state: FSMContext, bot):
    await delete_user_message(message)
    await send_or_edit_screen(message, "⚠️ Отправьте именно фотокарточку товара.", state=state, bot=bot)


@router.callback_query(F.data.startswith("adm_showcase_del_"))
async def ask_delete_showcase(call: CallbackQuery, session: AsyncSession, state: FSMContext):
    product_id = int(call.data.rsplit("_", 1)[1])
    product = await get_showcase_product(session, product_id)
    if not product:
        await call.answer("Товар не найден.", show_alert=True)
        return
    await send_or_edit_screen(
        call,
        f"⚠️ <b>Удалить товар?</b>\n{DIVIDER}\n🏷 {product.title}\n💵 {product.price:g} ₽",
        reply_markup=get_showcase_delete_confirm_kb(product_id),
        state=state,
    )
    await call.answer()


@router.callback_query(F.data.startswith("adm_showcase_confirm_del_"))
async def confirm_delete_showcase(call: CallbackQuery, session: AsyncSession, state: FSMContext):
    product_id = int(call.data.rsplit("_", 1)[1])
    deleted = await delete_showcase_product(session, product_id)
    await call.answer("Товар удалён." if deleted else "Товар уже удалён.", show_alert=True)
    await show_showcase_screen(call, session, state)


@router.callback_query(F.data == "adm_showcase_info")
async def showcase_info(call: CallbackQuery):
    await call.answer("Для удаления используйте кнопку 🗑 рядом с товаром.", show_alert=True)
