from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy import select, update, delete, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    User,
    Category,
    Product,
    ProductItem,
    Order,
    Transaction,
    ProductType,
    OrderStatus,
    PaymentStatus
    ,ReferralReward
    , ShowcaseProduct
)

REFERRAL_RATE = 0.05


def validate_showcase_minimum(unit: str, quantity: float) -> float:
    """Проверяет и нормализует минимальный заказ витринного товара."""
    if quantity <= 0:
        raise ValueError("Минимальное количество должно быть положительным")
    if unit == "г":
        if quantity < 0.5 or quantity % 0.5 != 0:
            raise ValueError("Минимум для граммов — 0.5 г с шагом 0.5")
    elif unit == "шт.":
        if quantity < 3 or not quantity.is_integer():
            raise ValueError("Минимум для штук — 3 шт. или больше целым числом")
    else:
        raise ValueError("Неизвестная единица измерения")
    return float(quantity)

async def get_showcase_products(session: AsyncSession, include_inactive: bool = False) -> List[ShowcaseProduct]:
    query = select(ShowcaseProduct).options(selectinload(ShowcaseProduct.category)).order_by(ShowcaseProduct.id)
    if not include_inactive:
        query = query.where(ShowcaseProduct.is_active == True)
    return list((await session.execute(query)).scalars().all())

async def get_showcase_product(session: AsyncSession, product_id: int) -> Optional[ShowcaseProduct]:
    return await session.get(ShowcaseProduct, product_id)


