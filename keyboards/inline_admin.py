from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton as TelegramInlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models import Category, Product, City, District
from config import config
from utils.button_settings import registered_buttons, resolve_button


def InlineKeyboardButton(*, text: str, **kwargs):
    _, text, emoji_id = resolve_button(text, scope="admin", **kwargs)
    if emoji_id:
        kwargs.setdefault("icon_custom_emoji_id", emoji_id)
    return TelegramInlineKeyboardButton(text=text, **kwargs)


def get_admin_main_kb() -> InlineKeyboardMarkup:
    """Главное меню админ-панели."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👥 Пользователи", callback_data="adm_users")
    )
    builder.row(
        InlineKeyboardButton(text="📢 Рассылка", callback_data="adm_broadcast"),
        InlineKeyboardButton(text="📊 Аналитика и статистика", callback_data="adm_stats")
    )
    builder.row(
        InlineKeyboardButton(text="🛍️ Товары", callback_data="adm_showcase")
    )
    builder.row(
        InlineKeyboardButton(text="🏙️ Города и районы", callback_data="adm_cities")
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки бота", callback_data="adm_settings")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ В клиентское меню", callback_data="to_main_menu")
    )
    return builder.as_markup()


def get_showcase_admin_kb(products) -> InlineKeyboardMarkup:
    """Отдельное управление товарами клиентского каталога."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Добавить товар", callback_data="adm_showcase_add"))
    for product in products:
        builder.row(
            InlineKeyboardButton(
                text=f"🏷 {product.title} · {product.price:g} ₽ · мин. {product.start_quantity:g}{product.unit}",
                callback_data=f"adm_showcase_edit_{product.id}"
            ),
            InlineKeyboardButton(text="✏️", callback_data=f"adm_showcase_edit_{product.id}"),
            InlineKeyboardButton(text="🖼️", callback_data=f"adm_showcase_image_{product.id}"),
            InlineKeyboardButton(text="🗑", callback_data=f"adm_showcase_del_{product.id}")
        )
    builder.row(InlineKeyboardButton(text="🔙 В админку", callback_data="adm_main"))
    return builder.as_markup()


def get_showcase_delete_confirm_kb(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"adm_showcase_confirm_del_{product_id}"),
            InlineKeyboardButton(text="↩️ Отмена", callback_data="adm_showcase"),
        ]
    ])


def get_showcase_unit_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚖️ За грамм (г)", callback_data="showcase_unit_g"),
            InlineKeyboardButton(text="📦 За штуку (шт.)", callback_data="showcase_unit_piece"),
        ]
    ])


def get_admin_settings_kb() -> InlineKeyboardMarkup:
    """Меню просмотра настроек бота для администратора."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎭 Изменить стартовый стикер", callback_data="adm_change_start_sticker")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Редактировать кнопки", callback_data="adm_edit_buttons")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить настройки", callback_data="adm_settings")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 В админку", callback_data="adm_main")
    )
    return builder.as_markup()


def get_button_editor_kb(page: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    buttons = registered_buttons("main_menu")
    page_size = 8
    start = max(page, 0) * page_size
    for index, _, label in buttons[start:start + page_size]:
        builder.row(
            InlineKeyboardButton(
                text=f"✏️ {label[:40] if len(label) > 40 else label}",
                callback_data=f"adm_button_edit_{index}"
            )
        )
    navigation = []
    if page > 0:
        navigation.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"adm_button_page_{page - 1}"))
    if start + page_size < len(buttons):
        navigation.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"adm_button_page_{page + 1}"))
    if navigation:
        builder.row(*navigation)
    builder.row(InlineKeyboardButton(text="🔙 К настройкам", callback_data="adm_settings"))
    return builder.as_markup()


def get_categories_admin_kb(categories: List[Category]) -> InlineKeyboardMarkup:
    """Список категорий для админа с возможностью перехода к товарам или удалению."""
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.row(
            InlineKeyboardButton(text=f"📁 {cat.name}", callback_data=f"adm_cat_{cat.id}"),
            InlineKeyboardButton(text="❌", callback_data=f"adm_del_cat_{cat.id}")
        )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="adm_catalog"))
    return builder.as_markup()


def get_products_admin_kb(products: List[Product], category_id: int) -> InlineKeyboardMarkup:
    """Список товаров в категории для админа."""
    builder = InlineKeyboardBuilder()
    for prod in products:
        builder.row(
            InlineKeyboardButton(text=f"🏷 {prod.title} ({prod.price:g} ₽)", callback_data=f"adm_prod_{prod.id}"),
            InlineKeyboardButton(text="❌", callback_data=f"adm_del_prod_{prod.id}")
        )
    builder.row(InlineKeyboardButton(text="🔙 К категориям", callback_data="adm_list_categories"))
    return builder.as_markup()


def get_product_admin_card_kb(product_id: int, category_id: int) -> InlineKeyboardMarkup:
    """Карточка управления конкретным товаром в админке."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📥 Залить базу (ключи/строки)", callback_data=f"adm_stock_{product_id}")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить цену", callback_data=f"adm_price_{product_id}"),
        InlineKeyboardButton(text="🗑 Удалить товар", callback_data=f"adm_del_prod_{product_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 К товарам", callback_data=f"adm_cat_{category_id}")
    )
    return builder.as_markup()


