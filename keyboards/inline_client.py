from typing import List, Optional, Dict
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models import Category, Product, Order, User
from config import config

CITY_DISTRICTS: Dict[str, List[str]] = {
    "Москва": [
        "Центральный",
        "Северный",
        "Северо-Восточный",
        "Восточный",
        "Юго-Восточный",
        "Южный",
        "Юго-Западный",
        "Западный",
        "Северо-Западный",
        "Зеленоградский",
        "Новомосковский",
        "Троицкий",
    ],
    "Санкт-Петербург": [
        "Центральный",
        "Адмиралтейский",
        "Василеостровский",
        "Петроградский",
        "Приморский",
        "Московский",
        "Калининский",
        "Невский",
        "Выборгский",
    ],
    "Волгоград": ["Центральный", "Ворошиловский", "Дзержинский", "Кировский", "Красноармейский", "Краснооктябрьский", "Советский", "Тракторозаводский"],
    "Пермь": ["Дзержинский", "Индустриальный", "Кировский", "Ленинский", "Мотовилихинский", "Орджоникидзевский", "Свердловский"],
    "Воронеж": ["Железнодорожный", "Коминтерновский", "Левобережный", "Ленинский", "Советский", "Центральный"],
    "Омск": ["Кировский", "Ленинский", "Октябрьский", "Советский", "Центральный"],
    "Ростов-на-Дону": ["Ворошиловский", "Железнодорожный", "Кировский", "Ленинский", "Октябрьский", "Первомайский", "Пролетарский", "Советский"],
    "Самара": ["Железнодорожный", "Кировский", "Красноглинский", "Куйбышевский", "Ленинский", "Октябрьский", "Промышленный", "Самарский", "Советский"],
    "Краснодар": ["Западный", "Карасунский", "Прикубанский", "Центральный"],
    "Уфа": ["Демский", "Калининский", "Кировский", "Ленинский", "Октябрьский", "Орджоникидзевский", "Советский"],
    "Челябинск": ["Калининский", "Курчатовский", "Ленинский", "Металлургический", "Советский", "Тракторозаводский", "Центральный"],
    "Нижний Новгород": ["Автозаводский", "Канавинский", "Ленинский", "Московский", "Нижегородский", "Приокский", "Советский", "Сормовский"],
    "Красноярск": ["Железнодорожный", "Кировский", "Ленинский", "Октябрьский", "Свердловский", "Советский", "Центральный"],
    "Казань": ["Авиастроительный", "Вахитовский", "Кировский", "Московский", "Ново-Савиновский", "Приволжский", "Советский"],
    "Екатеринбург": ["Академический", "Верх-Исетский", "Железнодорожный", "Кировский", "Ленинский", "Октябрьский", "Орджоникидзевский", "Чкаловский"],
    "Новосибирск": ["Дзержинский", "Железнодорожный", "Заельцовский", "Калининский", "Кировский", "Ленинский", "Октябрьский", "Первомайский", "Советский", "Центральный"],
}

CITY_CODES = {city: index for index, city in enumerate(CITY_DISTRICTS)}


