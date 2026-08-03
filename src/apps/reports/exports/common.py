"""Shared helpers for safe report CSV exports."""

from datetime import datetime

from django.utils import timezone

_DANGEROUS_CELL_PREFIXES = (
    "=",
    "+",
    "-",
    "@",
    "\t",
    "\r",
)


def safe_csv_text(value: object) -> str:
    """Protect text cells from spreadsheet formulas."""

    text = str(value)

    if text.startswith(_DANGEROUS_CELL_PREFIXES):
        return f"'{text}"

    return text


def format_local_datetime(
    value: datetime | None,
) -> str:
    """Return a stable local datetime for CSV output."""

    if value is None:
        return ""

    if timezone.is_aware(value):
        value = timezone.localtime(value)

    return value.strftime("%Y-%m-%d %H:%M:%S")