def get_product_types_kb() -> InlineKeyboardMarkup:
    """Выбор типа создаваемого товара."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔑 Цифровой ключ / строка (аккаунты)", callback_data="type_digital_item")
    )
    builder.row(
        InlineKeyboardButton(text="📁 Статичный файл (архив, документ)", callback_data="type_file")
    )
    builder.row(
        InlineKeyboardButton(text="🛠 Услуга / Ручная выдача", callback_data="type_service")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="adm_catalog")
    )
    return builder.as_markup()


def get_user_manage_kb(user_id: int, is_banned: bool, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Кнопки управления найденным пользователем."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💰 Начислить баланс (+)", callback_data=f"adm_bal_add_{user_id}"),
        InlineKeyboardButton(text="💸 Списать баланс (-)", callback_data=f"adm_bal_sub_{user_id}")
    )
    ban_text = "🟢 Разблокировать" if is_banned else "⛔️ Заблокировать"
    ban_action = "unban" if is_banned else "ban"
    builder.row(
        InlineKeyboardButton(text=ban_text, callback_data=f"adm_{ban_action}_{user_id}")
    )
    builder.row(
        InlineKeyboardButton(
            text="✅ Уже администратор" if is_admin else "👑 Сделать админом",
            callback_data=f"adm_make_admin_{user_id}" if not is_admin else "adm_admin_already"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🔙 К поиску", callback_data="adm_users")
    )
    return builder.as_markup()


def get_stats_period_kb() -> InlineKeyboardMarkup:
    """Периоды отображения аналитики."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 За сегодня", callback_data="stat_today"),
        InlineKeyboardButton(text="🗓 За 7 дней", callback_data="stat_week"),
        InlineKeyboardButton(text="♾ За все время", callback_data="stat_all")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 В админку", callback_data="adm_main")
    )
    return builder.as_markup()


def get_broadcast_confirm_kb() -> InlineKeyboardMarkup:
    """Подтверждение старта рассылки."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚀 Запустить рассылку", callback_data="adm_start_broadcast"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="adm_cancel_broadcast")
    )
    return builder.as_markup()


# -------------------------------------------------------------
# 🏙️ КЛАВИАТУРЫ УПРАВЛЕНИЯ ГОРОДАМИ И РАЙОНАМИ
# -------------------------------------------------------------

def get_admin_cities_kb(cities: List[City], page: int = 0) -> InlineKeyboardMarkup:
    """Список городов для администратора с пагинацией."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить город", callback_data="adm_city_add")
    )

    page_size = 8
    total_pages = max(1, (len(cities) + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))

    start = page * page_size
    current_cities = cities[start : start + page_size]

    for city in current_cities:
        dist_count = len([d for d in city.districts if d.is_active])
        builder.row(
            InlineKeyboardButton(
                text=f"📍 {city.name} ({dist_count} р-нов)",
                callback_data=f"adm_city_view_{city.id}"
            )
        )

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"adm_cities_page_{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"adm_cities_page_{page + 1}"))
    if nav_row:
        builder.row(*nav_row)

    builder.row(InlineKeyboardButton(text="🔙 В админку", callback_data="adm_main"))
    return builder.as_markup()


def get_admin_city_view_kb(city: City, districts: List[District], page: int = 0) -> InlineKeyboardMarkup:
    """Экран города со списком районов, управлением (редактировать/удалить каждый) и кнопками добавления."""
    builder = InlineKeyboardBuilder()

    # --- действия с городом ---
    builder.row(
        InlineKeyboardButton(text="✏️ Переименовать город", callback_data=f"adm_city_rename_{city.id}"),
        InlineKeyboardButton(text="🗑 Удалить город", callback_data=f"adm_city_del_{city.id}")
    )
    builder.row(
        InlineKeyboardButton(text="➕ Добавить район(ы)", callback_data=f"adm_dist_add_{city.id}")
    )

    # --- список районов с пагинацией ---
    page_size = 6
    total_pages = max(1, (len(districts) + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    current_districts = districts[start: start + page_size]

    for dist in current_districts:
        builder.row(
            InlineKeyboardButton(
                text=f"📍 {dist.name}",
                callback_data=f"adm_dist_rename_{dist.id}"
            ),
            InlineKeyboardButton(text="✏️", callback_data=f"adm_dist_rename_{dist.id}"),
            InlineKeyboardButton(text="🗑", callback_data=f"adm_dist_del_{dist.id}")
        )

    # --- навигация по страницам ---
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"adm_dist_page_{city.id}_{page - 1}"))
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="adm_noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"adm_dist_page_{city.id}_{page + 1}"))
    if nav_row:
        builder.row(*nav_row)

    builder.row(InlineKeyboardButton(text="🔙 К списку городов", callback_data="adm_cities"))
    return builder.as_markup()


def get_admin_city_del_confirm_kb(city_id: int) -> InlineKeyboardMarkup:
    """Подтверждение удаления города."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗑 Да, удалить город", callback_data=f"adm_city_confirm_del_{city_id}"),
            InlineKeyboardButton(text="↩️ Отмена", callback_data=f"adm_city_view_{city_id}"),
        ]
    ])


def get_admin_dist_del_confirm_kb(district_id: int, city_id: int) -> InlineKeyboardMarkup:
    """Подтверждение удаления района."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗑 Да, удалить район", callback_data=f"adm_dist_confirm_del_{district_id}"),
            InlineKeyboardButton(text="↩️ Отмена", callback_data=f"adm_city_view_{city_id}"),
        ]
    ])


def get_admin_city_rename_kb(city_id: int) -> InlineKeyboardMarkup:
    """Клавиатура отмены переименования города."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Отмена", callback_data=f"adm_city_view_{city_id}")]
    ])


def get_admin_dist_rename_kb(district_id: int, city_id: int) -> InlineKeyboardMarkup:
    """Клавиатура отмены переименования района."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Отмена", callback_data=f"adm_city_view_{city_id}")]
    ])
