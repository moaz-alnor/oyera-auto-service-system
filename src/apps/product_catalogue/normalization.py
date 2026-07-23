"""Normalization utilities for product-catalogue information."""

import re

from django.core.exceptions import ValidationError

_WHITESPACE_PATTERN = re.compile(r"\s+")
_NON_ALPHANUMERIC_PATTERN = re.compile(r"[^A-Z0-9]+")


def normalize_category_code_display(value: str) -> str:
    """Normalize a product-category code for display.

    Args:
        value: Category code entered by an employee.

    Returns:
        An uppercase code using hyphens as separators.

    Raises:
        ValidationError: If the normalized code is invalid.
    """

    normalized_value = _NON_ALPHANUMERIC_PATTERN.sub(
        "-",
        value.strip().upper(),
    ).strip("-")

    if not 2 <= len(normalized_value) <= 30:
        raise ValidationError(
            "Enter a category code containing 2 to 30 letters or numbers.",
            code="invalid_category_code",
        )

    return normalized_value


def normalize_category_code_key(value: str) -> str:
    """Return the canonical product-category matching key."""

    normalized_value = _NON_ALPHANUMERIC_PATTERN.sub(
        "",
        value.upper(),
    )

    if not 2 <= len(normalized_value) <= 30:
        raise ValidationError(
            "Enter a valid product-category code.",
            code="invalid_category_code",
        )

    return normalized_value


def normalize_product_sku_display(value: str) -> str:
    """Normalize a product SKU for display.

    Args:
        value: SKU entered by an employee.

    Returns:
        An uppercase SKU using hyphens as separators.

    Raises:
        ValidationError: If the normalized SKU is invalid.
    """

    normalized_value = _NON_ALPHANUMERIC_PATTERN.sub(
        "-",
        value.strip().upper(),
    ).strip("-")

    if not 2 <= len(normalized_value) <= 40:
        raise ValidationError(
            "Enter a SKU containing 2 to 40 letters or numbers.",
            code="invalid_product_sku",
        )

    return normalized_value


def normalize_product_sku_key(value: str) -> str:
    """Return the canonical SKU matching key."""

    normalized_value = _NON_ALPHANUMERIC_PATTERN.sub(
        "",
        value.upper(),
    )

    if not 2 <= len(normalized_value) <= 40:
        raise ValidationError(
            "Enter a valid product SKU.",
            code="invalid_product_sku",
        )

    return normalized_value


def normalize_product_name(value: str) -> str:
    """Normalize a product or category display name."""

    normalized_value = _WHITESPACE_PATTERN.sub(
        " ",
        value,
    ).strip()

    if not normalized_value:
        raise ValidationError(
            "A name is required.",
            code="required",
        )

    return normalized_value


def normalize_part_number_display(value: str) -> str:
    """Normalize an optional manufacturer part number."""

    stripped_value = value.strip()

    if not stripped_value:
        return ""

    normalized_value = _NON_ALPHANUMERIC_PATTERN.sub(
        "-",
        stripped_value.upper(),
    ).strip("-")

    if len(normalized_value) > 80:
        raise ValidationError(
            "The manufacturer part number cannot exceed 80 characters.",
            code="invalid_part_number",
        )

    return normalized_value


def normalize_part_number_key(value: str) -> str:
    """Return the matching key for an optional part number."""

    return _NON_ALPHANUMERIC_PATTERN.sub(
        "",
        value.upper(),
    )


def normalize_category_code_search(value: str) -> str:
    """Return a canonical partial category-code search value."""

    return _NON_ALPHANUMERIC_PATTERN.sub(
        "",
        value.upper(),
    )


def normalize_product_sku_search(value: str) -> str:
    """Return a canonical partial SKU search value."""

    return _NON_ALPHANUMERIC_PATTERN.sub(
        "",
        value.upper(),
    )


def normalize_part_number_search(value: str) -> str:
    """Return a canonical partial manufacturer-part search value."""

    return _NON_ALPHANUMERIC_PATTERN.sub(
        "",
        value.upper(),
    )
