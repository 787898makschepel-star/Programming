import pytest

from config import Settings
from handlers.client.profile import MANUAL_CRYPTO_METHODS
from keyboards.inline_client import get_crypto_networks_kb
from utils.callback_parser import parse_callback_suffix, parse_callback_int, split_callback_suffix


def test_usdt_wallet_addresses_match_requested_values():
    settings = Settings(_env_file=None)

    assert settings.USDT_TRC20_ADDRESS == "TFxNg46apWAirutFCKPTrntWyjvzmkzV9m"
    assert settings.USDT_ERC20_ADDRESS == "0x8782dFC5801D1ce09d9BC38d125FE7FDb4A1534A"
    assert settings.USDT_BEP20_ADDRESS == "0x8782dFC5801D1ce09d9BC38d125FE7FDb4A1534A"


def test_crypto_network_keyboard_only_offers_supported_usdt_networks():
    keyboard = get_crypto_networks_kb()
    callback_data = [button.callback_data for row in keyboard.inline_keyboard for button in row]

    assert callback_data == [
        "topup_manual_usdt_trc20",
        "topup_manual_usdt_erc20",
        "topup_manual_usdt_bep20",
        "client_profile",
    ]
    assert set(MANUAL_CRYPTO_METHODS) == {"usdt_trc20", "usdt_erc20", "usdt_bep20"}


def test_parse_callback_suffix_handles_prefixed_payloads():
    assert parse_callback_suffix("topup_manual_usdt_bep20", "topup_manual_") == "usdt_bep20"
    assert parse_callback_suffix("view_order_42", "view_order_") == "42"
    assert parse_callback_suffix("", "topup_manual_") is None
    assert parse_callback_suffix(None, "topup_manual_") is None


def test_parse_callback_int_rejects_invalid_payloads():
    assert parse_callback_int("view_order_42", "view_order_") == 42
    assert parse_callback_int("view_order_x", "view_order_") is None
    assert parse_callback_int("invalid", "view_order_") is None


def test_split_callback_suffix_supports_showcase_quantity_payloads():
    assert split_callback_suffix("candy_plus_12_3.5", "candy_plus_") == ["12", "3.5"]
    assert split_callback_suffix("buy_candy_7_2", "buy_candy_") == ["7", "2"]
    assert split_callback_suffix("candy_minus_12_0.5", "candy_minus_") == ["12", "0.5"]


def test_parse_callback_suffix_rejects_malformed_data():
    assert parse_callback_suffix("candy_plus_", "candy_plus_") is None
    assert parse_callback_suffix("other_prefix", "candy_plus_") is None
    assert parse_callback_suffix("candy_plus_x", "candy_plus_") == "x"
