"""Normalization utilities for service-catalogue information."""

import re

from django.core.exceptions import ValidationError

_WHITESPACE_PATTERN = re.compile(r"\s+")
_NON_ALPHANUMERIC_PATTERN = re.compile(r"[^A-Z0-9]+")


def normalize_service_code_display(value: str) -> str:
    """Normalize a service code for display.

    Args:
        value: Service code entered by an employee.

    Returns:
        An uppercase service code using hyphens as separators.

    Raises:
        ValidationError: If the normalized code is invalid.
    """

    normalized_value = _NON_ALPHANUMERIC_PATTERN.sub(
        "-",
        value.strip().upper(),
    ).strip("-")

    if not 2 <= len(normalized_value) <= 30:
        raise ValidationError(
            "Enter a service code containing 2 to 30 letters or numbers.",
            code="invalid_service_code",
        )

    return normalized_value


def normalize_service_code_key(value: str) -> str:
    """Return a canonical service-code value for matching."""

    normalized_value = _NON_ALPHANUMERIC_PATTERN.sub(
        "",
        value.upper(),
    )

    if not 2 <= len(normalized_value) <= 30:
        raise ValidationError(
            "Enter a valid service code.",
            code="invalid_service_code",
        )

    return normalized_value


def normalize_service_name(value: str) -> str:
    """Normalize a service display name.

    Args:
        value: Service name entered by an employee.

    Returns:
        A trimmed name with repeated whitespace collapsed.

    Raises:
        ValidationError: If no name remains.
    """

    normalized_value = _WHITESPACE_PATTERN.sub(
        " ",
        value,
    ).strip()

    if not normalized_value:
        raise ValidationError(
            "Service name is required.",
            code="required",
        )

    return normalized_value
