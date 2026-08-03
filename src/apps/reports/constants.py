"""Constants and permissions for operational reports."""

from enum import StrEnum

from django.db import models


class ReportPeriodPreset(models.TextChoices):
    """Identify supported report date presets."""

    TODAY = "TODAY", "Today"
    THIS_WEEK = "THIS_WEEK", "This week"
    THIS_MONTH = "THIS_MONTH", "This month"
    CUSTOM = "CUSTOM", "Custom range"


class ReportPermissionName(StrEnum):
    """Identify reporting permissions used by the system."""

    ACCESS_REPORTS = "reports.access_reports"

    VIEW_CUSTOMER_FINANCE_REPORT = "reports.view_customer_finance_report"
    VIEW_WORKSHOP_REPORT = "reports.view_workshop_report"
    VIEW_INVENTORY_REPORT = "reports.view_inventory_report"
    VIEW_PURCHASING_REPORT = "reports.view_purchasing_report"

    EXPORT_REPORTS = "reports.export_reports"
