import asyncio
import html
import logging
import random
import secrets
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

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
    User as TelegramUser,
)
from sqlalchemy.ext.asyncio import AsyncSession

from config import config, get_receipts_chat_ids
from database.crud import get_or_create_user
from database.models import User
from states.client_states import CityState
from utils.formatters import DIVIDER

logger = logging.getLogger(__name__)
router = Router(name="emoji_captcha")

CAPTCHA_TIMEOUT = 60
CALLBACK_PREFIX = "ec_"
START_CALLBACK_PREFIX = "esc_"
ADMIN_BAN_PREFIX = "ec_admin_ban:"

EMOJI_NAMES = {
    "🍎": "яблоко",
    "🚗": "машина",
    "☂️": "зонт",
    "🐱": "кошка",
    "🐶": "собака",
    "🍕": "пицца",
    "⚽": "мяч",
    "✈️": "самолёт",
    "🌞": "солнце",
    "📚": "книги",
    "🎸": "гитара",
    "🚲": "велосипед",
}

ChallengeKey = Tuple[int, int]


@dataclass
class CaptchaChallenge:
    chat_id: int
    user_id: int
    message_id: int
    correct_token: str
    choices: Dict[str, str]
    expiry_task: Optional[asyncio.Task] = field(default=None, repr=False)


challenges: Dict[ChallengeKey, CaptchaChallenge] = {}
start_challenges: Dict[ChallengeKey, CaptchaChallenge] = {}
failed_attempts: Dict[ChallengeKey, int] = {}
start_failed_attempts: Dict[ChallengeKey, int] = {}


def _key(chat_id: int, user_id: int) -> ChallengeKey:
    return chat_id, user_id


def _mention_html(user_id: int, full_name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{html.escape(full_name or "пользователь")}</a>'


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


async def _delete_captcha_message(bot: Bot, challenge: CaptchaChallenge) -> None:
    try:
        await bot.delete_message(challenge.chat_id, challenge.message_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        logger.debug("Captcha message %s is already unavailable", challenge.message_id)


def _cancel_expiry(challenge: CaptchaChallenge) -> None:
    if challenge.expiry_task and not challenge.expiry_task.done():
        challenge.expiry_task.cancel()


def _build_captcha_buttons(prefix: str) -> Tuple[list, Dict[str, str], str]:
    selected_emojis = random.sample(list(EMOJI_NAMES), 4)
    choices: Dict[str, str] = {}
    buttons = []
    for emoji in selected_emojis:
        token = secrets.token_urlsafe(18)
        choices[token] = emoji
        buttons.append(InlineKeyboardButton(text=emoji, callback_data=f"{prefix}{token}"))
    correct_token = next(token for token, emoji in choices.items() if emoji == selected_emojis[0])
    random.shuffle(buttons)
    correct_button = next(
        button for button in buttons
        if button.callback_data == f"{prefix}{correct_token}"
    )
    buttons.remove(correct_button)
    buttons.insert(random.choice((1, 2)), correct_button)
    return buttons, choices, correct_token


async def _send_group_captcha(bot: Bot, chat_id: int, user: TelegramUser) -> None:
    buttons, choices, correct_token = _build_captcha_buttons(CALLBACK_PREFIX)
    correct_emoji = choices[correct_token]
    user_id = user.id
    mention = _mention_html(user_id, user.full_name)
    text = (
        f"Привет, {mention}! Чтобы получить возможность писать в чат, "
        f"нажми на <b>{html.escape(EMOJI_NAMES[correct_emoji])}</b> "
        f"в течение {CAPTCHA_TIMEOUT} секунд."
    )
    message = await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[buttons]),
    )
    key = _key(chat_id, user_id)
    challenge = CaptchaChallenge(
        chat_id=chat_id,
        user_id=user_id,
        message_id=message.message_id,
        correct_token=correct_token,
        choices=choices,
    )
    challenges[key] = challenge
    challenge.expiry_task = asyncio.create_task(
        _expire_challenge(bot, key, correct_token)
    )