async def create_showcase_product(
    session: AsyncSession,
    title: str,
    price: float,
    image_file_id: Optional[str],
    unit: str = "шт.",
    start_quantity: Optional[float] = None
) -> ShowcaseProduct:
    if start_quantity is None:
        if unit == "г":
            start_quantity = 0.5
        elif unit == "шт.":
            start_quantity = 3.0
        else:
            start_quantity = 1.0
    start_quantity = validate_showcase_minimum(unit, float(start_quantity))

    product = ShowcaseProduct(
        title=title,
        price=price,
        image_file_id=image_file_id,
        unit=unit,
        start_quantity=start_quantity,
        is_active=True
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product

async def update_showcase_product(
    session: AsyncSession,
    product_id: int,
    title: str,
    price: float,
    image_file_id: Optional[str],
    category_id: Optional[int] = None,
    unit: Optional[str] = None,
    start_quantity: Optional[float] = None,
) -> Optional[ShowcaseProduct]:
    product = await get_showcase_product(session, product_id)
    if not product:
        return None
    product.title = title
    product.price = price
    if category_id is not None:
        product.category_id = category_id
    if image_file_id is not None:
        product.image_file_id = image_file_id
    if unit is not None:
        product.unit = unit
    if start_quantity is not None:
        product.start_quantity = validate_showcase_minimum(product.unit, float(start_quantity))
    await session.commit()
    await session.refresh(product)
    return product

async def delete_showcase_product(session: AsyncSession, product_id: int) -> bool:
    product = await get_showcase_product(session, product_id)
    if not product:
        return False
    await session.delete(product)
    await session.commit()
    return True


# ==========================================
# USERS CRUD
# ==========================================

async def get_or_create_user(
    session: AsyncSession,
    tg_id: int,
    username: Optional[str] = None,
    full_name: str = ""
) -> Tuple[User, bool]:
    """Получить существующего пользователя или создать нового."""
    query = select(User).where(User.tg_id == tg_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if user:
        # Обновим имя и юзернейм если изменились
        updated = False
        if user.username != username:
            user.username = username
            updated = True
        if user.full_name != full_name:
            user.full_name = full_name
            updated = True
        if updated:
            await session.commit()
        return user, False

    new_user = User(
        tg_id=tg_id,
        username=username,
        full_name=full_name,
        balance=0.0,
        city="",
        district=None,
        referrer_id=None,
        referral_earnings=0.0,
        used_promos="",
        is_banned=False
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user, True


async def attach_referrer(session: AsyncSession, user: User, referrer_tg_id: int) -> bool:
    """Однократно привязывает пользователя к пригласившему."""
    if user.referrer_id or user.tg_id == referrer_tg_id:
        return False
    referrer = await get_user_by_tg_id(session, referrer_tg_id)
    if not referrer or referrer.id == user.id:
        return False
    user.referrer_id = referrer.id
    await session.commit()
    return True


async def apply_referral_reward(session: AsyncSession, order: Order) -> Optional[float]:
    """Начисляет рефереру 5% за заказ ровно один раз."""
    buyer = await session.get(User, order.user_id)
    if not buyer or not buyer.referrer_id:
        return None
    referrer = await session.get(User, buyer.referrer_id)
    if not referrer:
        return None
    reward = round(order.amount * REFERRAL_RATE, 2)
    session.add(ReferralReward(order_id=order.id, referrer_id=referrer.id, amount=reward))
    referrer.balance = round(referrer.balance + reward, 2)
    referrer.referral_earnings = round(referrer.referral_earnings + reward, 2)
    return reward


async def get_user_by_tg_id(session: AsyncSession, tg_id: int) -> Optional[User]:
    """Найти пользователя по Telegram ID."""
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    return result.scalar_one_or_none()


async def get_referral_stats(session: AsyncSession, user_id: int) -> Tuple[int, float]:
    """Возвращает число приглашенных и общую сумму вознаграждений."""
    referrals_count = (await session.execute(
        select(func.count(User.id)).where(User.referrer_id == user_id)
    )).scalar() or 0
    user = await session.get(User, user_id)
    return referrals_count, round(user.referral_earnings if user else 0.0, 2)


async def get_user_by_username(session: AsyncSession, username: str) -> Optional[User]:
    """Найти пользователя по username."""
    clean_username = username.lstrip("@").strip()
    result = await session.execute(select(User).where(func.lower(User.username) == clean_username.lower()))
    return result.scalar_one_or_none()


async def update_user_balance(session: AsyncSession, tg_id: int, amount_delta: float) -> Optional[User]:
    """Изменить баланс пользователя на amount_delta (может быть как + так и -)."""
    user = await get_user_by_tg_id(session, tg_id)
    if not user:
        return None
    user.balance = round(user.balance + amount_delta, 2)
    await session.commit()
    await session.refresh(user)
    return user


async def set_user_ban_status(session: AsyncSession, tg_id: int, is_banned: bool) -> Optional[User]:
    """Установить статус блокировки пользователя."""
    user = await get_user_by_tg_id(session, tg_id)
    if not user:
        return None
    user.is_banned = is_banned
    await session.commit()
    await session.refresh(user)
    return user


async def get_all_user_tg_ids(session: AsyncSession) -> List[int]:
    """Получить список всех Telegram ID пользователей (не забаненных) для рассылки."""
    result = await session.execute(select(User.tg_id).where(User.is_banned == False))
    return list(result.scalars().all())


async def get_users_count(session: AsyncSession) -> int:
    """Общее количество пользователей в боте."""
    result = await session.execute(select(func.count(User.id)))
    return result.scalar() or 0


# ==========================================
# CATEGORIES CRUD
# ==========================================

async def get_main_categories(session: AsyncSession) -> List[Category]:
    """Получить список корневых категорий (parent_id IS NULL)."""
    result = await session.execute(
        select(Category)
        .where(and_(Category.parent_id.is_(None), Category.is_active == True))
        .order_by(Category.id)
    )
    return list(result.scalars().all())


async def get_subcategories(session: AsyncSession, parent_id: int) -> List[Category]:
    """Получить подкатегории для заданной родительской категории."""
    result = await session.execute(
        select(Category)
        .where(and_(Category.parent_id == parent_id, Category.is_active == True))
        .order_by(Category.id)
    )
    return list(result.scalars().all())


async def get_category_by_id(session: AsyncSession, category_id: int) -> Optional[Category]:
    """Получить категорию по ID."""
    result = await session.execute(select(Category).where(Category.id == category_id))
    return result.scalar_one_or_none()


async def create_category(session: AsyncSession, name: str, parent_id: Optional[int] = None) -> Category:
    """Создать новую категорию или подкатегорию."""
    category = Category(name=name, parent_id=parent_id, is_active=True)
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


async def delete_category(session: AsyncSession, category_id: int) -> bool:
    """Удалить категорию и все вложенные товары/подкатегории."""
    category = await get_category_by_id(session, category_id)
    if not category:
        return False
    await session.delete(category)
    await session.commit()
    return True


# ==========================================
# PRODUCTS & STOCK CRUD
# ==========================================

async def get_products_by_category(session: AsyncSession, category_id: int) -> List[Product]:
    """Получить активные товары в указанной категории."""
    result = await session.execute(
        select(Product)
        .where(and_(Product.category_id == category_id, Product.is_active == True))
        .order_by(Product.id)
    )
    return list(result.scalars().all())


async def get_product_by_id(session: AsyncSession, product_id: int) -> Optional[Product]:
    """Получить карточку товара по ID."""
    result = await session.execute(
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.id == product_id)
    )
    return result.scalar_one_or_none()


async def update_product_price(session: AsyncSession, product_id: int, new_price: float) -> Optional[Product]:
    """Обновить цену товара."""
    product = await get_product_by_id(session, product_id)
    if not product:
        return None
    product.price = new_price
    await session.commit()
    await session.refresh(product)
    return product


async def delete_product(session: AsyncSession, product_id: int) -> bool:
    """Удалить товар."""
    product = await get_product_by_id(session, product_id)
    if not product:
        return False
    await session.delete(product)
    await session.commit()
    return True


async def get_product_stock(session: AsyncSession, product_id: int) -> int:
    """Получить количество доступных (не проданных) штучных единиц товара."""
    result = await session.execute(
        select(func.count(ProductItem.id))
        .where(and_(ProductItem.product_id == product_id, ProductItem.is_sold == False))
    )
    return result.scalar() or 0


async def add_product_items(session: AsyncSession, product_id: int, items_data: List[str]) -> int:
    """
    Массово загрузить строки цифрового товара (ключи, аккаунты).
    Возвращает количество успешно добавленных записей.
    """
    clean_items = [line.strip() for line in items_data if line.strip()]
    if not clean_items:
        return 0

    items_objects = [
        ProductItem(product_id=product_id, data=line, is_sold=False)
        for line in clean_items
    ]
    session.add_all(items_objects)
    await session.commit()
    return len(items_objects)


async def buy_product_atomic(
    session: AsyncSession,
    user: User,
    product: Product,
    payment_method: str = "balance"
) -> Tuple[Optional[Order], Optional[str]]:
    """
    Атомарная покупка товара:
    1. Проверяет баланс (если payment_method == 'balance').
    2. Если DIGITAL_ITEM: выбирает 1 не проданную единицу из склада ProductItem, помечает ее проданной.
    3. Создает заказ Order и списывает баланс.
    Возвращает: (Order, delivered_content) или (None, error_message).
    """
    if payment_method == "balance":
        if user.balance < product.price:
            return None, "Недостаточно средств на балансе."

    delivered_data = ""
    assigned_item: Optional[ProductItem] = None

    if product.product_type == ProductType.DIGITAL_ITEM:
        # Выбираем одну свободную позицию
        item_query = (
            select(ProductItem)
            .where(and_(ProductItem.product_id == product.id, ProductItem.is_sold == False))
            .limit(1)
        )
        item_res = await session.execute(item_query)
        assigned_item = item_res.scalar_one_or_none()

        if not assigned_item:
            return None, "К сожалению, товар закончился на складе."

        assigned_item.is_sold = True
        assigned_item.sold_at = datetime.utcnow()
        delivered_data = assigned_item.data

    elif product.product_type == ProductType.FILE:
        delivered_data = f"FILE:{product.file_id}"

    elif product.product_type == ProductType.SERVICE:
        delivered_data = f"Инструкция по услуге: {product.description}\nСвяжитесь с администрацией для активации."

    # Списываем баланс если оплата с баланса
    if payment_method == "balance":
        user.balance = round(user.balance - product.price, 2)

    # Создаем заказ
    order = Order(
        user_id=user.id,
        product_id=product.id,
        amount=product.price,
        payment_method=payment_method,
        status=OrderStatus.COMPLETED,
        delivered_data=delivered_data
    )
    session.add(order)
    await session.flush()  # Получаем order.id

    if assigned_item:
        assigned_item.order_id = order.id

    await apply_referral_reward(session, order)

    await session.commit()
    await session.refresh(order)
    return order, delivered_data


# ==========================================
# ORDERS & HISTORY CRUD
# ==========================================

async def get_user_orders(session: AsyncSession, user_id: int, limit: int = 20, offset: int = 0) -> List[Order]:
    """Получить историю заказов пользователя с подгрузкой товаров."""
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.product))
        .where(Order.user_id == user_id)
        .order_by(desc(Order.created_at))
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_order_by_id(session: AsyncSession, order_id: int) -> Optional[Order]:
    """Получить заказ по его ID."""
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.product))
        .where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


