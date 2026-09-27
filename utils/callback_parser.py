from __future__ import annotations

from typing import Optional


def parse_callback_suffix(callback_data: Optional[str], prefix: str) -> Optional[str]:
    """Return raw suffix after the prefix or None when payload is invalid."""
    if not callback_data or not isinstance(callback_data, str):
        return None

    if not callback_data.startswith(prefix):
        return None

    suffix = callback_data[len(prefix):]
    return suffix or None


def parse_callback_int(callback_data: Optional[str], prefix: str) -> Optional[int]:
    """Parse integer suffix from callback data when it is valid."""
    suffix = parse_callback_suffix(callback_data, prefix)
    if suffix is None or not suffix.isdigit():
        return None
    return int(suffix)


def split_callback_suffix(callback_data: Optional[str], prefix: str) -> Optional[list[str]]:
    """Split a callback suffix on underscores, returning None for invalid payloads."""
    suffix = parse_callback_suffix(callback_data, prefix)
    if suffix is None:
        return None
    parts = suffix.split("_")
    return parts if any(part for part in parts) else None
