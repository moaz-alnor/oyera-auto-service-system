"""Constants and permission identifiers for quotations."""

from enum import StrEnum

from django.db import models


class QuotationStatus(models.TextChoices):
    """Identify the lifecycle state of a quotation revision."""

    DRAFT = "DRAFT", "Draft"
    SENT = "SENT", "Sent to customer"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class CustomerDecisionMethod(models.TextChoices):
    """Identify how a customer communicated their decision."""

    IN_PERSON = "IN_PERSON", "In person"
    PHONE = "PHONE", "Phone"
    EMAIL = "EMAIL", "Email"
    WHATSAPP = "WHATSAPP", "WhatsApp"
    SIGNED_DOCUMENT = "SIGNED_DOCUMENT", "Signed document"
    OTHER = "OTHER", "Other"


class QuotationPermissionName(StrEnum):
    """Identify quotation permissions used by the application."""

    VIEW_QUOTATION = "quotations.view_quotation"
    ADD_QUOTATION = "quotations.add_quotation"
    CHANGE_QUOTATION = "quotations.change_quotation"

    SUBMIT_QUOTATION = "quotations.submit_quotation"
    APPROVE_QUOTATION = "quotations.approve_quotation"
    REJECT_QUOTATION = "quotations.reject_quotation"
    REVISE_QUOTATION = "quotations.revise_quotation"
