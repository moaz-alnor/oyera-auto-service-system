"""Normalization utilities for vehicle information."""

import re

from django.core.exceptions import ValidationError

_WHITESPACE_PATTERN = re.compile(r"\s+")
_NON_ALPHANUMERIC_PATTERN = re.compile(r"[^A-Z0-9]+")


def normalize_registration_display(value: str) -> str:
    """Normalize a registration number for display.

    Args:
        value: Registration number entered by an employee.

    Returns:
        An uppercase value with repeated whitespace removed.

    Raises:
        ValidationError: If no registration number remains.
    """

    normalized_value = _WHITESPACE_PATTERN.sub(
        " ",
        value.strip().upper(),
    )

    if not normalized_value:
        raise ValidationError(
            "Vehicle registration number is required.",
            code="required",
        )

    return normalized_value


def normalize_registration_key(value: str) -> str:
    """Return a canonical registration value for matching.

    Spaces, hyphens, and other punctuation are removed so values such as
    ``UBD 245X``, ``UBD-245X``, and ``ubd245x`` match the same vehicle.

    Args:
        value: Registration number entered by an employee.

    Returns:
        An uppercase letters-and-digits-only identifier.

    Raises:
        ValidationError: If the canonical value has an invalid length.
    """

    normalized_value = _NON_ALPHANUMERIC_PATTERN.sub(
        "",
        value.upper(),
    )

    if not 3 <= len(normalized_value) <= 20:
        raise ValidationError(
            "Enter a valid vehicle registration number.",
            code="invalid_registration_number",
        )

    return normalized_value


def normalize_vehicle_name(value: str) -> str:
    """Normalize a vehicle make or model name."""

    return _WHITESPACE_PATTERN.sub(" ", value).strip()


def normalize_optional_identifier(value: str) -> str:
    """Normalize an optional engine, chassis, or VIN identifier."""

    return _WHITESPACE_PATTERN.sub(
        " ",
        value.strip().upper(),
    )
