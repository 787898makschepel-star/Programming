import asyncio
import os
import random
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from database.models import User, ProductType, Order, OrderStatus, ShowcaseProduct
from database.crud import (
    get_main_categories,
    get_subcategories,
    get_category_by_id,
    get_products_by_category,
    get_product_by_id,
    get_product_stock,
    buy_product_atomic,
    apply_referral_reward,
    get_user_by_tg_id,
    get_showcase_products,
    get_showcase_product
)
from keyboards.inline_client import (
    get_districts_kb,
    get_categories_kb,
    get_products_kb,
    get_product_card_kb,
    get_back_to_menu_kb,
    get_topup_methods_kb,
    get_candies_assortment_kb,
    get_candy_card_kb,
    get_candy_by_idx,
    CANDY_ITEMS,
    CITY_DISTRICTS,
    CITY_CODES
)
from utils.ui_cleaner import send_or_edit_screen
from utils.formatters import format_product_card, format_purchase_success, DIVIDER

router = Router(name="client_catalog")

BANNER_PATH = "assets/main_banner.jpg"


def get_main_banner() -> FSInputFile | None:
    """Возвращает баннер с тюленем."""
    if os.path.exists(BANNER_PATH):
        return FSInputFile(BANNER_PATH)
    return None


def get_candy_photo(candy_idx: int) -> FSInputFile | None:
    """Возвращает индивидуальное фото конфеты или основной баннер."""
    candy = get_candy_by_idx(candy_idx)
    img_path = candy.get("image")
    if img_path and os.path.exists(img_path):
        return FSInputFile(img_path)
    return get_main_banner()


def get_showcase_photo(product: ShowcaseProduct) -> str | FSInputFile | None:
    return product.image_file_id or get_main_banner()


def get_start_quantity_for_unit(unit: str) -> float:
    """Главное правило: все карточки в граммах стартуют с 0.5 г, все штуки — с 3 шт."""
    return 0.5 if unit == "г" else 3.0


def get_minimum_quantity(product: ShowcaseProduct) -> float:
    """Возвращает сохранённый минимум заказа с безопасным fallback для старых записей."""
    minimum = float(product.start_quantity or 0)
    if product.unit == "г":
        return max(0.5, minimum)
    return max(3.0, minimum)


def calculate_showcase_total(base_price: float, base_quantity: float, quantity: float, unit: str) -> float:
    """Рассчитывает стоимость витринного товара по правилам веса или упаковки."""
    if base_price < 0 or base_quantity <= 0 or quantity <= 0:
        raise ValueError("Цена и количество должны быть положительными")

    if unit == "г":
        if quantity % 0.5 != 0:
            raise ValueError("Количество в граммах должно быть кратно 0.5")
        return round((base_price / base_quantity) * quantity, 2)

    minimum_quantity = 3
    if quantity < minimum_quantity or quantity != int(quantity):
        raise ValueError("Минимальное количество товара — 3 шт.")
    return round(base_price + ((quantity - minimum_quantity) * (base_price / minimum_quantity)), 2)


def build_waiting_for_coordinates_text(order_code: int, candy_name: str, qty_text: str, total_price: float, district: str) -> str:
    """Красивое сообщение после оплаты с ожиданием координат выдачи."""
    return (
        f"✅ <b>Заказ #{order_code} оформлен</b>\n"
        f"{DIVIDER}\n"
        f"🍬 Товар: <b>{candy_name}</b> ({qty_text})\n"
        f"📍 Район: <b>{district}</b>\n"
        f"💵 Сумма: <code>{total_price:g} ₽</code>\n"
        f"{DIVIDER}\n"
        f"⏳ <b>Пожалуйста, подождите.</b>\n"
        f"В течение нескольких минут мы пришлём вам координаты точки выдачи.\n"
        f"Не закрывайте чат — уведомление придёт автоматически."
    )


def get_support_url() -> str:
    support = config.SUPPORT_USERNAME.strip()
    if support.startswith("@"):
        return f"https://t.me/{support[1:]}"
    return support


