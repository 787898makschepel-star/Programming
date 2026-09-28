import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Category, Product, ProductItem, ProductType, ShowcaseProduct

logger = logging.getLogger(__name__)

from catalog_config import SHOWCASE_PRODUCTS


async def seed_showcase_catalog(session: AsyncSession) -> None:
    """
    Синхронизирует витрину с файлом catalog_config.py:
    обновляет названия, цены, единицы (г/шт.), минимальный заказ и картинки.
    """
    default_category = (await session.execute(select(Category).order_by(Category.id).limit(1))).scalar_one_or_none()
    default_cat_id = default_category.id if default_category else None

    existing_products = list((await session.execute(
        select(ShowcaseProduct).order_by(ShowcaseProduct.id)
    )).scalars().all())

    for idx, item in enumerate(SHOWCASE_PRODUCTS):
        title = item.get("title", f"Товар {idx + 1}")
        price = float(item.get("price", 1000))
        unit = str(item.get("unit", "шт."))
        min_qty = float(item.get("min_quantity") or item.get("start_quantity") or (0.5 if unit == "г" else 3.0))
        image = item.get("image") or item.get("image_file_id")

        if idx < len(existing_products):
            prod = existing_products[idx]
            prod.title = title
            prod.price = price
            prod.unit = unit
            prod.start_quantity = min_qty
            prod.image_file_id = image
            prod.is_active = item.get("is_active", True)
            if default_cat_id and not prod.category_id:
                prod.category_id = default_cat_id
        else:
            new_prod = ShowcaseProduct(
                title=title,
                price=price,
                unit=unit,
                start_quantity=min_qty,
                image_file_id=image,
                category_id=default_cat_id,
                is_active=item.get("is_active", True)
            )
            session.add(new_prod)

    if len(existing_products) > len(SHOWCASE_PRODUCTS):
        for prod in existing_products[len(SHOWCASE_PRODUCTS):]:
            prod.is_active = False

    await session.commit()
    logger.info("Витрина товаров успешно синхронизирована с catalog_config.py (%d позиций).", len(SHOWCASE_PRODUCTS))