# ==========================================
# TRANSACTIONS CRUD
# ==========================================

async def create_transaction(
    session: AsyncSession,
    user_id: int,
    amount: float,
    payment_system: str,
    invoice_id: Optional[str] = None
) -> Transaction:
    """Создать запись о начале транзакции пополнения."""
    transaction = Transaction(
        user_id=user_id,
        amount=amount,
        payment_system=payment_system,
        status=PaymentStatus.PENDING,
        invoice_id=invoice_id
    )
    session.add(transaction)
    await session.commit()
    await session.refresh(transaction)
    return transaction


async def get_transaction_by_id(session: AsyncSession, transaction_id: int) -> Optional[Transaction]:
    """Получить транзакцию по ID с загрузкой пользователя."""
    result = await session.execute(
        select(Transaction)
        .options(selectinload(Transaction.user))
        .where(Transaction.id == transaction_id)
    )
    return result.scalar_one_or_none()


async def approve_receipt_transaction(session: AsyncSession, transaction_id: int, amount_rub: float) -> Optional[Transaction]:
    """Подтвердить чек, обновить сумму в рублях и начислить баланс пользователю."""
    tx = await get_transaction_by_id(session, transaction_id)
    if not tx or tx.status == PaymentStatus.SUCCESS:
        return tx

    tx.amount = amount_rub
    tx.status = PaymentStatus.SUCCESS
    tx.user.balance = round(tx.user.balance + amount_rub, 2)
    await session.commit()
    await session.refresh(tx)
    return tx