def build_order_followup_text(order_code: int) -> str:
    """Сообщение, если координаты не были отправлены вовремя."""
    return (
        f"⚠️ <b>Извините, что-то пошло не так.</b>\n\n"
        f"Пожалуйста, пришлите оператору код заказа: <code>#{order_code}</code>"
    )


async def send_order_followup(bot: Bot, chat_id: int, order_code: int) -> None:
    """Отправляет клиенту напоминание через 15 минут после оформления."""
    await asyncio.sleep(15 * 60)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛟 Написать оператору", url=get_support_url())]
    ])
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=build_order_followup_text(order_code),
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except Exception:
        return


def build_admin_order_notification(order_code: int, user: User, candy_name: str, qty_text: str, city: str, district: str, total_price: float) -> str:
    """Уведомление в админ-группу о новом заказе."""
    username = f"@{user.username}" if user.username else f"TG:{user.tg_id}"
    city_name = city or "—"
    return (
        f"✅ <b>Заказ #{order_code}</b> оформлен\n"
        f"{DIVIDER}\n"
        f"👤 <b>Клиент:</b> {username}\n"
        f"🍬 <b>Товар:</b> {candy_name} ({qty_text})\n"
        f"🏙️ <b>Город:</b> {city_name}\n"
        f"📍 <b>Район:</b> {district}\n"
        f"💵 <b>Сумма:</b> <code>{total_price:g} ₽</code>\n"
        f"{DIVIDER}\n"
        f"⏳ <b>Пожалуйста, подождите.</b>\n"
        f"В течение нескольких минут мы пришлём вам координаты точки выдачи."
    )


# ==========================================
# ЭКРАН РАЙОНОВ ГОРОДА (ТОЧНО КАК НА СКРИНШОТЕ)
# ==========================================

@router.callback_query(F.data == "client_catalog")
async def show_catalog_districts(call: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext):
    """
    Экран районов города точь-в-точь со скриншота:
    - Тот же баннер с тюленем на месте.
    - Подпись: '🌊 Каталог • Москва'
    - Кнопки районов: Центральный, Северный, ..., ⚡️ Назад
    """
    await state.clear()
    city = getattr(db_user, "city", "") or ""
    if city not in CITY_DISTRICTS:
        await send_or_edit_screen(
            event=call,
            text=(
                "📍 <b>Сначала выберите город</b>\n"
                f"{DIVIDER}\n"
                "Для просмотра каталога и оформления заказа укажите город."
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📍 Выбрать город", callback_data="client_city")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="to_main_menu")]
            ]),
            photo=get_main_banner(),
            state=state
        )
        await call.answer()
        return
    caption = f"🌊 Каталог • {city}"
    banner = get_main_banner()

    await send_or_edit_screen(
        event=call,
        text=caption,
        reply_markup=get_districts_kb(city),
        photo=banner,
        state=state
    )
    await call.answer()


# ==========================================
# ВХОД В ВЫБРАННЫЙ РАЙОН -> АССОРТИМЕНТ ИЗ 16 ПОЗИЦИЙ
# ==========================================

@router.callback_query(F.data.startswith("dist_"))
async def open_district_catalog(call: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext):
    """
    Вход в район: отображение экрана с 16 позициями ассортимента конфет со скриншота
    и кнопкой '⚡️ Назад'.
    """
    parts = call.data.split("_")
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
        await call.answer("Не удалось определить район. Откройте каталог заново.", show_alert=True)
        return

    city = getattr(db_user, "city", "") or ""
    city_code = int(parts[1])
    district_index = int(parts[2])
    if city not in CITY_DISTRICTS or CITY_CODES.get(city) != city_code:
        await call.answer("Этот район недоступен для выбранного города.", show_alert=True)
        return
    districts = CITY_DISTRICTS[city]
    if district_index >= len(districts):
        await call.answer("Этот район недоступен для выбранного города.", show_alert=True)
        return
    district = districts[district_index]

    db_user.district = district
    await session.commit()
    await session.refresh(db_user)
    await state.update_data(current_district=district)

    banner = get_main_banner()
    caption = f"🌊 Каталог • {city} • {district}"

    await send_or_edit_screen(
        event=call,
        text=caption,
        reply_markup=get_candies_assortment_kb(await get_showcase_products(session)),
        photo=banner,
        state=state
    )
    await call.answer()


