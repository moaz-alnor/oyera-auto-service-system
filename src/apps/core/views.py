"""HTTP views for shared application pages."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.billing.constants import BillingPermissionName
from apps.core.selectors import (
    get_financial_dashboard_metrics,
    get_operational_dashboard_alerts,
    get_operational_dashboard_metrics,
)
from apps.purchasing.constants import (
    PurchasingPermissionName,
)


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """Display the authenticated employee dashboard."""

    can_view_customer_finance = request.user.has_perm(
        BillingPermissionName.VIEW_INVOICE.value
    )
    can_view_supplier_finance = request.user.has_perm(
        PurchasingPermissionName.VIEW_SUPPLIER_INVOICE.value
    )

    return render(
        request,
        "core/dashboard.html",
        {
            "metrics": (get_operational_dashboard_metrics()),
            "alerts": (get_operational_dashboard_alerts()),
            "financial_metrics": (
                get_financial_dashboard_metrics(
                    include_customer_finance=(can_view_customer_finance),
                    include_supplier_finance=(can_view_supplier_finance),
                )
            ),
        },
    )