async def _notify_admin_group(
    bot: Bot,
    challenge: CaptchaChallenge,
    user: TelegramUser,
    attempts: int,
) -> None:
    username = f"@{user.username}" if user.username else "не указан"
    user_type = "бот" if user.is_bot else "пользователь"
    text = (
        "⚠️ <b>Пользователь не прошёл капчу</b>\n"
        f"{DIVIDER}\n"
        f"Тип: <b>{user_type}</b>\n"
        f"Имя: <b>{html.escape(user.full_name or 'не указано')}</b>\n"
        f"Username: <b>{html.escape(username)}</b>\n"
        f"Telegram ID: <code>{user.id}</code>\n"
        f"Чат ID: <code>{challenge.chat_id}</code>\n"
        f"Название чата: <b>{html.escape(str(challenge.chat_id))}</b>\n"
        f"Ошибок капчи: <b>{attempts}</b>"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🚫 Заблокировать пользователя",
            callback_data=f"{ADMIN_BAN_PREFIX}{challenge.chat_id}:{user.id}",
        )
    ]])
    for chat_id in get_receipts_chat_ids():
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            logger.info(
                "Captcha failure notification sent to admin group %s for user %s",
                chat_id,
                user.id,
            )
            return
        except (TelegramBadRequest, TelegramForbiddenError) as error:
            logger.warning(
                "Failed to notify admin group %s about user %s: %s",
                chat_id,
                user.id,
                error,
            )

    logger.error("Could not notify any configured admin group about user %s", user.id)


async def _notify_user_about_failed_captcha(bot: Bot, user_id: int) -> None:
    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "❌ Вы три раза ввели неправильный ответ капчи. "
                "Администратор получил уведомление о попытке входа."
            ),
        )
    except (TelegramBadRequest, TelegramForbiddenError):
        logger.debug("Failed to notify user %s about failed captcha", user_id)


async def send_start_captcha(
    bot: Bot,
    chat_id: int,
    user: User,
    reset_attempts: bool = True,
) -> None:
    """Отправляет капчу после второго /start в личном чате."""
    key = _key(chat_id, user.tg_id)
    previous = start_challenges.pop(key, None)
    if previous:
        _cancel_expiry(previous)
        await _delete_captcha_message(bot, previous)
    if reset_attempts:
        start_failed_attempts.pop(key, None)

    buttons, choices, correct_token = _build_captcha_buttons(START_CALLBACK_PREFIX)
    message = await bot.send_message(
        chat_id=chat_id,
        text=(
            f"Привет, {_mention_html(user.tg_id, user.full_name)}! Для входа в бота "
            f"нажми на <b>{html.escape(EMOJI_NAMES[choices[correct_token]])}</b> "
            f"в течение {CAPTCHA_TIMEOUT} секунд."
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[buttons]),
    )
    challenge = CaptchaChallenge(
        chat_id=chat_id,
        user_id=user.tg_id,
        message_id=message.message_id,
        correct_token=correct_token,
        choices=choices,
    )
    start_challenges[key] = challenge
    challenge.expiry_task = asyncio.create_task(
        _expire_start_challenge(bot, key, correct_token)
    )


async def _expire_start_challenge(bot: Bot, key: ChallengeKey, token: str) -> None:
    try:
        await asyncio.sleep(CAPTCHA_TIMEOUT)
    except asyncio.CancelledError:
        return

    challenge = start_challenges.get(key)
    if not challenge or challenge.correct_token != token:
        return
    start_challenges.pop(key, None)
    start_failed_attempts.pop(key, None)
    await _delete_captcha_message(bot, challenge)


@router.callback_query(F.data.startswith(START_CALLBACK_PREFIX))
async def handle_start_captcha_answer(
    callback: CallbackQuery,
    bot: Bot,
    session: AsyncSession,
    db_user: User,
    state: FSMContext,
) -> None:
    if not callback.message:
        await callback.answer("Капча больше недоступна.", show_alert=True)
        return

    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    token = callback.data[len(START_CALLBACK_PREFIX):]
    challenge = next(
        (item for item in start_challenges.values() if token in item.choices),
        None,
    )
    if not challenge:
        await callback.answer("Капча больше недоступна.", show_alert=True)
        return
    if user_id != challenge.user_id or chat_id != challenge.chat_id:
        await callback.answer("Это не ваша капча", show_alert=True)
        return

    key = _key(chat_id, user_id)
    start_challenges.pop(key, None)
    _cancel_expiry(challenge)

    if token != challenge.correct_token:
        await _delete_captcha_message(bot, challenge)
        attempts = start_failed_attempts.get(key, 0) + 1
        start_failed_attempts[key] = attempts
        if attempts < 3:
            await callback.answer(
                f"Неверный ответ. Попытка {attempts} из 3. Попробуйте ещё раз.",
                show_alert=True,
            )
            await send_start_captcha(
                bot,
                chat_id,
                db_user,
                reset_attempts=False,
            )
            return

        start_failed_attempts.pop(key, None)
        await callback.answer(
            "Три ошибки. Администраторы получили уведомление.",
            show_alert=True,
        )
        await _notify_user_about_failed_captcha(bot, user_id)
        await _notify_admin_group(bot, challenge, callback.from_user, attempts)
        return

    start_failed_attempts.pop(key, None)
    db_user.captcha_passed = True
    db_user.start_pending = False
    await session.commit()
    await callback.answer("Капча пройдена!")
    await _delete_captcha_message(bot, challenge)
    await state.clear()
    await state.set_state(CityState.waiting_for_city)
    await state.update_data(onboarding_after_captcha=True)
    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"📍 <b>Капча пройдена!</b>\n{DIVIDER}\n"
            "Напишите свой город, чтобы продолжить."
        ),
        parse_mode="HTML",
        reply_markup=ForceReply(
            input_field_placeholder="Напишите свой город",
            selective=True,
        ),
    )


