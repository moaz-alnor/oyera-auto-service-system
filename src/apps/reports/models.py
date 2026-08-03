"""Permission definitions for operational reports."""

from django.db import models


class ReportAccess(models.Model):
    """Provide content-type permissions without stored records."""

    class Meta:
        """Configure reporting permissions."""

        managed = False
        default_permissions = ()
        verbose_name = "report access"
        verbose_name_plural = "report access"

        permissions = (
            (
                "access_reports",
                "Can access operational reports",
            ),
            (
                "view_customer_finance_report",
                "Can view the customer finance report",
            ),
            (
                "view_workshop_report",
                "Can view the workshop operations report",
            ),
            (
                "view_inventory_report",
                "Can view the inventory report",
            ),
            (
                "view_purchasing_report",
                "Can view the purchasing report",
            ),
            (
                "export_reports",
                "Can export operational reports",
            ),
        )
