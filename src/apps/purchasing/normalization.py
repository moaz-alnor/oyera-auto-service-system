"""Normalisation helpers for purchasing records."""

import re

_NON_ALPHANUMERIC_PATTERN = re.compile(r"[^A-Z0-9]+")


def normalize_supplier_code(value: str) -> str:
    """Return a stable uppercase supplier code."""

    normalized = value.strip().upper()

    return _NON_ALPHANUMERIC_PATTERN.sub(
        "-",
        normalized,
    ).strip("-")


def normalize_supplier_name(value: str) -> str:
    """Return a searchable supplier name."""

    return " ".join(value.strip().casefold().split())


def normalize_contact_value(value: str) -> str:
    """Trim optional supplier contact information."""

    return value.strip()
