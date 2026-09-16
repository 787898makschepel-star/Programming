from typing import List, Tuple, Dict, Any
from database.models import User, Product, Order, ProductType
from config import config

DIVIDER = "────────────────────────────"


def format_main_menu(user: User) -> str:
    """Шаблон главного экрана магазина."""
    name = user.full_name or user.username or "Покупатель"
    return (
        f"👋 <b>Добро пожаловать, {name}!</b>\n"
        f"{DIVIDER}\n"
        f"⚡️ <b>MWAVES STORE</b> — автоматизированный сервис мгновенной "
        f"покупки цифровых товаров, подписок и аккаунтов.\n\n"
        f"💰 Ваш баланс: <code>{user.balance:g} ₽</code>\n"
        f"🆔 Ваш Telegram ID: <code>{user.tg_id}</code>\n"
        f"{DIVIDER}\n"
        f"🛡 <i>Все товары проверяются автоматически перед выдачей.</i>\n"
        f"Выберите необходимый раздел в меню ниже:"
    )


def format_profile(user: User, orders_count: int) -> str:
    """Шаблон личного кабинета."""
    reg_date = user.created_at.strftime("%d.%m.%Y") if user.created_at else "Недавно"
    status_label = "⛔️ Заблокирован" if user.is_banned else "🟢 Активен"

    return (
        f"👤 <b>Личный кабинет</b>\n"
        f"{DIVIDER}\n"
        f"🆔 <b>ID аккаунта:</b> <code>{user.tg_id}</code>\n"
        f"👤 <b>Username:</b> @{user.username or 'не указан'}\n"
        f"💰 <b>Текущий баланс:</b> <code>{user.balance:g} ₽</code>\n"
        f"📦 <b>Куплено товаров:</b> <b>{orders_count} шт.</b>\n"
        f"📅 <b>Дата регистрации:</b> <code>{reg_date}</code>\n"
        f"🛡 <b>Статус:</b> {status_label}\n"
        f"{DIVIDER}\n"
        f"💡 <i>Вы можете моментально пополнить баланс или повторно "
        f"посмотреть купленные ранее данные в разделе «Мои покупки».</i>"
    )


def format_product_card(product: Product, stock_count: int) -> str:
    """Шаблон карточки товара."""
    if product.product_type == ProductType.DIGITAL_ITEM:
        stock_badge = f"🟢 <b>В наличии:</b> <code>{stock_count} шт.</code>" if stock_count > 0 else "🔴 <b>Нет в наличии</b>"
    elif product.product_type == ProductType.FILE:
        stock_badge = "📁 <b>Тип:</b> <code>Файл / Архив</code> (Доступен)"
    else:
        stock_badge = "🛠 <b>Тип:</b> <code>Услуга</code> (Ручная выдача)"

    desc = product.description.strip() if product.description else "Описание отсутствует."

    return (
        f"🏷 <b>{product.title}</b>\n"
        f"{DIVIDER}\n"
        f"📝 <b>Описание:</b>\n{desc}\n\n"
        f"{stock_badge}\n"
        f"💵 <b>Стоимость:</b> <code>{product.price:g} ₽</code>\n"
        f"{DIVIDER}\n"
        f"⚡️ <i>После нажатия кнопки «Купить» с вашего баланса спишется указанная сумма, "
        f"а товар будет мгновенно отправлен в чат.</i>"
    )


def format_purchase_success(order: Order, product: Product, delivered_data: str, new_balance: float) -> str:
    """Шаблон успешного оформления покупки."""
    return (
        f"🎉 <b>Покупка успешно совершена!</b>\n"
        f"{DIVIDER}\n"
        f"📦 <b>Заказ:</b> <code>#{order.id}</code>\n"
        f"🏷 <b>Товар:</b> <b>{product.title}</b>\n"
        f"💵 <b>Сумма списания:</b> <code>{order.amount:g} ₽</code>\n"
        f"💰 <b>Оставшийся баланс:</b> <code>{new_balance:g} ₽</code>\n"
        f"{DIVIDER}\n"
        f"🔑 <b>Ваши данные:</b>\n"
        f"<code>{delivered_data}</code>\n\n"
        f"💾 <i>Все приобретенные ключи и аккаунты сохранены навсегда в разделе «Мой профиль ➔ Мои покупки».</i>"
    )


def format_order_details(order: Order) -> str:
    """Шаблон просмотра ранее купленного заказа."""
    date_str = order.created_at.strftime("%d.%m.%Y %H:%M")
    title = order.product.title if order.product else f"Товар #{order.product_id}"

    return (
        f"📦 <b>Информация о заказе #{order.id}</b>\n"
        f"{DIVIDER}\n"
        f"🏷 <b>Товар:</b> <b>{title}</b>\n"
        f"💵 <b>Стоимость:</b> <code>{order.amount:g} ₽</code>\n"
        f"📅 <b>Дата покупки:</b> <code>{date_str}</code>\n"
        f"💳 <b>Способ оплаты:</b> <code>{order.payment_method}</code>\n"
        f"{DIVIDER}\n"
        f"🔑 <b>Выданные данные:</b>\n"
        f"<code>{order.delivered_data}</code>"
    )