async def seed_initial_catalog(session: AsyncSession) -> None:
    """
    Наполняет магазин стартовым ассортиментом цифровых товаров (аналог @mwavesrobot),
    если база данных пустая.
    """
    cat_count_res = await session.execute(select(func.count(Category.id)))
    if (cat_count_res.scalar() or 0) > 0:
        return  # База уже наполнена

    logger.info("Начальное заполнение каталога товарами и складом @mwavesrobot...")

    # 1. Категория Telegram Premium
    cat_tg = Category(name="💎 Telegram Премиум & Stars", is_active=True)
    session.add(cat_tg)
    await session.flush()

    prod_tg_3m = Product(
        category_id=cat_tg.id,
        title="Telegram Premium (3 месяца)",
        description="Официальная подписка в виде подарочной ссылки (Gift link). Активация на любой аккаунт без входа.",
        price=990.0,
        product_type=ProductType.DIGITAL_ITEM,
        is_active=True
    )
    prod_tg_12m = Product(
        category_id=cat_tg.id,
        title="Telegram Premium (12 месяцев)",
        description="Годовая премиум-подписка со скидкой 40%. Моментальная выдача официальной gift-ссылки.",
        price=2490.0,
        product_type=ProductType.DIGITAL_ITEM,
        is_active=True
    )
    prod_tg_stars = Product(
        category_id=cat_tg.id,
        title="Telegram Stars ⭐ 100 XTR",
        description="Пакет 100 звезд Telegram для оплаты в ботах и поддержки каналов.",
        price=190.0,
        product_type=ProductType.DIGITAL_ITEM,
        is_active=True
    )
    session.add_all([prod_tg_3m, prod_tg_12m, prod_tg_stars])
    await session.flush()

    # Склад для TG Premium
    items_tg_3m = [
        ProductItem(product_id=prod_tg_3m.id, data="https://t.me/giftcode/MWAVES_PREM3M_A98F71BC24"),
        ProductItem(product_id=prod_tg_3m.id, data="https://t.me/giftcode/MWAVES_PREM3M_B12D88EF31"),
        ProductItem(product_id=prod_tg_3m.id, data="https://t.me/giftcode/MWAVES_PREM3M_C44A19FF02"),
    ]
    items_tg_12m = [
        ProductItem(product_id=prod_tg_12m.id, data="https://t.me/giftcode/MWAVES_PREM12M_X901AA8721"),
        ProductItem(product_id=prod_tg_12m.id, data="https://t.me/giftcode/MWAVES_PREM12M_Z440EE1934"),
    ]
    items_stars = [
        ProductItem(product_id=prod_tg_stars.id, data="https://t.me/giftcode/STARS100_MWV_8819A"),
        ProductItem(product_id=prod_tg_stars.id, data="https://t.me/giftcode/STARS100_MWV_9934B"),
        ProductItem(product_id=prod_tg_stars.id, data="https://t.me/giftcode/STARS100_MWV_1120C"),
    ]
    session.add_all(items_tg_3m + items_tg_12m + items_stars)

    # 2. Категория VPN & Proxy
    cat_vpn = Category(name="🌐 Скоростной VPN (VLESS)", is_active=True)
    session.add(cat_vpn)
    await session.flush()

    prod_vpn_1m = Product(
        category_id=cat_vpn.id,
        title="VLESS Безлимит (1 месяц)",
        description="Протокол нового поколения VLESS Reality. Не блокируется провайдерами, скорость до 1 Гбит/с. Подходит для iOS, Android, Windows.",
        price=149.0,
        product_type=ProductType.DIGITAL_ITEM,
        is_active=True
    )
    prod_vpn_3m = Product(
        category_id=cat_vpn.id,
        title="VLESS Безлимит (3 месяца)",
        description="Выгодный тариф на 90 дней безлимитного скоростного интернета. Подключение за 1 минуту.",
        price=389.0,
        product_type=ProductType.DIGITAL_ITEM,
        is_active=True
    )
    session.add_all([prod_vpn_1m, prod_vpn_3m])
    await session.flush()

    items_vpn_1m = [
        ProductItem(product_id=prod_vpn_1m.id, data="vless://mwaves-vpn-key-01@nl.node.mwaves.net:443?security=reality#MWAVES_VPN_1M"),
        ProductItem(product_id=prod_vpn_1m.id, data="vless://mwaves-vpn-key-02@de.node.mwaves.net:443?security=reality#MWAVES_VPN_1M"),
        ProductItem(product_id=prod_vpn_1m.id, data="vless://mwaves-vpn-key-03@fi.node.mwaves.net:443?security=reality#MWAVES_VPN_1M"),
    ]
    items_vpn_3m = [
        ProductItem(product_id=prod_vpn_3m.id, data="vless://mwaves-vpn-3m-01@nl.node.mwaves.net:443?security=reality#MWAVES_VPN_3M"),
        ProductItem(product_id=prod_vpn_3m.id, data="vless://mwaves-vpn-3m-02@de.node.mwaves.net:443?security=reality#MWAVES_VPN_3M"),
    ]
    session.add_all(items_vpn_1m + items_vpn_3m)

    # 3. Категория AI & Нейросети
    cat_ai = Category(name="🤖 ChatGPT & ИИ Подписки", is_active=True)
    session.add(cat_ai)
    await session.flush()

    prod_gpt = Product(
        category_id=cat_ai.id,
        title="ChatGPT Plus (GPT-4o) Аккаунт",
        description="Индивидуальный аккаунт с активной подпиской ChatGPT Plus на 1 месяц. Полный доступ к GPT-4o, DALL-E 3 и генерации файлов.",
        price=1890.0,
        product_type=ProductType.DIGITAL_ITEM,
        is_active=True
    )
    session.add(prod_gpt)
    await session.flush()

    items_gpt = [
        ProductItem(product_id=prod_gpt.id, data="chatgpt_user442@mwaves-mail.com:SecurePass#9910"),
        ProductItem(product_id=prod_gpt.id, data="chatgpt_user819@mwaves-mail.com:AlphaBeta!2026"),
    ]
    session.add_all(items_gpt)

    # 4. Категория Игры & Discord
    cat_games = Category(name="🎮 Discord & Игровые ключи", is_active=True)
    session.add(cat_games)
    await session.flush()

    prod_nitro = Product(
        category_id=cat_games.id,
        title="Discord Nitro (1 месяц) с 2 бустами",
        description="Гифт-ссылка на активацию подписки Discord Nitro Full. Кастомные эмодзи, стримы 1080p 60fps.",
        price=349.0,
        product_type=ProductType.DIGITAL_ITEM,
        is_active=True
    )
    prod_steam = Product(
        category_id=cat_games.id,
        title="Steam Лицензионный ключ [Random AAA]",
        description="Ключ для платформы Steam с гарантией игры от 990 рублей в официальном магазине Steam.",
        price=199.0,
        product_type=ProductType.DIGITAL_ITEM,
        is_active=True
    )
    session.add_all([prod_nitro, prod_steam])
    await session.flush()

    items_nitro = [
        ProductItem(product_id=prod_nitro.id, data="https://discord.gift/mwaves-nitro-99882314"),
        ProductItem(product_id=prod_nitro.id, data="https://discord.gift/mwaves-nitro-11294810"),
    ]
    items_steam = [
        ProductItem(product_id=prod_steam.id, data="MWV99-KJA82-7719B"),
        ProductItem(product_id=prod_steam.id, data="MWV88-LLZ91-4401X"),
        ProductItem(product_id=prod_steam.id, data="MWV12-QQM34-9981Y"),
    ]
    session.add_all(items_nitro + items_steam)

    await session.commit()
    logger.info("Каталог @mwavesrobot успешно наполнен товарами и складом!")
