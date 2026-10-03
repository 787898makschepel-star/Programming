import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.enums import ChatType
from aiogram.types import Message, CallbackQuery, User as TelegramUser, Chat
from handlers.captcha import generate_math_problem
from middlewares.user_tracker import UserTrackerMiddleware
from database.models import User
from states.client_states import CaptchaState


def test_generate_math_problem_ranges_and_answers():
    """Проверяет корректность генерации математических примеров."""
    for _ in range(100):
        problem_str, answer = generate_math_problem()
        assert isinstance(problem_str, str)
        assert isinstance(answer, int)
        assert answer > 0

        if "+" in problem_str:
            parts = problem_str.split("+")
            a, b = int(parts[0].strip()), int(parts[1].strip())
            assert a + b == answer
            assert 12 <= a <= 49
            assert 11 <= b <= 49
        elif "−" in problem_str or "-" in problem_str:
            clean = problem_str.replace("−", "-")
            parts = clean.split("-")
            a, b = int(parts[0].strip()), int(parts[1].strip())
            assert a - b == answer
            assert a >= 30
            assert answer >= 10
        elif "×" in problem_str or "*" in problem_str:
            clean = problem_str.replace("×", "*")
            parts = clean.split("*")
            a, b = int(parts[0].strip()), int(parts[1].strip())
            assert a * b == answer
            assert 3 <= a <= 9
            assert 3 <= b <= 9


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