def get_bottom_reply_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Нижняя постоянная панель с дополнительной кнопкой админ-команды."""
    keyboard = [[KeyboardButton(text="🌊 Главное меню")]]
    if is_admin:
        keyboard.append([KeyboardButton(text="/admin")])
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True
    )


def get_main_menu_kb(user: Optional[User] = None) -> InlineKeyboardMarkup:
    """Точная копия кнопок главного меню METH WAVE со скриншота."""
    builder = InlineKeyboardBuilder()

    balance_val = 0
    city = "Не выбран"
    if user:
        city = getattr(user, "city", "") or "Не выбран"
        b = user.balance
        balance_val = int(b) if b.is_integer() else round(b, 2)

    # 1. 🌊 Каталог
    builder.row(InlineKeyboardButton(text="🌊 Каталог", callback_data="client_catalog"))
    # 2. 💰 Баланс (0₽)
    builder.row(InlineKeyboardButton(text=f"💰 Баланс ({balance_val}₽)", callback_data="client_profile"))
    # 3. 🛒 Мои покупки
    builder.row(InlineKeyboardButton(text="🛒 Мои покупки", callback_data="profile_orders"))
    # 4. 💦 Город (Москва)
    builder.row(InlineKeyboardButton(text=f"💦 Город ({city})", callback_data="client_city"))
    # 5. 🎁 Промокод
    builder.row(InlineKeyboardButton(text="🎁 Промокод", callback_data="client_promo"))
    # 6. 🤝 Пригласи друга
    builder.row(InlineKeyboardButton(text="🤝 Пригласи друга", callback_data="client_ref"))

    reviews_url = f"https://t.me/{config.REVIEWS_CHANNEL.lstrip('@')}" if config.REVIEWS_CHANNEL.startswith("@") else config.REVIEWS_CHANNEL
    support_url = f"https://t.me/{config.SUPPORT_USERNAME.lstrip('@')}" if config.SUPPORT_USERNAME.startswith("@") else config.SUPPORT_USERNAME

    # 7. 💠 Отзывы ↗
    builder.row(InlineKeyboardButton(text="💠 Отзывы ↗", url=reviews_url))
    # 8. 🛟 Тех. Поддержка ↗
    builder.row(InlineKeyboardButton(text="🛟 Тех. Поддержка ↗", url=support_url))

    return builder.as_markup()


def get_city_select_kb() -> InlineKeyboardMarkup:
    """Список городов, доступных для оформления заказа."""
    builder = InlineKeyboardBuilder()
    for city in CITY_DISTRICTS:
        builder.button(text=f"📍 {city}", callback_data=f"set_city_{city}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="⚡️ Назад", callback_data="to_main_menu"))
    return builder.as_markup()


def get_districts_kb(city: str = "") -> InlineKeyboardMarkup:
    """
    Точная копия экрана районов со скриншота пользователя:
    💦 Центральный
    💦 Северный
    ...
    ⚡️ Назад
    """
    districts = CITY_DISTRICTS.get(city, [])
    city_code = CITY_CODES.get(city)
    if city_code is None:
        city_code = -1
    builder = InlineKeyboardBuilder()

    for district_index, district in enumerate(districts):
        builder.row(
            InlineKeyboardButton(
                text=f"💦 {district}",
                callback_data=f"dist_{city_code}_{district_index}"
            )
        )

    builder.row(InlineKeyboardButton(text="⚡️ Назад", callback_data="to_main_menu"))
    return builder.as_markup()


CANDY_ITEMS: List[Dict[str, any]] = [
    {"name": "Anonymous 2.0 - 310mg", "price": 1680, "image": "assets/candy_anonymous.jpg"},
    {"name": "Punisher - 300mg", "price": 1650, "image": None},
    {"name": "Red Bull - 280mg", "price": 1500, "image": None},
    {"name": "Maybach - 320mg", "price": 1700, "image": None},
    {"name": "Tesla - 300mg", "price": 1650, "image": None},
    {"name": "Chupa Chups - 270mg", "price": 1450, "image": None},
    {"name": "Burger King - 290mg", "price": 1550, "image": None},
    {"name": "Rolex - 310mg", "price": 1680, "image": None},
    {"name": "Skittles - 260mg", "price": 1400, "image": None},
    {"name": "Philipp Plein - 300mg", "price": 1650, "image": None},
    {"name": "EA7 Emporio - 280mg", "price": 1500, "image": None},
    {"name": "Gucci - 320mg", "price": 1750, "image": None},
    {"name": "Supreme - 290mg", "price": 1550, "image": None},
    {"name": "Heineken - 280mg", "price": 1500, "image": None},
    {"name": "Audi - 300mg", "price": 1600, "image": None},
    {"name": "Warner Bros - 310mg", "price": 1680, "image": None},
]


def get_candy_by_idx(candy_idx: int) -> Dict[str, any]:
    """Получение конфеты по индексу."""
    if 1 <= candy_idx <= len(CANDY_ITEMS):
        item = CANDY_ITEMS[candy_idx - 1]
        if isinstance(item, dict):
            return item
        return {"name": str(item), "price": 1680, "image": None}
    return {"name": "Конфеты высшего сорта", "price": 1680, "image": None}


def get_default_quantity_for_unit(unit: str) -> float:
    """Стартовое количество в карточке смотри по типу единицы."""
    if unit == "г":
        return 0.5
    if unit == "шт.":
        return 3.0
    return 1.0


def format_quantity_label(qty: float, unit: str) -> str:
    """Форматирует число для кнопки количества: 0.5г, 3шт, 1г."""
    if unit == "г":
        return f"{float(qty):g}г"
    return f"{int(qty)}шт"


def get_candies_assortment_kb(products=None) -> InlineKeyboardMarkup:
    """Точно 16 позиций ассортимента конфет и кнопка ⚡️ Назад."""
    builder = InlineKeyboardBuilder()
    items = products if products is not None else CANDY_ITEMS
    for idx, item in enumerate(items, start=1):
        name = getattr(item, "title", None) or (item["name"] if isinstance(item, dict) else item)
        item_id = getattr(item, "id", idx)
        builder.row(InlineKeyboardButton(text=f"💦 {name}", callback_data=f"candy_{item_id}"))
    builder.row(InlineKeyboardButton(text="⚡️ Назад", callback_data="client_catalog"))
    return builder.as_markup()


def get_candy_card_kb(candy_idx: int, qty: float = 3.0, price_per_piece: float = 1680.0, unit: str = "шт.", base_quantity: float = 0.5) -> InlineKeyboardMarkup:
    """Карточка выбранной конфеты с корректным стартовым количеством для граммов и штук."""
    builder = InlineKeyboardBuilder()
    base_quantity = base_quantity if unit == "г" else 3.0
    if unit == "г":
        total_price = round((price_per_piece / base_quantity) * qty)
    else:
        total_price = round(price_per_piece + ((qty - 3.0) * (price_per_piece / 3.0)))
    quantity_label = format_quantity_label(qty, unit)

    builder.row(
        InlineKeyboardButton(text="−", callback_data=f"candy_minus_{candy_idx}_{qty}"),
        InlineKeyboardButton(text=quantity_label, callback_data=f"candy_qty_{candy_idx}_{qty}"),
        InlineKeyboardButton(text="+", callback_data=f"candy_plus_{candy_idx}_{qty}")
    )
    builder.row(
        InlineKeyboardButton(text="✅ Проверить наличие", callback_data=f"candy_stock_{candy_idx}")
    )
    builder.row(
        InlineKeyboardButton(text="⚡️ Назад", callback_data="back_to_assortment"),
        InlineKeyboardButton(text=f"🛒 Купить {total_price}₽", callback_data=f"buy_candy_{candy_idx}_{qty}")
    )
    return builder.as_markup()


get_cities_kb = get_city_select_kb


def get_categories_kb(categories: List[Category], parent_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Сетка категорий с эргономичной навигацией."""
    builder = InlineKeyboardBuilder()

    for cat in categories:
        builder.button(text=f"📁 {cat.name}", callback_data=f"cat_{cat.id}")

    builder.adjust(2)

    if parent_id is not None:
        builder.row(InlineKeyboardButton(text="⚡️ Назад", callback_data="client_catalog"))
    else:
        builder.row(InlineKeyboardButton(text="⚡️ Назад к районам", callback_data="client_catalog"))

    return builder.as_markup()


