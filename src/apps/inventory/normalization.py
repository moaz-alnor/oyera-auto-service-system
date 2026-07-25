"""Normalization helpers for inventory records."""

import re

_MULTIPLE_WHITESPACE_PATTERN = re.compile(r"\s+")
_LOCATION_CODE_PATTERN = re.compile(r"[^A-Z0-9]+")


def normalize_location_code(value: str) -> str:
    """Return a stable uppercase storage-location code."""

    normalized = value.strip().upper()
    normalized = _LOCATION_CODE_PATTERN.sub("-", normalized)

    return normalized.strip("-")


def normalize_reference(value: str) -> str:
    """Normalize an external inventory reference."""

    return _MULTIPLE_WHITESPACE_PATTERN.sub(
        " ",
        value.strip(),
    )
