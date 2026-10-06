import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.enums import ChatType
from aiogram.types import Message, CallbackQuery, User as TelegramUser, Chat
from handlers.captcha import generate_math_problem
from middlewares.user_tracker import UserTrackerMiddleware
from database.models import User
from states.client_states import CaptchaState


def test_generate_math_problem_ranges_and_answers():
    """Проверяет корректность генерации простых математических примеров (9-7, 5+5, 3+4)."""
    for _ in range(200):
        problem_str, answer = generate_math_problem()
        assert isinstance(problem_str, str)
        assert isinstance(answer, int)
        assert answer >= 1

        if "+" in problem_str:
            parts = problem_str.split("+")
            a, b = int(parts[0].strip()), int(parts[1].strip())
            assert a + b == answer
            assert 1 <= a <= 9
            assert 1 <= b <= 9
        elif "−" in problem_str or "-" in problem_str:
            clean = problem_str.replace("−", "-")
            parts = clean.split("-")
            a, b = int(parts[0].strip()), int(parts[1].strip())
            assert a - b == answer
            assert 3 <= a <= 10
            assert 1 <= b < a
            assert answer >= 1


def test_middleware_blocks_callback_for_unverified_user():
    """Проверяет, что CallbackQuery полностью блокируются, если капча не пройдена."""
    async def run():
        middleware = UserTrackerMiddleware()
        handler = AsyncMock()

        tg_user = TelegramUser(id=999, is_bot=False, first_name="Test")
        event = MagicMock(spec=CallbackQuery)
        event.from_user = tg_user
        event.answer = AsyncMock()

        db_user = MagicMock(spec=User)
        db_user.is_banned = False
        db_user.is_admin = False
        db_user.captcha_passed = False

        data = {
            "session": AsyncMock(),
            "state": AsyncMock(),
        }

        with patch("middlewares.user_tracker.get_or_create_user", AsyncMock(return_value=(db_user, False))), \
             patch("middlewares.user_tracker.config.ADMIN_IDS", [123]):
            result = await middleware(handler, event, data)

        assert result is None
        handler.assert_not_called()
        event.answer.assert_called_once()
        assert "капчу" in event.answer.call_args[0][0]

    asyncio.run(run())


def test_middleware_blocks_unauthorized_message_for_unverified_user():
    """Проверяет, что обычные команды и сообщения блокируются, если капча не пройдена."""
    async def run():
        middleware = UserTrackerMiddleware()
        handler = AsyncMock()

        tg_user = TelegramUser(id=999, is_bot=False, first_name="Test")
        chat = Chat(id=999, type=ChatType.PRIVATE)
        event = MagicMock(spec=Message)
        event.from_user = tg_user
        event.chat = chat
        event.text = "🍭 Главное меню"
        event.answer = AsyncMock()

        db_user = MagicMock(spec=User)
        db_user.is_banned = False
        db_user.is_admin = False
        db_user.captcha_passed = False

        fsm_state = AsyncMock()
        fsm_state.get_state = AsyncMock(return_value=None)
        data = {
            "session": AsyncMock(),
            "state": fsm_state,
        }

        with patch("middlewares.user_tracker.get_or_create_user", AsyncMock(return_value=(db_user, False))), \
             patch("middlewares.user_tracker.config.ADMIN_IDS", [123]):
            result = await middleware(handler, event, data)

        assert result is None
        handler.assert_not_called()
        event.answer.assert_called_once()
        assert "Доступ к боту ограничен" in event.answer.call_args[0][0]

    asyncio.run(run())