@router.callback_query(F.data == "back_to_assortment")
async def back_to_candies_assortment(call: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext):
    """Возврат назад к списку из 16 позиций конфет."""
    data = await state.get_data()
    district = data.get("current_district", "Центральный")
    city = getattr(db_user, "city", "Москва") or "Москва"
    banner = get_main_banner()
    caption = f"🌊 Каталог • {city} • {district}"

    await send_or_edit_screen(
        event=call,
        text=caption,
        reply_markup=get_candies_assortment_kb(await get_showcase_products(session)),
        photo=banner,
        state=state
    )
    await call.answer()


@router.callback_query(F.data.startswith("candy_plus_"))
async def cb_candy_plus(call: CallbackQuery, session: AsyncSession):
    """Увеличение количества товара по единице/половине грамма в зависимости от типа товара."""
    parts = call.data.split("_")
    candy_idx = int(parts[2])
    candy = await get_showcase_product(session, candy_idx)
    if not candy:
        await call.answer("Товар больше недоступен.", show_alert=True)
        return

    qty = float(parts[3])
    step = 0.5 if candy.unit == "г" else 1.0
    new_qty = min(qty + step, 50.0)
    price_per_piece = candy.price
    kb = get_candy_card_kb(candy_idx, qty=new_qty, price_per_piece=price_per_piece, unit=candy.unit, base_quantity=get_minimum_quantity(candy))

    try:
        await call.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass
    await call.answer()


@router.callback_query(F.data.startswith("candy_qty_") | F.data.startswith("candy_minus_"))
async def cb_candy_qty(call: CallbackQuery, session: AsyncSession):
    """Уменьшает количество на 1 шт. или 0.5 г, но не ниже минимума."""
    parts = call.data.split("_")
    candy_idx = int(parts[2])
    candy = await get_showcase_product(session, candy_idx)
    if not candy:
        await call.answer("Товар больше недоступен.", show_alert=True)
        return

    qty = float(parts[3])
    step = 0.5 if candy.unit == "г" else 1.0
    minimum = get_minimum_quantity(candy)

    if qty - step >= minimum:
        new_qty = round(qty - step, 2)
        price_per_piece = candy.price
        kb = get_candy_card_kb(candy_idx, qty=new_qty, price_per_piece=price_per_piece, unit=candy.unit, base_quantity=get_minimum_quantity(candy))
        try:
            await call.message.edit_reply_markup(reply_markup=kb)
        except Exception:
            pass
        await call.answer()
    else:
        message = "Минимальное количество для заказа — 0.5 г." if candy.unit == "г" else "Минимальное количество для заказа — 3 шт."
        await call.answer(message, show_alert=False)


