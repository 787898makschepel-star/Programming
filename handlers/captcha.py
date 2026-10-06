import asyncio
import html
import logging
import random
import time
from typing import Optional, Tuple

from aiogram import Bot, F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    ChatPermissions,
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User as TelegramUser,
)
from sqlalchemy.ext.asyncio import AsyncSession

from config import config, get_receipts_chat_ids
from database.crud import attach_referrer, get_or_create_user
from database.models import User
from states.client_states import CaptchaState, CityState
from utils.formatters import DIVIDER

logger = logging.getLogger(__name__)
router = Router(name="math_captcha")

ADMIN_BAN_PREFIX = "captcha_admin_ban:"
LEGACY_BAN_PREFIX = "ec_admin_ban:"
CAPTCHA_COOLDOWN_SECONDS = 300  # 5 минут после 3 неудачных попыток


def generate_math_problem() -> Tuple[str, int]:
    """
    Генерирует простой математический пример:
    1) Сложение (+): A (1..9) + B (1..9) -> результат (2..18)
    2) Вычитание (−): A (2..9) − B (1..A-1) -> результат (1..8)
    Оба операнда являются однозначными цифрами от 1 до 9.
    """
    op = random.choice(["+", "-"])
    if op == "+":
        a = random.randint(1, 9)
        b = random.randint(1, 9)
        return f"{a} + {b}", a + b
    else:
        a = random.randint(2, 9)
        b = random.randint(1, a - 1)
        return f"{a} - {b}", a - b