async def _expire_challenge(bot: Bot, key: ChallengeKey, token: str) -> None:
    try:
        await asyncio.sleep(CAPTCHA_TIMEOUT)
    except asyncio.CancelledError:
        return

    challenge = challenges.get(key)
    if not challenge or challenge.correct_token != token:
        return

    challenges.pop(key, None)
    failed_attempts.pop(key, None)
    await _delete_captcha_message(bot, challenge)
    try:
        await bot.ban_chat_member(
            chat_id=challenge.chat_id,
            user_id=challenge.user_id,
            revoke_messages=True,
        )
        await bot.unban_chat_member(
            chat_id=challenge.chat_id,
            user_id=challenge.user_id,
            only_if_banned=True,
        )
        logger.info("User %s was removed after captcha timeout", challenge.user_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        logger.exception("Failed to remove user %s after captcha timeout", challenge.user_id)


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
    if not _is_new_member(event):
        return

    user = event.new_chat_member.user
    key = _key(event.chat.id, user.id)
    previous = challenges.pop(key, None)
    if previous:
        _cancel_expiry(previous)
        await _delete_captcha_message(bot, previous)

    try:
        await bot.restrict_chat_member(
            chat_id=event.chat.id,
            user_id=user.id,
            permissions=_restricted_permissions(),
        )
    except (TelegramBadRequest, TelegramForbiddenError):
        logger.exception("Failed to restrict new member %s", user.id)
        return

    try:
        failed_attempts.pop(key, None)
        await _send_group_captcha(bot, event.chat.id, user)
    except (TelegramBadRequest, TelegramForbiddenError):
        logger.exception("Failed to send captcha for user %s", user.id)
        return


@router.callback_query(F.data.startswith(ADMIN_BAN_PREFIX))
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

    try:
        chat_id_text, user_id_text = callback.data[len(ADMIN_BAN_PREFIX):].split(":", 1)
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


@router.callback_query(F.data.startswith(CALLBACK_PREFIX))
async def handle_captcha_answer(callback: CallbackQuery, bot: Bot) -> None:
    if not callback.message:
        await callback.answer("Капча больше недоступна.", show_alert=True)
        return

    chat_id = callback.message.chat.id
    user_id = callback.from_user.id
    token = callback.data[len(CALLBACK_PREFIX):]
    challenge = next(
        (item for item in challenges.values() if token in item.choices),
        None,
    )

    if not challenge:
        await callback.answer("Капча больше недоступна.", show_alert=True)
        return

    if user_id != challenge.user_id or chat_id != challenge.chat_id:
        await callback.answer("Это не ваша капча", show_alert=True)
        return

    key = _key(chat_id, user_id)

    challenges.pop(key, None)
    _cancel_expiry(challenge)

    if token == challenge.correct_token:
        try:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=_member_permissions(),
            )
            await callback.answer("Готово! Теперь вы можете писать в чат.")
            await _delete_captcha_message(bot, challenge)
        except (TelegramBadRequest, TelegramForbiddenError):
            logger.exception("Failed to unrestrict user %s", user_id)
            await callback.answer("Не удалось снять ограничения. Обратитесь к администратору.", show_alert=True)
        return

    attempts = failed_attempts.get(key, 0) + 1
    failed_attempts[key] = attempts
    await _delete_captcha_message(bot, challenge)
    if attempts < 3:
        await callback.answer(
            f"Неверный ответ. Попытка {attempts} из 3. Попробуйте ещё раз.",
            show_alert=True,
        )
        try:
            await _send_group_captcha(bot, chat_id, callback.from_user)
        except (TelegramBadRequest, TelegramForbiddenError):
            logger.exception("Failed to resend captcha for user %s", user_id)
        return

    failed_attempts.pop(key, None)
    await callback.answer(
        "Три ошибки. Администраторы получили уведомление.",
        show_alert=True,
    )
    await _notify_user_about_failed_captcha(bot, user_id)
    await _notify_admin_group(bot, challenge, callback.from_user, attempts)


__all__ = ["router"]
