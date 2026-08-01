"""HTTP views for operational reports."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.accounts.decorators import (
    employee_permission_required,
)
from apps.reports.constants import (
    ReportPeriodPreset,
    ReportPermissionName,
)
from apps.reports.forms import ReportDateRangeForm


@employee_permission_required(ReportPermissionName.ACCESS_REPORTS.value)
def report_index(
    request: HttpRequest,
) -> HttpResponse:
    """Display the operational report catalogue."""

    form_data = (
        request.GET if request.GET else {"preset": (ReportPeriodPreset.THIS_MONTH)}
    )

    form = ReportDateRangeForm(form_data)

    date_range = form.to_date_range() if form.is_valid() else None

    return render(
        request,
        "reports/report_index.html",
        {
            "form": form,
            "date_range": date_range,
        },
    )