def _mention_html(user_id: int, full_name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{html.escape(full_name or "пользователь")}</a>'


async def _safe_delete(bot: Bot, chat_id: int, message_id: Optional[int]) -> None:
    if not message_id:
        return
    try:
        await bot.delete_message(chat_id, message_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        pass
    except Exception:
        pass


async def _notify_admin_group(
    bot: Bot,
    chat_id: int,
    user: TelegramUser,
    attempts: int,
) -> None:
    username = f"@{user.username}" if user.username else "не указан"
    user_type = "бот" if user.is_bot else "пользователь"
    text = (
        "⚠️ <b>Пользователь не прошёл проверку</b>\n"
        f"{DIVIDER}\n"
        f"Тип: <b>{user_type}</b>\n"
        f"Имя: <b>{html.escape(user.full_name or 'не указано')}</b>\n"
        f"Username: <b>{html.escape(username)}</b>\n"
        f"Telegram ID: <code>{user.id}</code>\n"
        f"Чат ID: <code>{chat_id}</code>\n"
        f"Ошибок: <b>{attempts}</b>"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🚫 Заблокировать",
            callback_data=f"{ADMIN_BAN_PREFIX}{chat_id}:{user.id}",
        )
    ]])
    for admin_chat_id in get_receipts_chat_ids():
        try:
            await bot.send_message(
                chat_id=admin_chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            return
        except (TelegramBadRequest, TelegramForbiddenError) as error:
            logger.warning("Failed to notify admin group %s: %s", admin_chat_id, error)


async def send_math_captcha(
    bot: Bot,
    chat_id: int,
    user: User,
    state: FSMContext,
    reset_attempts: bool = True,
) -> None:
    """
    Отправляет простой математический пример для подтверждения.
    """
    data = await state.get_data()

    # Проверка временного кулдауна после 3 ошибок
    cooldown_until = data.get("cooldown_until", 0)
    now = time.time()
    if cooldown_until > now:
        remaining_mins = max(1, int((cooldown_until - now) // 60 + 1))
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "⏳ <b>Доступ временно ограничен</b>\n\n"
                f"Вы исчерпали лимит попыток. Подождите <b>{remaining_mins} мин.</b> и отправьте команду /start."
            ),
            parse_mode="HTML",
        )
        return

    # Удаляем предыдущее сообщение с капчей, если было
    old_msg_id = data.get("captcha_msg_id")
    if old_msg_id:
        await _safe_delete(bot, chat_id, old_msg_id)

    attempts = 3 if reset_attempts else data.get("captcha_attempts", 3)
    problem_text, answer = generate_math_problem()

    msg = await bot.send_message(
        chat_id=chat_id,
        text=(
            "🔐 <b>Подтверждение</b>\n\n"
            f"Решите пример: <b>{problem_text} = ?</b>\n"
            "<i>Отправьте ответ числом</i>"
        ),
        parse_mode="HTML",
        reply_markup=ForceReply(
            input_field_placeholder="Введите ответ...",
            selective=True,
        ),
    )

    await state.set_state(CaptchaState.waiting_for_answer)
    await state.update_data(
        captcha_answer=answer,
        captcha_problem=problem_text,
        captcha_attempts=attempts,
        captcha_msg_id=msg.message_id,
        captcha_created_at=now,
    )


# Алиас для обратной совместимости
send_start_captcha = send_math_captcha


@router.message(CaptchaState.waiting_for_answer)
async def handle_math_captcha_answer(
    message: Message,
    bot: Bot,
    session: AsyncSession,
    db_user: User,
    state: FSMContext,
) -> None:
    """
    Обрабатывает ввод ответа на пример.
    После успешного решения сообщение капчи и ответ пользователя удаляются.
    """
    data = await state.get_data()
    correct_answer = data.get("captcha_answer")
    attempts = data.get("captcha_attempts", 3)
    captcha_msg_id = data.get("captcha_msg_id")
    chat_id = message.chat.id
    raw_text = (message.text or "").strip().rstrip(".!?,")

    # Удаляем сообщение с ответом пользователя для чистоты чата
    await _safe_delete(bot, chat_id, message.message_id)

    # Проверка кулдауна
    cooldown_until = data.get("cooldown_until", 0)
    now = time.time()
    if cooldown_until > now:
        remaining_mins = max(1, int((cooldown_until - now) // 60 + 1))
        await _safe_delete(bot, chat_id, captcha_msg_id)
        msg = await bot.send_message(
            chat_id=chat_id,
            text=(
                "⏳ <b>Доступ временно ограничен</b>\n\n"
                f"Подождите <b>{remaining_mins} мин.</b> и отправьте команду /start."
            ),
            parse_mode="HTML",
        )
        await state.update_data(captcha_msg_id=msg.message_id)
        return

    # Если вдруг сессия FSM пустая (бот перезагружался)
    if correct_answer is None:
        await send_math_captcha(bot, chat_id, db_user, state, reset_attempts=True)
        return

    # Проверка на числовой ввод
    try:
        user_answer = int(raw_text)
    except ValueError:
        await _safe_delete(bot, chat_id, captcha_msg_id)
        problem_text = data.get("captcha_problem") or "0 + 0"
        err_msg = await bot.send_message(
            chat_id=chat_id,
            text=(
                "⚠️ <b>Отправьте ответ числом</b>\n\n"
                f"Решите пример: <b>{problem_text} = ?</b>\n"
                f"<i>Осталось попыток: {attempts}</i>"
            ),
            parse_mode="HTML",
            reply_markup=ForceReply(
                input_field_placeholder="Введите ответ...",
                selective=True,
            ),
        )
        await state.update_data(captcha_msg_id=err_msg.message_id)
        return

    # 1. ПРАВИЛЬНЫЙ ОТВЕТ
    if user_answer == correct_answer:
        db_user.captcha_passed = True
        db_user.start_pending = False
        db_user.city = ""
        db_user.district = None

        # Начисление реферала, если был переход по реф-ссылке
        pending_ref = data.get("pending_referrer_id")
        if pending_ref:
            await attach_referrer(session, db_user, int(pending_ref))

        await session.commit()

        # Полностью удаляем сообщение капчи из чата (после прохождения капчи текст убираем)
        await _safe_delete(bot, chat_id, captcha_msg_id)
        await state.clear()

        # Всегда переходим к обязательному ручному вводу города
        await state.set_state(CityState.waiting_for_city)
        await state.update_data(onboarding_after_captcha=True)
        city_msg = await bot.send_message(
            chat_id=chat_id,
            text=(
                "📍 <b>Укажите ваш город</b>\n\n"
                "Напишите свой город, чтобы продолжить."
            ),
            parse_mode="HTML",
            reply_markup=ForceReply(
                input_field_placeholder="Напишите свой город",
                selective=True,
            ),
        )
        await state.update_data(city_prompt_msg_id=city_msg.message_id)
        return

    # 2. НЕПРАВИЛЬНЫЙ ОТВЕТ
    attempts -= 1
    await _safe_delete(bot, chat_id, captcha_msg_id)

    if attempts > 0:
        new_problem, new_answer = generate_math_problem()
        new_msg = await bot.send_message(
            chat_id=chat_id,
            text=(
                "❌ <b>Неверно, попробуйте ещё раз</b>\n\n"
                f"Решите пример: <b>{new_problem} = ?</b>\n"
                f"<i>Осталось попыток: {attempts}</i>"
            ),
            parse_mode="HTML",
            reply_markup=ForceReply(
                input_field_placeholder="Введите ответ...",
                selective=True,
            ),
        )
        await state.update_data(
            captcha_answer=new_answer,
            captcha_problem=new_problem,
            captcha_attempts=attempts,
            captcha_msg_id=new_msg.message_id,
        )
        return

    # 3. ИСЧЕРПАНЫ ВСЕ 3 ПОПЫТКИ
    cooldown_until = now + CAPTCHA_COOLDOWN_SECONDS
    await state.update_data(cooldown_until=cooldown_until, captcha_attempts=0, captcha_msg_id=None)

    await bot.send_message(
        chat_id=chat_id,
        text=(
            "⏳ <b>Лимит попыток исчерпан</b>\n\n"
            "Повторите попытку через <b>5 минут</b> (/start)."
        ),
        parse_mode="HTML",
    )

    if message.from_user:
        await _notify_admin_group(bot, chat_id, message.from_user, attempts=3)


# ============================================================
# АДМИНИСТРАТИВНЫЙ БАН ПО КНОПКЕ ИЗ АДМИН-ГРУППЫ
# ============================================================

@router.callback_query(F.data.startswith(ADMIN_BAN_PREFIX))
@router.callback_query(F.data.startswith(LEGACY_BAN_PREFIX))
async def handle_admin_ban(
    callback: CallbackQuery,
    bot: Bot,
    session: AsyncSession,
    db_user: User,
) -> None:
    """Блокирует пользователя по решению администратора из админ-группы."""
    if callback.from_user.id not in config.ADMIN_IDS and not db_user.is_admin:
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    prefix = ADMIN_BAN_PREFIX if callback.data.startswith(ADMIN_BAN_PREFIX) else LEGACY_BAN_PREFIX
    try:
        chat_id_text, user_id_text = callback.data[len(prefix):].split(":", 1)
        chat_id = int(chat_id_text)
        user_id = int(user_id_text)
    except (AttributeError, ValueError):
        await callback.answer("Некорректные данные блокировки.", show_alert=True)
        return

    target_user, _ = await get_or_create_user(session, tg_id=user_id)
    target_user.is_banned = True
    await session.commit()

    if chat_id != user_id:
        try:
            await bot.ban_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                revoke_messages=True,
            )
        except (TelegramBadRequest, TelegramForbiddenError):
            logger.exception("Failed to ban user %s from chat %s", user_id, chat_id)
            await callback.answer(
                "Пользователь заблокирован в боте, но не в группе.",
                show_alert=True,
            )
            return

    await callback.answer("Пользователь заблокирован в боте.")
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)


# ============================================================
# ДЛЯ ГРУППОВЫХ ЧАТОВ (если бот добавлен в супергруппу)
# ============================================================

def _restricted_permissions() -> ChatPermissions:
    return ChatPermissions(
        can_send_messages=False,
        can_send_audios=False,
        can_send_documents=False,
        can_send_photos=False,
        can_send_videos=False,
        can_send_video_notes=False,
        can_send_voice_notes=False,
        can_send_polls=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False,
        can_change_info=False,
        can_invite_users=False,
        can_pin_messages=False,
        can_manage_topics=False,
    )


def _member_permissions() -> ChatPermissions:
    return ChatPermissions(
        can_send_messages=True,
        can_send_audios=True,
        can_send_documents=True,
        can_send_photos=True,
        can_send_videos=True,
        can_send_video_notes=True,
        can_send_voice_notes=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
        can_change_info=False,
        can_invite_users=True,
        can_pin_messages=False,
        can_manage_topics=False,
    )


def _is_new_member(event: ChatMemberUpdated) -> bool:
    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status
    return (
        event.chat.type in {ChatType.GROUP, ChatType.SUPERGROUP}
        and new_status in {ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED}
        and old_status not in {ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED}
    )


@router.chat_member()
async def handle_new_member(event: ChatMemberUpdated, bot: Bot) -> None:
    """Ограничивает нового участника группы и предлагает верифицироваться в боте."""
    if not _is_new_member(event):
        return

    user = event.new_chat_member.user
    try:
        await bot.restrict_chat_member(
            chat_id=event.chat.id,
            user_id=user.id,
            permissions=_restricted_permissions(),
        )
    except (TelegramBadRequest, TelegramForbiddenError):
        logger.exception("Failed to restrict new member %s", user.id)
        return

    bot_info = await bot.get_me()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🛡 Пройти проверку в боте",
            url=f"https://t.me/{bot_info.username}?start=group_verify",
        )
    ]])
    try:
        await bot.send_message(
            chat_id=event.chat.id,
            text=(
                f"Привет, {_mention_html(user.id, user.full_name)}!\n"
                "Чтобы писать в чате, подтвердите, что вы человек, в личном диалоге с ботом."
            ),
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except (TelegramBadRequest, TelegramForbiddenError):
        pass


__all__ = [
    "router",
    "send_math_captcha",
    "send_start_captcha",
    "generate_math_problem",
]