@router.callback_query(F.data.startswith("candy_stock_"))
async def cb_candy_stock(call: CallbackQuery, session: AsyncSession):
    """
    Имитация проверки наличия на складе с обратным отсчетом.
    """
    candy_idx = int(call.data.replace("candy_stock_", ""))
    candy = await get_showcase_product(session, candy_idx)
    if not candy:
        await call.answer("Товар больше недоступен.", show_alert=True)
        return
    duration = random.randint(20, 30)
    progress_message = await call.message.answer(
        f"🔎 <b>Проверяем наличие на складе</b>\n"
        f"{DIVIDER}\n"
        f"Товар: <b>{candy.title}</b>\n"
        f"⏳ Поиск позиции... осталось примерно <b>{duration} сек.</b>"
    )
    await call.answer("Проверяем наличие на складе...")

    for remaining in range(duration - 1, -1, -1):
        await asyncio.sleep(1)
        if remaining and remaining % 5 != 0:
            continue
        try:
            await progress_message.edit_text(
                f"🔎 <b>Проверяем наличие на складе</b>\n"
                f"{DIVIDER}\n"
                f"Товар: <b>{candy.title}</b>\n"
                f"⏳ Поиск позиции... осталось примерно <b>{remaining} сек.</b>"
            )
        except Exception:
            return

    result_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Перейти к оформлению", callback_data=f"candy_{candy_idx}")]
    ])
    await progress_message.edit_text(
        f"✅ <b>Товар найден на складе</b>\n"
        f"{DIVIDER}\n"
        f"Позиция: <b>{candy.title}</b>\n"
        f"📦 Статус: <b>в наличии</b>\n"
        f"⚡️ Доступна моментальная выдача после оплаты.",
        reply_markup=result_keyboard
    )


@router.callback_query(F.data.regexp(r"^candy_\d+$"))
async def open_candy_detail(call: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext):
    """
    Карточка выбранной конфеты из ассортимента точь-в-точь по скриншоту пользователя:
    - Фото позиции
    - Подпись: 🌊 Каталог • Москва • Западный • {candy_name}
    - Кнопки:
      [ 1шт ]  [ + ]
      [ ❓ Проверить наличие ]
      [ ⚡️ Назад ]  [ 🛒 Купить {цена за 1 шт}₽ ]
    """
    candy_idx = int(call.data.replace("candy_", ""))
    candy = await get_showcase_product(session, candy_idx)
    if not candy or not candy.is_active:
        await call.answer("Товар больше недоступен.", show_alert=True)
        return
    candy_name = candy.title
    price = candy.price

    initial_qty = get_minimum_quantity(candy)

    data = await state.get_data()
    district = data.get("current_district", "Западный")
    city = getattr(db_user, "city", "Москва") or "Москва"

    caption = f"🌊 Каталог • {city} • {district} • {candy_name}"
    photo = get_showcase_photo(candy)

    await send_or_edit_screen(
        event=call,
        text=caption,
        reply_markup=get_candy_card_kb(candy_idx, qty=initial_qty, price_per_piece=price, unit=candy.unit, base_quantity=get_minimum_quantity(candy)),
        photo=photo,
        state=state
    )
    await call.answer()


