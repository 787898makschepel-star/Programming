import json
from pathlib import Path
from typing import Any

from config import config

_registry: dict[str, str] = {}


def _read_mapping(raw: str) -> dict[str, str]:
    try:
        value = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items() if item is not None}


def _button_key(text: str, options: dict[str, Any], scope: str) -> str:
    callback_data = options.get("callback_data")
    if callback_data:
        return f"{scope}:callback:{callback_data}"
    url = options.get("url")
    if url:
        return f"{scope}:url:{url}"
    return f"{scope}:text:{text}"


def resolve_button(text: str, *, scope: str = "client", **options: Any) -> tuple[str, str, str]:
    key = _button_key(text, options, scope)
    _registry.setdefault(key, text)
    labels = _read_mapping(getattr(config, "BUTTON_LABELS", "{}"))
    emoji_ids = _read_mapping(getattr(config, "BUTTON_EMOJI_IDS", "{}"))
    label = labels.get(key, text)
    emoji_id = emoji_ids.get(key) or str(getattr(config, "BUTTON_EMOJI_ID", "") or "").strip()
    return key, label, emoji_id


def resolve_reply_button(key: str, text: str, scope: str = "client") -> tuple[str, str]:
    _, label, emoji_id = resolve_button(text, callback_data=f"reply:{key}", scope=scope)
    return label, emoji_id


def registered_buttons(scope: str = "client") -> list[tuple[int, str, str]]:
    labels = _read_mapping(getattr(config, "BUTTON_LABELS", "{}"))
    scoped = [(key, default_text) for key, default_text in _registry.items() if key.startswith(f"{scope}:")]
    return [(index, key, labels.get(key, default_text)) for index, (key, default_text) in enumerate(scoped)]


def button_key_by_index(index: int, scope: str = "client") -> str | None:
    buttons = registered_buttons(scope)
    for item_index, key, _ in buttons:
        if item_index == index:
            return key
    return None


def button_details(key: str) -> tuple[str, str]:
    labels = _read_mapping(getattr(config, "BUTTON_LABELS", "{}"))
    emoji_ids = _read_mapping(getattr(config, "BUTTON_EMOJI_IDS", "{}"))
    return labels.get(key, _registry.get(key, key)), emoji_ids.get(key) or str(getattr(config, "BUTTON_EMOJI_ID", "") or "").strip()


def _write_env_value(name: str, value: str) -> None:
    env_path = Path(".env")
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    replacement = f"{name}={value}"
    for index, line in enumerate(lines):
        if line.startswith(f"{name}="):
            lines[index] = replacement
            break
    else:
        lines.append(replacement)
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_button_override(key: str, label: str, emoji_id: str) -> None:
    labels = _read_mapping(getattr(config, "BUTTON_LABELS", "{}"))
    emoji_ids = _read_mapping(getattr(config, "BUTTON_EMOJI_IDS", "{}"))
    labels[key] = label
    if emoji_id:
        emoji_ids[key] = emoji_id
    else:
        emoji_ids.pop(key, None)
    labels_value = json.dumps(labels, ensure_ascii=False, separators=(",", ":"))
    emoji_value = json.dumps(emoji_ids, ensure_ascii=False, separators=(",", ":"))
    config.BUTTON_LABELS = labels_value
    config.BUTTON_EMOJI_IDS = emoji_value
    _write_env_value("BUTTON_LABELS", labels_value)
    _write_env_value("BUTTON_EMOJI_IDS", emoji_value)
