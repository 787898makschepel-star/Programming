from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ─────────────────────────────────────────────
#  Тексты кнопок — константы для единой точки
#  обращения в хэндлерах
# ─────────────────────────────────────────────

BTN_ADM_PANEL     = "🛠 Панель управления"
BTN_ADM_USERS     = "👥 Пользователи"
BTN_ADM_STATS     = "📊 Статистика"
BTN_ADM_BROADCAST = "📢 Рассылка"
BTN_ADM_CITIES    = "🏙️ Города"
BTN_ADM_SHOWCASE  = "🛍️ Товары"
BTN_ADM_SETTINGS  = "⚙️ Настройки"
BTN_ADM_MAIN_MENU = "◀️ В клиентское меню"


def get_admin_reply_kb() -> ReplyKeyboardMarkup:
    """
    Красивая постоянная Reply-клавиатура для администраторов.

    Раскладка:
        [ 🛠 Панель управления ]
        [ 👥 Пользователи ]  [ 📊 Статистика ]
        [ 📢 Рассылка    ]  [ 🏙️ Города      ]
        [ 🛍️ Товары      ]  [ ⚙️ Настройки   ]
        [ ◀️ В клиентское меню ]
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ADM_PANEL)],
            [
                KeyboardButton(text=BTN_ADM_USERS),
                KeyboardButton(text=BTN_ADM_STATS),
            ],
            [
                KeyboardButton(text=BTN_ADM_BROADCAST),
                KeyboardButton(text=BTN_ADM_CITIES),
            ],
            [
                KeyboardButton(text=BTN_ADM_SHOWCASE),
                KeyboardButton(text=BTN_ADM_SETTINGS),
            ],
            [KeyboardButton(text=BTN_ADM_MAIN_MENU)],
        ],
        resize_keyboard=True,
        persistent=True,
        input_field_placeholder="Выберите раздел...",
    )
