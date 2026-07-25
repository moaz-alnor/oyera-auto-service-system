"""Constants and permission identifiers for billing workflows."""

from enum import StrEnum

from django.db import models


class InvoiceStatus(models.TextChoices):
    """Identify the lifecycle state of an invoice."""

    DRAFT = "DRAFT", "Draft"
    ISSUED = "ISSUED", "Issued"
    PARTIALLY_PAID = (
        "PARTIALLY_PAID",
        "Partially paid",
    )
    PAID = "PAID", "Paid"
    VOIDED = "VOIDED", "Voided"


class PaymentStatus(models.TextChoices):
    """Identify whether a payment remains financially active."""

    POSTED = "POSTED", "Posted"
    VOIDED = "VOIDED", "Voided"


class PaymentMethod(models.TextChoices):
    """Identify how the customer made a payment."""

    CASH = "CASH", "Cash"
    MOBILE_MONEY = "MOBILE_MONEY", "Mobile money"
    CARD = "CARD", "Card"
    BANK_TRANSFER = (
        "BANK_TRANSFER",
        "Bank transfer",
    )
    OTHER = "OTHER", "Other"


class BillingPermissionName(StrEnum):
    """Identify billing permissions used by the application."""

    VIEW_INVOICE = "billing.view_invoice"
    ADD_INVOICE = "billing.add_invoice"
    ISSUE_INVOICE = "billing.issue_invoice"
    VOID_INVOICE = "billing.void_invoice"

    VIEW_PAYMENT = "billing.view_payment"
    RECORD_PAYMENT = "billing.record_payment"
    VOID_PAYMENT = "billing.void_payment"