@router.callback_query(F.data.startswith("buy_candy_"))
async def process_buy_candy(call: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext, bot: Bot):
    """Оформление покупки конфет с баланса с учетом выбранного количества."""
    parts = call.data.split("_")
    candy_idx = int(parts[2])

    candy = await get_showcase_product(session, candy_idx)
    if not candy or not candy.is_active:
        await call.answer("Товар больше недоступен.", show_alert=True)
        return

    qty = float(parts[3]) if len(parts) > 3 else get_minimum_quantity(candy)
    candy_name = candy.title
    base_quantity = get_minimum_quantity(candy)
    try:
        total_price = calculate_showcase_total(candy.price, base_quantity, qty, candy.unit)
    except ValueError as error:
        await call.answer(str(error), show_alert=True)
        return

    data = await state.get_data()
    district = data.get("current_district", "Западный")

    if db_user.balance < total_price:
        needed = round(total_price - db_user.balance, 2)
        qty_text = f"{float(qty):g} г" if candy.unit == "г" else f"{int(qty)} шт."
        text = (
            f"❌ <b>Недостаточно средств на балансе</b>\n"
            f"{DIVIDER}\n"
            f"🍬 Товар: <b>{candy_name}</b> ({qty_text})\n"
            f"💵 Стоимость: <code>{total_price:g} ₽</code>\n"
            f"💰 Ваш баланс: <code>{db_user.balance:g} ₽</code>\n"
            f"Не хватает: <b>{needed:g} ₽</b>\n"
            f"{DIVIDER}\n"
            f"Пополните баланс в разделе профиля или активируйте промокод #WILLIWONKA:"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="client_profile")],
            [InlineKeyboardButton(text="🎁 Ввести промокод", callback_data="client_promo")],
            [InlineKeyboardButton(text="⚡️ Назад", callback_data=f"candy_{candy_idx}")]
        ])
        photo = get_showcase_photo(candy)
        await send_or_edit_screen(call, text, reply_markup=kb, photo=photo, state=state)
        await call.answer()
        return

    # Списание с баланса
    db_user.balance -= total_price
    await session.commit()

    import random
    qty_text = f"{float(qty):g} г" if candy.unit == "г" else f"{int(qty)} шт."
    order = Order(
        user_id=db_user.id,
        product_id=None,
        amount=total_price,
        payment_method="balance",
        status=OrderStatus.COMPLETED,
        delivered_data=f"{candy_name} ({qty_text})"
    )
    session.add(order)
    await session.flush()
    await apply_referral_reward(session, order)
    await session.commit()
    order_id = order.id
    order_code = random.randint(100000, 999999)
    pickup_code = f"WAVE-{order_id}-{random.randint(10, 99)}"

    text = build_waiting_for_coordinates_text(order_code, candy_name, qty_text, total_price, district)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡️ Назад в ассортимент", callback_data="back_to_assortment")],
        [InlineKeyboardButton(text="🌊 Главное меню", callback_data="to_main_menu")]
    ])
    photo = get_showcase_photo(candy)

    short_status = (
        "✅ Заказ оформлен\n\n"
        "⏳ Пожалуйста, подождите\n\n"
        "В течение нескольких минут мы пришлём вам координаты точки выдачи"
    )

    admin_text = build_admin_order_notification(order_code, db_user, candy_name, qty_text, db_user.city or "—", district, total_price)
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить сообщение", callback_data=f"adm_delete_order_{order_code}")]
    ])
    try:
        await bot.send_message(
            chat_id=config.RECEIPTS_GROUP_ID,
            text=admin_text,
            reply_markup=admin_kb,
            parse_mode="HTML"
        )
    except Exception:
        pass

    await send_or_edit_screen(call, text, reply_markup=kb, photo=photo, state=state)
    await call.message.answer(short_status)
    asyncio.create_task(send_order_followup(bot, db_user.tg_id, order_code))
    await call.answer("Заказ оформлен.", show_alert=False)


# ==========================================
# КАТЕГОРИИ И ПОДКАТЕГОРИИ
# ==========================================

@router.callback_query(F.data.startswith("adm_delete_order_"))
async def admin_delete_order_message(call: CallbackQuery, session: AsyncSession):
    """Удаляет сообщение в админ-группе о новом заказе."""
    db_user = await get_user_by_tg_id(session, call.from_user.id)
    if call.from_user.id not in config.ADMIN_IDS and not (db_user and db_user.is_admin):
        await call.answer("⛔️ Нет прав.", show_alert=True)
        return

    try:
        await call.message.delete()
    except Exception:
        pass
    await call.answer("Сообщение удалено.", show_alert=False)


@router.callback_query(F.data.startswith("cat_"))
async def open_category(call: CallbackQuery, session: AsyncSession, db_user: User, state: FSMContext):
    """Вход в категорию (товары)."""
    cat_id = int(call.data.split("_")[1])
    category = await get_category_by_id(session, cat_id)

    if not category:
        await call.answer("Категория не найдена.", show_alert=True)
        return

    subcategories = await get_subcategories(session, cat_id)
    banner = get_main_banner()

    if subcategories:
        caption = (
            f"📁 <b>{category.name}</b>\n"
            f"{DIVIDER}\n"
            f"Выберите подкатегорию:"
        )
        await send_or_edit_screen(
            call,
            caption,
            reply_markup=get_categories_kb(subcategories, parent_id=category.parent_id),
            photo=banner,
            state=state
        )
        await call.answer()
        return

    products = await get_products_by_category(session, cat_id)
    if not products:
        caption = (
            f"📁 <b>{category.name}</b>\n"
            f"{DIVIDER}\n"
            f"В данной категории пока нет активных позиций."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡️ Назад к районам", callback_data="client_catalog")]
        ])
        await send_or_edit_screen(call, caption, reply_markup=kb, photo=banner, state=state)
        await call.answer()
        return

    caption = (
        f"📁 <b>{category.name}</b>\n"
        f"{DIVIDER}\n"
        f"Доступные товары:"
    )
    await send_or_edit_screen(
        call,
        caption,
        reply_markup=get_products_kb(products, cat_id),
        photo=banner,
        state=state
    )
    await call.answer()