def test_middleware_allows_start_and_captcha_answer():
    """Проверяет, что /start и ответ на капчу в состоянии ожидания пропускаются."""
    async def run():
        middleware = UserTrackerMiddleware()
        handler = AsyncMock(return_value="OK")

        tg_user = TelegramUser(id=999, is_bot=False, first_name="Test")
        chat = Chat(id=999, type=ChatType.PRIVATE)

        db_user = MagicMock(spec=User)
        db_user.is_banned = False
        db_user.is_admin = False
        db_user.captcha_passed = False

        # 1. /start command
        msg_start = MagicMock(spec=Message)
        msg_start.from_user = tg_user
        msg_start.chat = chat
        msg_start.text = "/start"

        data_start = {
            "session": AsyncMock(),
            "state": AsyncMock(),
        }

        with patch("middlewares.user_tracker.get_or_create_user", AsyncMock(return_value=(db_user, False))), \
             patch("middlewares.user_tracker.config.ADMIN_IDS", [123]):
            res_start = await middleware(handler, msg_start, data_start)

        assert res_start == "OK"
        handler.assert_called_once()
        handler.reset_mock()

        # 2. Captcha answer in state
        msg_answer = MagicMock(spec=Message)
        msg_answer.from_user = tg_user
        msg_answer.chat = chat
        msg_answer.text = "42"

        fsm_waiting = AsyncMock()
        fsm_waiting.get_state = AsyncMock(return_value=CaptchaState.waiting_for_answer.state)
        data_answer = {
            "session": AsyncMock(),
            "state": fsm_waiting,
        }

        with patch("middlewares.user_tracker.get_or_create_user", AsyncMock(return_value=(db_user, False))), \
             patch("middlewares.user_tracker.config.ADMIN_IDS", [123]):
            res_answer = await middleware(handler, msg_answer, data_answer)

        assert res_answer == "OK"
        handler.assert_called_once()

    asyncio.run(run())


def test_middleware_allows_verified_user():
    """Проверяет, что верифицированный пользователь свободно пользуется ботом."""
    async def run():
        middleware = UserTrackerMiddleware()
        handler = AsyncMock(return_value="PASSED")

        tg_user = TelegramUser(id=999, is_bot=False, first_name="Test")
        chat = Chat(id=999, type=ChatType.PRIVATE)
        msg = MagicMock(spec=Message)
        msg.from_user = tg_user
        msg.chat = chat
        msg.text = "🛒 Каталог"

        db_user = MagicMock(spec=User)
        db_user.is_banned = False
        db_user.is_admin = False
        db_user.captcha_passed = True

        data = {
            "session": AsyncMock(),
            "state": AsyncMock(),
        }

        with patch("middlewares.user_tracker.get_or_create_user", AsyncMock(return_value=(db_user, False))), \
             patch("middlewares.user_tracker.config.ADMIN_IDS", [123]):
            res = await middleware(handler, msg, data)

        assert res == "PASSED"
        handler.assert_called_once()

    asyncio.run(run())


def test_handle_math_captcha_correct_answer_cleans_up_and_verifies():
    """Проверяет, что правильный ответ удаляет сообщение капчи, верифицирует пользователя и переходит далее."""
    async def run():
        from handlers.captcha import handle_math_captcha_answer
        from states.client_states import CityState

        bot = AsyncMock()
        session = AsyncMock()
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={
            "captcha_answer": 10,
            "captcha_attempts": 3,
            "captcha_msg_id": 555,
        })

        db_user = MagicMock(spec=User)
        db_user.captcha_passed = False
        db_user.start_pending = True
        db_user.city = None

        msg = AsyncMock(spec=Message)
        msg.chat = Chat(id=777, type=ChatType.PRIVATE)
        msg.message_id = 1001
        msg.text = "10"
        msg.from_user = TelegramUser(id=777, is_bot=False, first_name="Test")

        await handle_math_captcha_answer(msg, bot, session, db_user, state)

        # Проверяем удаление сообщения с ответом пользователя и сообщения с капчей
        bot.delete_message.assert_any_call(777, 1001)
        bot.delete_message.assert_any_call(777, 555)

        # Проверяем установку статуса и коммит в БД
        assert db_user.captcha_passed is True
        assert db_user.start_pending is False
        session.commit.assert_called_once()

        # FSM очищен и переведен на выбор города (так как город None)
        state.clear.assert_called_once()
        state.set_state.assert_called_once_with(CityState.waiting_for_city)

        # Новое сообщение пользователю запрашивает город БЕЗ лишнего текста о капче
        bot.send_message.assert_called_once()
        sent_text = bot.send_message.call_args[1]["text"]
        assert "Укажите ваш город" in sent_text
        assert "капча" not in sent_text.lower()

    asyncio.run(run())


