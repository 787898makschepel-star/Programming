import logging
import os
from typing import Optional, Union
from aiogram import Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InputMediaPhoto, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)

LAST_SCREEN_KEY = "last_screen_message_id"


async def delete_user_message(message: Optional[Message]) -> bool:
    """
    Безопасное удаление входящего сообщения пользователя для поддержания чистоты чата.
    """
    if not message:
        return False
    try:
        await message.delete()
        return True
    except TelegramBadRequest as e:
        logger.debug(f"Не удалось удалить входящее сообщение {message.message_id}: {e}")
        return False
    except Exception as e:
        logger.debug(f"Ошибка при удалении сообщения: {e}")
        return False


async def clear_previous_screen(
    bot: Bot,
    chat_id: int,
    state: Optional[FSMContext] = None,
    explicit_message_id: Optional[int] = None
) -> None:
    """
    Удаляет предыдущее активное окно (экран) бота.
    """
    target_id = explicit_message_id

    if not target_id and state:
        state_data = await state.get_data()
        target_id = state_data.get(LAST_SCREEN_KEY)

    if target_id:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=target_id)
        except TelegramBadRequest:
            pass  # Сообщение уже удалено пользователем или старше 48 часов
        except Exception as e:
            logger.debug(f"Ошибка при очистке старого экрана: {e}")

        if state:
            await state.update_data({LAST_SCREEN_KEY: None})


async def send_or_edit_screen(
    event: Union[Message, CallbackQuery],
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    photo: Optional[Union[str, FSInputFile]] = None,
    state: Optional[FSMContext] = None,
    bot: Optional[Bot] = None,
    force_new: bool = False
) -> Message:
    """
    Универсальный менеджер отображения экрана с поддержкой фото-баннеров и текста.
    """
    if isinstance(event, CallbackQuery):
        active_bot = bot or event.bot
        chat_id = event.message.chat.id if event.message else event.from_user.id
        current_msg: Optional[Message] = event.message
    else:
        active_bot = bot or event.bot
        chat_id = event.chat.id
        current_msg = None

    # Попытка редактирования существующего сообщения
    if isinstance(event, CallbackQuery) and current_msg and not force_new:
        try:
            # 1. Если было фото и передали фото -> edit_media или edit_caption
            if photo and current_msg.photo:
                try:
                    edited = await current_msg.edit_media(
                        media=InputMediaPhoto(media=photo, caption=text, parse_mode="HTML"),
                        reply_markup=reply_markup
                    )
                    if state:
                        await state.update_data({LAST_SCREEN_KEY: edited.message_id})
                    return edited
                except Exception:
                    edited = await current_msg.edit_caption(
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=reply_markup
                    )
                    if state:
                        await state.update_data({LAST_SCREEN_KEY: edited.message_id})
                    return edited

            # 2. Если фото нет и сообщение текстовое -> edit_text
            elif not photo and not current_msg.photo:
                edited = await current_msg.edit_text(
                    text=text,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                    disable_web_page_preview=True
                )
                if state:
                    await state.update_data({LAST_SCREEN_KEY: edited.message_id})
                return edited

            # 3. Если тип меняется (текст <-> фото), удаляем старое сообщение
            await clear_previous_screen(
                bot=active_bot,
                chat_id=chat_id,
                explicit_message_id=current_msg.message_id
            )

        except TelegramBadRequest as e:
            err_text = str(e).lower()
            if "message is not modified" in err_text:
                return current_msg
            elif "message to edit not found" in err_text:
                pass
            else:
                logger.debug(f"edit_message exception: {e}")

    # Отправка нового сообщения (после удаления старого)
    await clear_previous_screen(bot=active_bot, chat_id=chat_id, state=state)

    if photo:
        new_msg = await active_bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    else:
        new_msg = await active_bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )

    if state:
        await state.update_data({LAST_SCREEN_KEY: new_msg.message_id})

    return new_msg
