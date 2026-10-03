"""
Модуль для обратной совместимости.
Вся логика перенесена в handlers.captcha (математическая капча с ручным вводом).
"""
from handlers.captcha import (
    router,
    send_math_captcha,
    send_start_captcha,
    generate_math_problem,
)

__all__ = [
    "router",
    "send_math_captcha",
    "send_start_captcha",
    "generate_math_problem",
]