def get_products_kb(products: List[Product], category_id: int) -> InlineKeyboardMarkup:
    """Список товаров в категории."""
    builder = InlineKeyboardBuilder()

    for prod in products:
        builder.button(text=f"🏷 {prod.title} — {prod.price:g} ₽", callback_data=f"prod_{prod.id}")

    builder.adjust(1)
    builder.row(
        InlineKeyboardButton(text="⚡️ Назад", callback_data="client_catalog"),
        InlineKeyboardButton(text="🏠 Меню", callback_data="to_main_menu")
    )
    return builder.as_markup()


def get_product_card_kb(product_id: int, category_id: int, has_stock: bool) -> InlineKeyboardMarkup:
    """Инлайн-панель карточки товара."""
    builder = InlineKeyboardBuilder()

    if has_stock:
        builder.row(InlineKeyboardButton(text="⚡️ Купить сейчас", callback_data=f"buy_{product_id}"))
    else:
        builder.row(InlineKeyboardButton(text="🔴 Нет в наличии", callback_data="out_of_stock"))

    builder.row(
        InlineKeyboardButton(text="⚡️ Назад", callback_data=f"cat_{category_id}"),
        InlineKeyboardButton(text="🏠 Меню", callback_data="to_main_menu")
    )
    return builder.as_markup()


