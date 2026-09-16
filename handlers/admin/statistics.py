from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import get_analytics_stats, get_top_products
from keyboards.inline_admin import get_stats_period_kb
from utils.ui_cleaner import send_or_edit_screen
from utils.formatters import format_admin_stats, DIVIDER

router = Router(name="admin_statistics")


@router.callback_query(F.data == "adm_stats")
async def show_stats_menu(call: CallbackQuery, state: FSMContext):
    """Выбор периода для аналитики."""
    text = (
        f"📊 <b>Статистика и аналитика продаж</b>\n"
        f"{DIVIDER}\n"
        f"Выберите временной период для формирования сводки:"
    )
    await send_or_edit_screen(call, text, reply_markup=get_stats_period_kb(), state=state)
    await call.answer()


@router.callback_query(F.data.startswith("stat_"))
async def show_stats_period(call: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Отображение показателей за выбранный период в том же окне."""
    period_code = call.data.replace("stat_", "")
    period_titles = {
        "today": "за сегодня",
        "week": "за 7 дней",
        "all": "за все время"
    }
    period_title = period_titles.get(period_code, "за период")

    stats = await get_analytics_stats(session, period=period_code)
    top_products = await get_top_products(session, limit=5)

    report = format_admin_stats(stats, top_products, period_title)
    await send_or_edit_screen(call, report, reply_markup=get_stats_period_kb(), state=state)
    await call.answer()