def test_handle_math_captcha_incorrect_answer_rotates_problem_and_deletes_old():
    """Проверяет, что неверный ответ удаляет старое сообщение капчи и выдает новый пример."""
    async def run():
        from handlers.captcha import handle_math_captcha_answer

        bot = AsyncMock()
        bot.send_message = AsyncMock(return_value=MagicMock(message_id=556))
        session = AsyncMock()
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={
            "captcha_answer": 10,
            "captcha_attempts": 3,
            "captcha_msg_id": 555,
        })

        db_user = MagicMock(spec=User)
        db_user.captcha_passed = False

        msg = AsyncMock(spec=Message)
        msg.chat = Chat(id=777, type=ChatType.PRIVATE)
        msg.message_id = 1002
        msg.text = "7"
        msg.from_user = TelegramUser(id=777, is_bot=False, first_name="Test")

        await handle_math_captcha_answer(msg, bot, session, db_user, state)

        # Удаление ответа и старой капчи
        bot.delete_message.assert_any_call(777, 1002)
        bot.delete_message.assert_any_call(777, 555)

        # Пользователь не верифицирован
        assert db_user.captcha_passed is False

        # Отправлено новое сообщение с уменьшенным количеством попыток
        bot.send_message.assert_called_once()
        sent_text = bot.send_message.call_args[1]["text"]
        assert "Неверно, попробуйте ещё раз" in sent_text
        assert "Осталось попыток: 2" in sent_text

        # В state сохранен новый msg_id
        state.update_data.assert_called_once()
        update_args = state.update_data.call_args[1]
        assert update_args["captcha_attempts"] == 2
        assert update_args["captcha_msg_id"] == 556

    asyncio.run(run())


def test_handle_math_captcha_invalid_input_cleans_up_and_replaces_message():
    """Проверяет, что нечисловой ввод не оставляет дубликатов сообщений в чате."""
    async def run():
        from handlers.captcha import handle_math_captcha_answer

        bot = AsyncMock()
        bot.send_message = AsyncMock(return_value=MagicMock(message_id=557))
        session = AsyncMock()
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={
            "captcha_answer": 7,
            "captcha_problem": "3 + 4",
            "captcha_attempts": 3,
            "captcha_msg_id": 555,
        })

        db_user = MagicMock(spec=User)
        db_user.captcha_passed = False

        msg = AsyncMock(spec=Message)
        msg.chat = Chat(id=777, type=ChatType.PRIVATE)
        msg.message_id = 1003
        msg.text = "привет"
        msg.from_user = TelegramUser(id=777, is_bot=False, first_name="Test")

        await handle_math_captcha_answer(msg, bot, session, db_user, state)

        # Удален старый ввод и старая капча
        bot.delete_message.assert_any_call(777, 1003)
        bot.delete_message.assert_any_call(777, 555)

        # Отправлено аккуратное сообщение с напоминанием
        bot.send_message.assert_called_once()
        sent_text = bot.send_message.call_args[1]["text"]
        assert "Отправьте ответ числом" in sent_text
        assert "3 + 4 = ?" in sent_text

        # captcha_msg_id обновлен на id предупреждения
        state.update_data.assert_called_once_with(captcha_msg_id=557)

    asyncio.run(run())


