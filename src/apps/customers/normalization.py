"""Normalization utilities for customer information."""

import re

from django.core.exceptions import ValidationError

_WHITESPACE_PATTERN = re.compile(r"\s+")
_NON_DIGIT_PATTERN = re.compile(r"\D+")


def normalize_customer_name(value: str) -> str:
    """Normalize a customer or company name.

    Args:
        value: Name entered by an employee.

    Returns:
        A trimmed name with repeated whitespace collapsed.

    Raises:
        ValidationError: If the resulting name is empty.
    """

    normalized_value = _WHITESPACE_PATTERN.sub(
        " ",
        value,
    ).strip()

    if not normalized_value:
        raise ValidationError(
            "Customer name is required.",
            code="required",
        )

    return normalized_value


def normalize_phone_number(value: str) -> str:
    """Convert a phone number to digits used for matching.

    Formatting characters are removed, while the original value remains
    available separately for display.

    Args:
        value: Phone number entered by an employee.

    Returns:
        A digits-only phone number.

    Raises:
        ValidationError: If the number has an unsupported length.
    """

    normalized_value = _NON_DIGIT_PATTERN.sub("", value)

    if not 7 <= len(normalized_value) <= 15:
        raise ValidationError(
            "Enter a valid phone number containing 7 to 15 digits.",
            code="invalid_phone_number",
        )

    return normalized_value


def normalize_email_address(value: str) -> str:
    """Normalize an optional email address."""

    return value.strip().lower()
