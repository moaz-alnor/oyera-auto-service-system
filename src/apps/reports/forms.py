"""Forms shared by operational reports."""

from datetime import date, timedelta

from django import forms
from django.utils import timezone

from apps.reports.constants import (
    ReportPeriodPreset,
)
from apps.reports.date_ranges import ReportDateRange

_MAX_REPORT_DAYS = 366


class ReportDateRangeForm(forms.Form):
    """Validate a preset or custom reporting period."""

    preset = forms.ChoiceField(
        choices=ReportPeriodPreset.choices,
        initial=ReportPeriodPreset.THIS_MONTH,
        label="Reporting period",
    )
    start_date = forms.DateField(
        required=False,
        label="Start date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = forms.DateField(
        required=False,
        label="End date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def clean(self) -> dict[str, object]:
        """Resolve and validate the selected date range."""

        cleaned_data = super().clean()

        preset = cleaned_data.get("preset")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        today = timezone.localdate()

        if preset == ReportPeriodPreset.CUSTOM:
            if start_date is None:
                self.add_error(
                    "start_date",
                    ("A start date is required for a custom report."),
                )

            if end_date is None:
                self.add_error(
                    "end_date",
                    ("An end date is required for a custom report."),
                )

            if start_date is None or end_date is None:
                return cleaned_data

        elif preset == ReportPeriodPreset.TODAY:
            start_date = today
            end_date = today

        elif preset == ReportPeriodPreset.THIS_WEEK:
            start_date = today - timedelta(days=today.weekday())
            end_date = today

        elif preset == ReportPeriodPreset.THIS_MONTH:
            start_date = today.replace(day=1)
            end_date = today

        else:
            return cleaned_data

        if not isinstance(start_date, date):
            return cleaned_data

        if not isinstance(end_date, date):
            return cleaned_data

        if start_date > end_date:
            self.add_error(
                "start_date",
                ("Start date must be on or before end date."),
            )

        if end_date > today:
            self.add_error(
                "end_date",
                "Reports cannot include future dates.",
            )

        inclusive_days = (end_date - start_date).days + 1

        if inclusive_days > _MAX_REPORT_DAYS:
            self.add_error(
                "start_date",
                (f"A report period cannot exceed {_MAX_REPORT_DAYS} days."),
            )

        cleaned_data["start_date"] = start_date
        cleaned_data["end_date"] = end_date

        return cleaned_data

    def to_date_range(self) -> ReportDateRange:
        """Return the validated report date range."""

        if not self.is_bound:
            raise ValueError("The report date form is not bound.")

        if not hasattr(self, "cleaned_data"):
            self.full_clean()

        if self.errors:
            raise ValueError("The report date form is invalid.")

        start_date = self.cleaned_data.get("start_date")
        end_date = self.cleaned_data.get("end_date")

        if not isinstance(start_date, date):
            raise ValueError("The report start date is missing.")

        if not isinstance(end_date, date):
            raise ValueError("The report end date is missing.")

        return ReportDateRange(
            start_date=start_date,
            end_date=end_date,
        )