def test_cmd_start_requires_two_starts_for_all_users():
    """Проверяет, что любой пользователь (новый или существующий) обязан нажать /start дважды для вызова капчи."""
    async def run():
        from handlers.client.start import cmd_start

        bot = AsyncMock()
        session = AsyncMock()
        state = AsyncMock()

        # Существующий пользователь, у которого ранее был город и пройдена капча
        db_user = MagicMock(spec=User)
        db_user.captcha_passed = True
        db_user.start_count = 5
        db_user.start_pending = False
        db_user.city = "Москва"
        db_user.district = "Центральный"

        msg1 = AsyncMock(spec=Message)
        msg1.chat = Chat(id=777, type=ChatType.PRIVATE)
        msg1.message_id = 1004
        msg1.text = "/start"
        msg1.from_user = TelegramUser(id=777, is_bot=False, first_name="Test")

        with patch("handlers.client.start.send_math_captcha", AsyncMock()) as mock_send_captcha, \
             patch("handlers.client.start.delete_user_message", AsyncMock()) as mock_del_msg:
            # 1-е нажатие /start
            await cmd_start(msg1, db_user, state, bot, session)

            # Капча НЕ отправляется, start_pending становится True, статус и город сбрасываются
            mock_send_captcha.assert_not_called()
            mock_del_msg.assert_called_once_with(msg1)
            assert db_user.start_pending is True
            assert db_user.captcha_passed is False
            assert db_user.city == ""
            assert db_user.start_count == 6
            session.commit.assert_called_once()

            session.commit.reset_mock()
            mock_del_msg.reset_mock()

            # 2-е нажатие /start
            msg2 = AsyncMock(spec=Message)
            msg2.chat = Chat(id=777, type=ChatType.PRIVATE)
            msg2.message_id = 1005
            msg2.text = "/start"
            msg2.from_user = TelegramUser(id=777, is_bot=False, first_name="Test")

            await cmd_start(msg2, db_user, state, bot, session)

            # Капча отправляется!
            mock_send_captcha.assert_called_once_with(bot, 777, db_user, state)
            mock_del_msg.assert_called_once_with(msg2)
            assert db_user.start_pending is False
            assert db_user.captcha_passed is False
            assert db_user.city == ""
            assert db_user.start_count == 7
            session.commit.assert_called_once()

    asyncio.run(run())


def test_captcha_success_always_requires_manual_city_even_if_user_had_city():
    """Проверяет, что после успешной капчи ВСЕГДА запрашивается ручной ввод города."""
    async def run():
        from handlers.captcha import handle_math_captcha_answer
        from states.client_states import CityState

        bot = AsyncMock()
        session = AsyncMock()
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={
            "captcha_answer": 8,
            "captcha_attempts": 3,
            "captcha_msg_id": 555,
        })

        db_user = MagicMock(spec=User)
        db_user.captcha_passed = False
        db_user.city = "Казань"  # Допустим, ранее в БД был город

        msg = AsyncMock(spec=Message)
        msg.chat = Chat(id=777, type=ChatType.PRIVATE)
        msg.message_id = 1006
        msg.text = "8"
        msg.from_user = TelegramUser(id=777, is_bot=False, first_name="Test")

        await handle_math_captcha_answer(msg, bot, session, db_user, state)

        # Капча пройдена, город сброшен на ""
        assert db_user.captcha_passed is True
        assert db_user.city == ""

        # Сообщение с капчей удалено
        bot.delete_message.assert_any_call(777, 555)

        # Состояние переведено на ручной ввод города
        state.set_state.assert_called_once_with(CityState.waiting_for_city)
        bot.send_message.assert_called_once()
        sent_text = bot.send_message.call_args[1]["text"]
        assert "Укажите ваш город" in sent_text

    asyncio.run(run())


def test_process_city_input_deletes_city_prompt_message():
    """Проверяет, что сообщение с запросом города удаляется после ввода пользователем города."""
    async def run():
        from handlers.client.start import process_city_input

        bot = AsyncMock()
        session = AsyncMock()
        state = AsyncMock()
        state.get_data = AsyncMock(return_value={
            "onboarding_after_captcha": True,
            "city_prompt_msg_id": 888,
        })

        db_user = MagicMock(spec=User)
        db_user.city = ""
        db_user.district = None

        msg = AsyncMock(spec=Message)
        msg.chat = Chat(id=777, type=ChatType.PRIVATE)
        msg.message_id = 1007
        msg.text = "Москва"
        msg.reply_to_message = None
        msg.from_user = TelegramUser(id=777, is_bot=False, first_name="Test")

        with patch("handlers.client.start.send_or_edit_screen", AsyncMock()), \
             patch("handlers.client.start.delete_user_message", AsyncMock()) as mock_del_user:
            await process_city_input(msg, session, db_user, state, bot)

            # Проверяем, что сообщение бота с запросом города (id 888) было удалено
            bot.delete_message.assert_any_call(chat_id=777, message_id=888)
            mock_del_user.assert_called_once_with(msg)
            assert db_user.city == "Москва"
            session.commit.assert_called_once()

    asyncio.run(run())



