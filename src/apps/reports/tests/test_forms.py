"""Tests for report date-range validation."""

from datetime import date

import pytest

from apps.reports.constants import (
    ReportPeriodPreset,
)
from apps.reports.date_ranges import ReportDateRange
from apps.reports.forms import ReportDateRangeForm


@pytest.mark.parametrize(
    ("preset", "expected_start"),
    (
        (
            ReportPeriodPreset.TODAY,
            date(2026, 8, 1),
        ),
        (
            ReportPeriodPreset.THIS_WEEK,
            date(2026, 7, 27),
        ),
        (
            ReportPeriodPreset.THIS_MONTH,
            date(2026, 8, 1),
        ),
    ),
)
def test_report_period_presets(
    monkeypatch,
    preset: ReportPeriodPreset,
    expected_start: date,
) -> None:
    """Resolve supported preset periods."""

    monkeypatch.setattr(
        "apps.reports.forms.timezone.localdate",
        lambda: date(2026, 8, 1),
    )

    form = ReportDateRangeForm({"preset": preset})

    assert form.is_valid()

    assert form.to_date_range() == ReportDateRange(
        start_date=expected_start,
        end_date=date(2026, 8, 1),
    )


def test_custom_report_period() -> None:
    """Accept an explicit historical date range."""

    form = ReportDateRangeForm(
        {
            "preset": ReportPeriodPreset.CUSTOM,
            "start_date": "2026-07-01",
            "end_date": "2026-07-31",
        }
    )

    assert form.is_valid()

    assert form.to_date_range() == ReportDateRange(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    )


@pytest.mark.parametrize(
    ("data", "missing_field"),
    (
        (
            {
                "preset": (ReportPeriodPreset.CUSTOM),
                "end_date": "2026-07-31",
            },
            "start_date",
        ),
        (
            {
                "preset": (ReportPeriodPreset.CUSTOM),
                "start_date": "2026-07-01",
            },
            "end_date",
        ),
    ),
)
def test_custom_period_requires_both_dates(
    data: dict[str, object],
    missing_field: str,
) -> None:
    """Require both custom date boundaries."""

    form = ReportDateRangeForm(data)

    assert not form.is_valid()
    assert missing_field in form.errors


def test_report_period_rejects_reversed_dates() -> None:
    """Reject a start date after the end date."""

    form = ReportDateRangeForm(
        {
            "preset": ReportPeriodPreset.CUSTOM,
            "start_date": "2026-07-31",
            "end_date": "2026-07-01",
        }
    )

    assert not form.is_valid()
    assert "start_date" in form.errors


def test_report_period_rejects_future_dates(
    monkeypatch,
) -> None:
    """Reject a period extending into the future."""

    monkeypatch.setattr(
        "apps.reports.forms.timezone.localdate",
        lambda: date(2026, 8, 1),
    )

    form = ReportDateRangeForm(
        {
            "preset": ReportPeriodPreset.CUSTOM,
            "start_date": "2026-08-01",
            "end_date": "2026-08-02",
        }
    )

    assert not form.is_valid()
    assert "end_date" in form.errors


def test_report_period_rejects_more_than_one_year(
    monkeypatch,
) -> None:
    """Limit one report request to 366 days."""

    monkeypatch.setattr(
        "apps.reports.forms.timezone.localdate",
        lambda: date(2026, 8, 1),
    )

    form = ReportDateRangeForm(
        {
            "preset": ReportPeriodPreset.CUSTOM,
            "start_date": "2025-07-31",
            "end_date": "2026-08-01",
        }
    )

    assert not form.is_valid()
    assert "start_date" in form.errors