# ==========================================
# КАРТОЧКА ТОВАРА
# ==========================================

@router.callback_query(F.data.startswith("prod_"))
async def show_product_card(call: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Карточка товара с остатком в реальном времени."""
    prod_id = int(call.data.split("_")[1])
    product = await get_product_by_id(session, prod_id)

    if not product:
        await call.answer("Товар не найден.", show_alert=True)
        return

    stock = await get_product_stock(session, product.id) if product.product_type == ProductType.DIGITAL_ITEM else 1
    has_stock = stock > 0
    banner = get_main_banner()

    text = format_product_card(product, stock)
    await send_or_edit_screen(
        call,
        text,
        reply_markup=get_product_card_kb(product.id, product.category_id, has_stock),
        photo=banner,
        state=state
    )
    await call.answer()


# ==========================================
# ПОКУПКА ТОВАРА
# ==========================================

@router.callback_query(F.data.startswith("buy_"))
async def process_buy_product(call: CallbackQuery, session: AsyncSession, db_user: User, bot: Bot, state: FSMContext):
    """Обработка покупки товара с баланса."""
    prod_id = int(call.data.split("_")[1])
    product = await get_product_by_id(session, prod_id)

    if not product:
        await call.answer("Товар не найден.", show_alert=True)
        return

    # Проверка баланса
    if db_user.balance < product.price:
        needed = round(product.price - db_user.balance, 2)
        text = (
            f"❌ <b>Недостаточно средств на балансе</b>\n"
            f"{DIVIDER}\n"
            f"💵 Стоимость: <code>{product.price:g} ₽</code>\n"
            f"💰 Ваш баланс: <code>{db_user.balance:g} ₽</code>\n"
            f"Не хватает: <b>{needed:g} ₽</b>\n"
            f"{DIVIDER}\n"
            f"Выберите способ моментального пополнения баланса:"
        )
        banner = get_main_banner()
        await send_or_edit_screen(call, text, reply_markup=get_topup_methods_kb(needed), photo=banner, state=state)
        await call.answer()
        return

    # Атомарная покупка
    order, delivered = await buy_product_atomic(session, db_user, product, payment_method="balance")

    if not order:
        await call.answer(delivered or "Ошибка покупки товара.", show_alert=True)
        return

    success_text = format_purchase_success(order, product, delivered, db_user.balance)
    banner = get_main_banner()

    if product.product_type == ProductType.FILE and product.file_id:
        await send_or_edit_screen(call, success_text, reply_markup=get_back_to_menu_kb(), photo=banner, state=state)
        await bot.send_document(
            chat_id=call.from_user.id,
            document=product.file_id,
            caption=f"📦 Файл к заказу #{order.id}"
        )
    else:
        await send_or_edit_screen(call, success_text, reply_markup=get_back_to_menu_kb(), photo=banner, state=state)

    asyncio.create_task(send_order_followup(bot, db_user.tg_id, order.id))
    await call.answer("Покупка успешно совершена!", show_alert=False)


@router.callback_query(F.data == "out_of_stock")
async def cb_out_of_stock(call: CallbackQuery):
    """Оповещение об отсутствии остатка."""
    await call.answer("⚠️ Данная позиция временно отсутствует на складе.", show_alert=True)
