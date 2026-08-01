"""HTTP views for operational reports."""

from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
)
from django.shortcuts import render

from apps.accounts.decorators import (
    employee_permission_required,
)
from apps.reports.constants import (
    ReportPeriodPreset,
    ReportPermissionName,
)
from apps.reports.exports.customer_finance import (
    build_customer_finance_csv,
    customer_finance_csv_filename,
)
from apps.reports.forms import ReportDateRangeForm
from apps.reports.selectors.customer_finance import (
    get_customer_finance_report,
)


def _report_form_data(
    request: HttpRequest,
):
    """Return request filters or the default period."""

    if request.GET:
        return request.GET

    return {
        "preset": ReportPeriodPreset.THIS_MONTH,
    }


@employee_permission_required(ReportPermissionName.ACCESS_REPORTS.value)
def report_index(
    request: HttpRequest,
) -> HttpResponse:
    """Display the operational report catalogue."""

    form = ReportDateRangeForm(_report_form_data(request))

    date_range = form.to_date_range() if form.is_valid() else None

    return render(
        request,
        "reports/report_index.html",
        {
            "form": form,
            "date_range": date_range,
        },
    )


@employee_permission_required(ReportPermissionName.VIEW_CUSTOMER_FINANCE_REPORT.value)
def customer_finance_report(
    request: HttpRequest,
) -> HttpResponse:
    """Display customer invoice and payment activity."""

    form = ReportDateRangeForm(_report_form_data(request))

    date_range = form.to_date_range() if form.is_valid() else None

    report = (
        get_customer_finance_report(date_range=date_range)
        if date_range is not None
        else None
    )

    return render(
        request,
        "reports/customer_finance.html",
        {
            "form": form,
            "date_range": date_range,
            "report": report,
        },
    )


@employee_permission_required(ReportPermissionName.EXPORT_REPORTS.value)
@employee_permission_required(ReportPermissionName.VIEW_CUSTOMER_FINANCE_REPORT.value)
def customer_finance_export(
    request: HttpRequest,
) -> HttpResponse:
    """Download the filtered customer finance report."""

    form = ReportDateRangeForm(_report_form_data(request))

    if not form.is_valid():
        return HttpResponseBadRequest(
            "Invalid customer finance report filters.",
            content_type=("text/plain; charset=utf-8"),
        )

    date_range = form.to_date_range()

    report = get_customer_finance_report(date_range=date_range)

    filename = customer_finance_csv_filename(date_range=date_range)

    response = HttpResponse(
        build_customer_finance_csv(
            report=report,
            date_range=date_range,
        ),
        content_type=("text/csv; charset=utf-8"),
    )

    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["X-Content-Type-Options"] = "nosniff"

    return response
