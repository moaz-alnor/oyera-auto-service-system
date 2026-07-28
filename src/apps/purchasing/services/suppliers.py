"""Application services for supplier management."""

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.accounts.models import User
from apps.purchasing.constants import (
    PurchasingPermissionName,
)
from apps.purchasing.models import Supplier


@dataclass(frozen=True, slots=True)
class RegisterSupplierCommand:
    """Contain input for registering a supplier."""

    code: str
    name: str
    contact_name: str = ""
    phone_number: str = ""
    email: str = ""
    address: str = ""
    tax_identifier: str = ""
    payment_terms_days: int = 0
    preferred_currency: str = "UGX"
    notes: str = ""


@dataclass(frozen=True, slots=True)
class UpdateSupplierCommand:
    """Contain replacement supplier information."""

    code: str
    name: str
    contact_name: str = ""
    phone_number: str = ""
    email: str = ""
    address: str = ""
    tax_identifier: str = ""
    payment_terms_days: int = 0
    preferred_currency: str = "UGX"
    notes: str = ""


def _require_permission(
    *,
    actor: User,
    permission: PurchasingPermissionName,
) -> None:
    """Require one purchasing permission."""

    if not actor.has_perm(permission.value):
        raise PermissionDenied(
            "You do not have permission to perform this supplier action."
        )


@transaction.atomic
def register_supplier(
    *,
    actor: User,
    command: RegisterSupplierCommand,
) -> Supplier:
    """Register a supplier and generate its number."""

    _require_permission(
        actor=actor,
        permission=(PurchasingPermissionName.ADD_SUPPLIER),
    )

    supplier = Supplier(
        code=command.code,
        name=command.name,
        contact_name=command.contact_name,
        phone_number=command.phone_number,
        email=command.email,
        address=command.address,
        tax_identifier=command.tax_identifier,
        payment_terms_days=(command.payment_terms_days),
        preferred_currency=(command.preferred_currency),
        notes=command.notes,
        created_by=actor,
        updated_by=actor,
    )
    supplier.full_clean()
    supplier.save()

    if supplier.pk is None:
        raise RuntimeError("Supplier registration completed without a primary key.")

    supplier.supplier_number = f"SUP-{supplier.pk:06d}"
    supplier.save(
        update_fields=(
            "supplier_number",
            "updated_at",
        )
    )

    return supplier


@transaction.atomic
def update_supplier(
    *,
    actor: User,
    supplier_id: int,
    command: UpdateSupplierCommand,
) -> Supplier:
    """Update an existing supplier."""

    _require_permission(
        actor=actor,
        permission=(PurchasingPermissionName.CHANGE_SUPPLIER),
    )

    supplier = Supplier.objects.select_for_update().get(pk=supplier_id)

    supplier.code = command.code
    supplier.name = command.name
    supplier.contact_name = command.contact_name
    supplier.phone_number = command.phone_number
    supplier.email = command.email
    supplier.address = command.address
    supplier.tax_identifier = command.tax_identifier
    supplier.payment_terms_days = command.payment_terms_days
    supplier.preferred_currency = command.preferred_currency
    supplier.notes = command.notes
    supplier.updated_by = actor

    supplier.full_clean()
    supplier.save(
        update_fields=(
            "code",
            "normalized_code",
            "name",
            "normalized_name",
            "contact_name",
            "phone_number",
            "email",
            "address",
            "tax_identifier",
            "payment_terms_days",
            "preferred_currency",
            "notes",
            "updated_by",
            "updated_at",
        )
    )

    return supplier


@transaction.atomic
def deactivate_supplier(
    *,
    actor: User,
    supplier_id: int,
) -> Supplier:
    """Deactivate a supplier without deleting history."""

    _require_permission(
        actor=actor,
        permission=(PurchasingPermissionName.DEACTIVATE_SUPPLIER),
    )

    supplier = Supplier.objects.select_for_update().get(pk=supplier_id)

    if not supplier.is_active:
        return supplier

    supplier.is_active = False
    supplier.updated_by = actor
    supplier.save(
        update_fields=(
            "is_active",
            "updated_by",
            "updated_at",
        )
    )

    return supplier


@transaction.atomic
def reactivate_supplier(
    *,
    actor: User,
    supplier_id: int,
) -> Supplier:
    """Reactivate a previously inactive supplier."""

    _require_permission(
        actor=actor,
        permission=(PurchasingPermissionName.REACTIVATE_SUPPLIER),
    )

    supplier = Supplier.objects.select_for_update().get(pk=supplier_id)

    if supplier.is_active:
        return supplier

    supplier.is_active = True
    supplier.updated_by = actor
    supplier.save(
        update_fields=(
            "is_active",
            "updated_by",
            "updated_at",
        )
    )

    return supplier
