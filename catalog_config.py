"""
╔══════════════════════════════════════════════════════════════════════╗
║                    🍬 КАТАЛОГ ТОВАРОВ ВИТРИНЫ                       ║
║                                                                      ║
║  Редактируйте товары прямо здесь — название, картинку, цену,        ║
║  единицу измерения и минимальный заказ.                              ║
║                                                                      ║
║  После изменений перезапустите бота — каталог обновится автоматически║
╚══════════════════════════════════════════════════════════════════════╝

Формат каждого товара:
{
    "title":          "Название товара",        # Отображается в кнопке и карточке
    "price":          1680,                     # Цена за минимальный заказ (в рублях)
    "unit":           "шт." или "г",            # Единица измерения
    "min_quantity":   3,                        # Минимальное количество для заказа
                                                #   - для "шт." минимум 3
                                                #   - для "г" минимум 0.5 (шаг 0.5)
    "image":          "assets/photo.jpg",       # Путь к картинке (или None)
                                                #   Положите файл в папку assets/
                                                #   и укажите путь здесь
}
"""

# ──────────────────────────────────────────────
# 📦 СПИСОК ТОВАРОВ ВИТРИНЫ
# ──────────────────────────────────────────────
# Добавляйте, удаляйте и редактируйте товары.
# Порядок в списке = порядок кнопок в боте.

SHOWCASE_PRODUCTS = [
    {
        "title": "Амфетамин Айсберг (HQ)",
        "price": 1140,
        "unit": "г.",            # "шт." или "г"
        "min_quantity": 0.5,        # минимальный заказ
        "image": "assets/catalog/01_iceberg.jpg",
    },
    {
        "title": "Мефедрон кристаллы VHQ",
        "price": 1290,
        "unit": "г.",
        "min_quantity": 0.5,
        "image": "assets/catalog/02_mephedrone.jpg",
    },
    {
        "title": "Кокаин CR7 (VHQ)",
        "price": 12490,
        "unit": "г.",
        "min_quantity": 0.5,
        "image": "assets/catalog/03_cocaine_cr7.jpg",
    },
    {
        "title": "ШШ: Lemon OG Haze",
        "price": 3560,
        "unit": "г.",
        "min_quantity": 2.0,
        "image": "assets/catalog/04_lemon_og_haze.jpg",
    },
    {
        "title": "ШШ: OG Kush",
        "price": 3360,
        "unit": "г.",
        "min_quantity": 2.0,
        "image": "assets/catalog/05_og_kush.jpg",
    },
    {
        "title": "ШШ: Bruce Banner",
        "price": 3560,
        "unit": "г.",
        "min_quantity": 2.0,
        "image": "assets/catalog/06_bruce_banner.jpg",
    },
    {
        "title": "Гашиш КТМА",
        "price": 3360,
        "unit": "г.",
        "min_quantity": 2.0,
        "image": "assets/catalog/07_gashish_ktma.jpg",
    },
    {
        "title": "Грибы Pink Buffalo",
        "price": 2900,
        "unit": "г.",
        "min_quantity": 5.0,
        "image": "assets/catalog/08_pink_buffalo.jpg",
    },
    {
        "title": "Грибы Cambodian gold",
        "price": 2400,
        "unit": "г.",
        "min_quantity": 5.0,
        "image": "assets/catalog/09_cambodian_gold.jpg",
    },
    {
        "title": "Грибы Thai",
        "price": 3900,
        "unit": "г.",
        "min_quantity": 5.0,
        "image": "assets/catalog/10_thai.jpg",
    },
    {
        "title": "Экстази Red Bull",
        "price": 2940,
        "unit": "шт.",
        "min_quantity": 3,
        "image": "assets/catalog/11_red_bull.jpg",
    },
    {
        "title": "Punisher Blue - 300mg",
        "price": 3160,
        "unit": "шт.",
        "min_quantity": 3,
        "image": "assets/catalog/12_punisher_blue.jpg",
    },
    {
        "title": "Pharaon - 240mg",
        "price": 5040,
        "unit": "шт.",
        "min_quantity": 3,
        "image": "assets/catalog/13_pharaon.jpg",
    },
    {
        "title": "Anonymous - 310mg",
        "price": 5040,
        "unit": "шт.",
        "min_quantity": 3,
        "image": "assets/catalog/14_anonymous.jpg",
    },
    {
        "title": "Anonymous 2.0 - 310mg",
        "price": 5040,
        "unit": "шт.",
        "min_quantity": 3,
        "image": "assets/catalog/15_anonymous_2.jpg",
    },
    {
        "title": "La Casa De Papel - 320mg",
        "price": 5040,
        "unit": "шт.",
        "min_quantity": 3,
        "image": "assets/catalog/16_la_casa_de_papel.jpg",
    },
]