def get_balance_methods_kb() -> InlineKeyboardMarkup:
    """Точная копия кнопок экрана пополнения баланса со скриншота пользователя."""
    builder = InlineKeyboardBuilder()
    support_url = f"https://t.me/{config.SUPPORT_USERNAME.lstrip('@')}" if config.SUPPORT_USERNAME.startswith("@") else config.SUPPORT_USERNAME

    builder.row(InlineKeyboardButton(text="👨‍💻 Через оператора [24/7]", url=support_url))
    builder.row(InlineKeyboardButton(text="💲 Криптовалюта [АВТО]", callback_data="topup_crypto_auto"))
    builder.row(InlineKeyboardButton(text="🌊 Главное меню", callback_data="to_main_menu"))
    return builder.as_markup()


def get_crypto_wallet_kb() -> InlineKeyboardMarkup:
    """Выбор сети в окне криптовалютных реквизитов."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔵 USDT TRC20", callback_data="topup_crypto_auto"))
    builder.row(InlineKeyboardButton(text="🟡 USDT BEP20", callback_data="topup_manual_usdt_bep20"))
    builder.row(InlineKeyboardButton(text="🟡 BNB BEP20", callback_data="topup_manual_bnb_bep20"))
    builder.row(InlineKeyboardButton(text="₿ Bitcoin", callback_data="topup_manual_btc"))
    builder.row(InlineKeyboardButton(text="💠 Ethereum ERC20", callback_data="topup_manual_eth"))
    builder.row(InlineKeyboardButton(text="Ł Litecoin", callback_data="topup_manual_ltc"))
    builder.row(InlineKeyboardButton(text="⚡️ Назад", callback_data="client_profile"))
    return builder.as_markup()


def get_profile_kb() -> InlineKeyboardMarkup:
    """Клавиатура личного кабинета."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="profile_topup"),
        InlineKeyboardButton(text="📦 Мои покупки", callback_data="profile_orders")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="client_profile"),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_main_menu")
    )
    return builder.as_markup()


def get_topup_methods_kb(amount: float) -> InlineKeyboardMarkup:
    """Способы пополнения баланса."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⭐️ Telegram Stars (XTR)", callback_data=f"topup_stars_{amount}")
    )
    builder.row(
        InlineKeyboardButton(text="💎 CryptoBot (USDT, TON, BTC)", callback_data=f"topup_crypto_{amount}")
    )
    builder.row(
        InlineKeyboardButton(text="💳 Банковская карта РФ", callback_data=f"topup_card_{amount}")
    )
    builder.row(
        InlineKeyboardButton(text="⚡️ Отмена", callback_data="client_profile")
    )
    return builder.as_markup()


def get_order_history_kb(orders: List[Order]) -> InlineKeyboardMarkup:
    """Список заказов в истории покупок."""
    builder = InlineKeyboardBuilder()

    for o in orders:
        title = o.product.title if o.product else f"Товар #{o.product_id}"
        date_str = o.created_at.strftime("%d.%m")
        builder.button(
            text=f"📦 #{o.id} | {title[:18]} ({date_str})",
            callback_data=f"view_order_{o.id}"
        )

    builder.adjust(1)
    builder.row(
        InlineKeyboardButton(text="⚡️ В профиль", callback_data="client_profile"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="to_main_menu")
    )
    return builder.as_markup()


def get_back_to_menu_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_main_menu"))
    return builder.as_markup()
