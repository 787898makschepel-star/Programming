"""
Утилиты для работы с единицами измерения товаров витрины (граммы и штуки).
"""
from typing import Optional, Union


def is_gram_unit(unit: Optional[str]) -> bool:
    """Определяет, является ли единица измерения граммами (г, г., гр, грамм)."""
    if not unit:
        return False
    u = unit.strip().lower()
    return u.startswith("г") or u == "g" or "грамм" in u


def is_piece_unit(unit: Optional[str]) -> bool:
    """Определяет, является ли единица измерения штуками (шт, шт., pcs)."""
    return not is_gram_unit(unit)


def get_default_min_quantity(unit: Optional[str]) -> float:
    """Минимальный заказ по умолчанию: 0.5 для граммов, 3.0 для штук."""
    return 0.5 if is_gram_unit(unit) else 3.0


def get_quantity_step(unit: Optional[str]) -> float:
    """Шаг изменения количества: 0.5 для граммов, 1.0 для штук."""
    return 0.5 if is_gram_unit(unit) else 1.0


def format_quantity_label(qty: Union[float, int], unit: Optional[str]) -> str:
    """
    Форматирует значение количества для центральной кнопки между '-' и '+':
    - Если unit === "г." -> например: "0.5г."
    - Если unit === "г" -> например: "0.5г"
    - Если unit === "шт." или "шт" -> например: "3шт"
    """
    u = (unit or "шт.").strip()
    if is_gram_unit(u):
        val = f"{float(qty):g}"
        unit_str = u if u in ("г.", "г") else "г."
        return f"{val}{unit_str}"
    else:
        val = f"{int(qty)}"
        unit_str = "шт" if u in ("шт.", "шт") else u
        return f"{val}{unit_str}"


def format_quantity_with_unit(qty: Union[float, int], unit: Optional[str]) -> str:
    """
    Форматирует количество с пробелом перед единицей для текстов и чеков:
    например, '0.5 г.' или '3 шт.'
    """
    u = (unit or "шт.").strip()
    if is_gram_unit(u):
        unit_str = "г." if "." in u else "г"
        return f"{float(qty):g} {unit_str}"
    else:
        unit_str = "шт." if "." in u else "шт"
        return f"{int(qty)} {unit_str}"
