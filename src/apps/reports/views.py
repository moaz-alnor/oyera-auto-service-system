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
from apps.reports.exports.inventory_activity import (
    build_inventory_activity_csv,
    inventory_activity_csv_filename,
)
from apps.reports.exports.workshop_operations import (
    build_workshop_operations_csv,
    workshop_operations_csv_filename,
)
from apps.reports.forms import ReportDateRangeForm
from apps.reports.selectors.customer_finance import (
    get_customer_finance_report,
)
from apps.reports.selectors.inventory_activity import (
    get_inventory_activity_report,
)
from apps.reports.selectors.workshop_operations import (
    get_workshop_operations_report,
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


@employee_permission_required(ReportPermissionName.VIEW_WORKSHOP_REPORT.value)
def workshop_operations_report(
    request: HttpRequest,
) -> HttpResponse:
    """Display vehicle and workshop activity."""

    form = ReportDateRangeForm(_report_form_data(request))

    date_range = form.to_date_range() if form.is_valid() else None

    report = (
        get_workshop_operations_report(date_range=date_range)
        if date_range is not None
        else None
    )

    return render(
        request,
        "reports/workshop_operations.html",
        {
            "form": form,
            "date_range": date_range,
            "report": report,
        },
    )


@employee_permission_required(ReportPermissionName.EXPORT_REPORTS.value)
@employee_permission_required(ReportPermissionName.VIEW_WORKSHOP_REPORT.value)
def workshop_operations_export(
    request: HttpRequest,
) -> HttpResponse:
    """Download the filtered workshop report."""

    form = ReportDateRangeForm(_report_form_data(request))

    if not form.is_valid():
        return HttpResponseBadRequest(
            "Invalid workshop operations report filters.",
            content_type=("text/plain; charset=utf-8"),
        )

    date_range = form.to_date_range()

    report = get_workshop_operations_report(date_range=date_range)

    filename = workshop_operations_csv_filename(date_range=date_range)

    response = HttpResponse(
        build_workshop_operations_csv(
            report=report,
            date_range=date_range,
        ),
        content_type=("text/csv; charset=utf-8"),
    )

    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["X-Content-Type-Options"] = "nosniff"

    return response


@employee_permission_required(ReportPermissionName.VIEW_INVENTORY_REPORT.value)
def inventory_activity_report(
    request: HttpRequest,
) -> HttpResponse:
    """Display Inventory movement and stock-risk activity."""

    form = ReportDateRangeForm(_report_form_data(request))

    date_range = form.to_date_range() if form.is_valid() else None

    report = (
        get_inventory_activity_report(date_range=date_range)
        if date_range is not None
        else None
    )

    return render(
        request,
        "reports/inventory_activity.html",
        {
            "form": form,
            "date_range": date_range,
            "report": report,
        },
    )


@employee_permission_required(ReportPermissionName.EXPORT_REPORTS.value)
@employee_permission_required(ReportPermissionName.VIEW_INVENTORY_REPORT.value)
def inventory_activity_export(
    request: HttpRequest,
) -> HttpResponse:
    """Download the filtered Inventory report."""

    form = ReportDateRangeForm(_report_form_data(request))

    if not form.is_valid():
        return HttpResponseBadRequest(
            "Invalid Inventory activity report filters.",
            content_type=("text/plain; charset=utf-8"),
        )

    date_range = form.to_date_range()

    report = get_inventory_activity_report(date_range=date_range)

    filename = inventory_activity_csv_filename(date_range=date_range)

    response = HttpResponse(
        build_inventory_activity_csv(
            report=report,
            date_range=date_range,
        ),
        content_type=("text/csv; charset=utf-8"),
    )

    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["X-Content-Type-Options"] = "nosniff"

    return response
