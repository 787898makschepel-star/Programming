import asyncio
from database.models import User
from handlers.receipts import _build_receipt_card, get_admin_receipt_kb
from services.exchange_rate import convert_usdt_to_rub, convert_rub_to_usdt


def test_currency_conversion():
    async def _test():
        rub, rate = await convert_usdt_to_rub(50.0)
        assert rate > 10.0
        assert rub > 0.0

        usdt, rate2 = await convert_rub_to_usdt(rub)
        assert round(usdt) == 50

    asyncio.run(_test())


def test_build_receipt_card_pending():
    dummy_user = User(
        id=1,
        tg_id=123456789,
        username="john_doe",
        full_name="John Doe",
        balance=1500.0,
        city="Москва"
    )

    card = _build_receipt_card(
        receipt_code="123456",
        user=dummy_user,
        comment="Оплата 50 USDT",
        time_str="07.10.2026 16:50",
        status="pending",
        amount_rub=4650.0,
        amount_usdt=50.0,
        rate=93.0,
        network="BEP20 (BNB Smart Chain)"
    )

    assert "ЗАЯВКА #123456 · ОЖИДАЕТ" in card
    assert "50 USDT" in card
    assert "4,650.00 ₽" in card
    assert "1 USDT = 93.00 ₽" in card
    assert "BEP20 (BNB Smart Chain)" in card


def test_build_receipt_card_approved():
    dummy_user = User(
        id=1,
        tg_id=123456789,
        username="john_doe",
        full_name="John Doe",
        balance=6150.0,
        city="Москва"
    )

    card = _build_receipt_card(
        receipt_code="123456",
        user=dummy_user,
        comment="Оплата 50 USDT",
        time_str="07.10.2026 16:50",
        status="approved",
        amount_rub=4650.0,
        amount_usdt=50.0,
        rate=93.0,
        network="BEP20",
        admin_name="@admin"
    )

    assert "ЗАЯВКА #123456 · ПОДТВЕРЖДЕНА" in card
    assert "Зачислено на баланс:" in card
    assert "+4650 ₽" in card
    assert "1 USDT = 93.00 ₽" in card
    assert "@admin" in card


def test_admin_receipt_kb():
    kb = get_admin_receipt_kb(tx_id=99, amount_rub=4650.0)
    button_texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert any("4650 ₽" in t for t in button_texts)
    assert any("Изменить сумму" in t for t in button_texts)
    assert any("Отклонить" in t for t in button_texts)