async def reject_receipt_transaction(session: AsyncSession, transaction_id: int) -> Optional[Transaction]:
    """Отклонить транзакцию по чеку."""
    tx = await get_transaction_by_id(session, transaction_id)
    if not tx:
        return None

    tx.status = PaymentStatus.FAILED
    await session.commit()
    await session.refresh(tx)
    return tx


# ==========================================
# STATISTICS & ANALYTICS
# ==========================================

async def get_analytics_stats(session: AsyncSession, period: str = "all") -> Dict[str, Any]:
    """
    Сбор аналитики за выбранный период:
    period: 'today', 'week', 'all'
    """
    now = datetime.utcnow()
    filter_date = None

    if period == "today":
        filter_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        filter_date = now - timedelta(days=7)

    # Пользователи
    users_query = select(func.count(User.id))
    if filter_date:
        users_query = users_query.where(User.created_at >= filter_date)
    new_users = (await session.execute(users_query)).scalar() or 0

    # Заказы и выручка
    orders_query = select(func.count(Order.id), func.sum(Order.amount)).where(Order.status == OrderStatus.COMPLETED)
    if filter_date:
        orders_query = orders_query.where(Order.created_at >= filter_date)
    orders_res = (await session.execute(orders_query)).one()
    orders_count = orders_res[0] or 0
    total_revenue = round(orders_res[1] or 0.0, 2)

    return {
        "period": period,
        "new_users": new_users,
        "orders_count": orders_count,
        "total_revenue": total_revenue
    }


async def get_top_products(session: AsyncSession, limit: int = 5) -> List[Tuple[str, int, float]]:
    """
    Получить топ продаваемых товаров: [(название, кол-во_продаж, выручка), ...]
    """
    query = (
        select(
            Product.title,
            func.count(Order.id).label("sales_count"),
            func.sum(Order.amount).label("revenue")
        )
        .join(Order, Order.product_id == Product.id)
        .where(Order.status == OrderStatus.COMPLETED)
        .group_by(Product.id, Product.title)
        .order_by(desc("sales_count"))
        .limit(limit)
    )
    result = await session.execute(query)
    return [(row[0], row[1], round(row[2] or 0.0, 2)) for row in result.all()]