def format_faq() -> str:
    """Информационный раздел FAQ."""
    return (
        f"📖 <b>База знаний и ответы на вопросы</b>\n"
        f"{DIVIDER}\n"
        f"🔹 <b>Как происходит выдача товара?</b>\n"
        f"Выдача происходит моментально после оплаты. Товар отображается в чате "
        f"и дублируется в разделе «Мои покупки».\n\n"
        f"🔹 <b>Как пополнить баланс?</b>\n"
        f"В разделе «Профиль» нажмите «Пополнить баланс». Доступны Telegram Stars, "
        f"криптовалюта через CryptoBot и банковские карты.\n\n"
        f"🔹 <b>Есть ли гарантия на товар?</b>\n"
        f"Да, гарантия предоставляется на все категории. Если у вас возникла "
        f"сложность — обратитесь к нашему менеджеру.\n"
        f"{DIVIDER}\n"
        f"🆘 <b>Оператор поддержки:</b> {config.SUPPORT_USERNAME}"
    )


# ==========================================
# ШАБЛОНЫ АДМИНИСТРАТИВНОЙ ПАНЕЛИ
# ==========================================

def format_admin_dashboard() -> str:
    """Главный экран админ-панели."""
    return (
        f"👑 <b>Панель управления магазином</b>\n"
        f"{DIVIDER}\n"
        f"Добро пожаловать в административную систему управления.\n\n"
        f"Доступные разделы:\n"
        f"• <b>Пользователи</b> — поиск, балансы и блокировки\n"
        f"• <b>Рассылка</b> — создание массовых уведомлений с отчетом\n"
        f"• <b>Аналитика</b> — выручка, конверсия и топ продаж\n"
        f"{DIVIDER}\n"
        f"Выберите требуемый модуль:"
    )


def format_admin_product_card(product: Product, stock_count: int) -> str:
    """Карточка товара для администратора."""
    return (
        f"🏷 <b>Управление товаром #{product.id}</b>\n"
        f"{DIVIDER}\n"
        f"📌 <b>Название:</b> <b>{product.title}</b>\n"
        f"📝 <b>Описание:</b> {product.description or 'Отсутствует'}\n"
        f"💵 <b>Цена:</b> <code>{product.price:g} ₽</code>\n"
        f"⚙️ <b>Тип:</b> <code>{product.product_type.value}</code>\n"
        f"📦 <b>Текущий остаток:</b> <b>{stock_count} шт.</b>\n"
        f"{DIVIDER}\n"
        f"<i>Для залива новой партии аккаунтов или ключей нажмите кнопку ниже.</i>"
    )


def format_admin_user_card(user: User, orders_count: int) -> str:
    """Карточка пользователя в панели администратора."""
    status_label = "⛔️ Заблокирован" if user.is_banned else "🟢 Активен"
    reg_date = user.created_at.strftime("%d.%m.%Y %H:%M") if user.created_at else "-"

    return (
        f"👤 <b>Профиль пользователя #{user.id}</b>\n"
        f"{DIVIDER}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user.tg_id}</code>\n"
        f"👤 <b>Username:</b> @{user.username or 'отсутствует'}\n"
        f"📝 <b>Имя:</b> <b>{user.full_name}</b>\n"
        f"💰 <b>Баланс:</b> <code>{user.balance:g} ₽</code>\n"
        f"📦 <b>Заказов:</b> <b>{orders_count} шт.</b>\n"
        f"🛡 <b>Статус:</b> <b>{status_label}</b>\n"
        f"📅 <b>Дата регистрации:</b> <code>{reg_date}</code>\n"
        f"{DIVIDER}\n"
        f"Выберите действие с пользователем:"
    )


def format_admin_stats(stats: Dict[str, Any], top_products: List[Tuple[str, int, float]], period_title: str) -> str:
    """Экран аналитики для администратора."""
    text = (
        f"📊 <b>Финансовая аналитика ({period_title})</b>\n"
        f"{DIVIDER}\n"
        f"👥 Новых клиентов: <b>{stats['new_users']}</b>\n"
        f"📦 Завершенных заказов: <b>{stats['orders_count']} шт.</b>\n"
        f"💰 Общая выручка: <code>{stats['total_revenue']:g} ₽</code>\n"
        f"{DIVIDER}\n"
        f"🏆 <b>Топ продаваемых позиций:</b>\n"
    )
    if top_products:
        for idx, (title, count, revenue) in enumerate(top_products, start=1):
            text += f"{idx}. <b>{title}</b> — {count} шт. (<code>{revenue:g} ₽</code>)\n"
    else:
        text += "<i>Продаж за указанный период не зафиксировано.</i>\n"
    return text
