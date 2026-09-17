from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database.models import Category, Product


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
        InlineKeyboardButton(text="🔄 Обновить настройки", callback_data="adm_settings")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 В админку", callback_data="adm_main")
    )
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


def get_user_manage_kb(user_id: int, is_banned: bool) -> InlineKeyboardMarkup:
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
