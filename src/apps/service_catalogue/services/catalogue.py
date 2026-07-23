"""Application services for service-catalogue operations."""

from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.service_catalogue.constants import (
    ServicePermissionName,
)
from apps.service_catalogue.models import (
    Service,
    ServiceApplicability,
    ServicePrice,
)
from apps.vehicles.constants import VehicleCategory


@dataclass(frozen=True, slots=True)
class CreateServiceCommand:
    """Contain validated input for creating a catalogue service."""

    code: str
    name: str
    applicable_categories: tuple[VehicleCategory, ...]
    initial_price: Decimal
    description: str = ""
    estimated_duration_minutes: int | None = None
    currency: str = "UGX"
    price_notes: str = ""


@dataclass(frozen=True, slots=True)
class ChangeServicePriceCommand:
    """Contain information for a service price change."""

    amount: Decimal
    currency: str = "UGX"
    notes: str = ""


def _require_permission(
    *,
    actor: User,
    permission: ServicePermissionName,
) -> None:
    """Require an employee to hold a catalogue permission."""

    if not actor.has_perm(permission.value):
        raise PermissionDenied(
            "You do not have permission to perform this service-catalogue action."
        )


def _normalize_categories(
    categories: tuple[VehicleCategory, ...],
) -> tuple[VehicleCategory, ...]:
    """Return unique categories while preserving input order."""

    unique_categories = tuple(dict.fromkeys(categories))

    if not unique_categories:
        raise ValidationError(
            {
                "applicable_categories": (
                    "Select at least one applicable vehicle category."
                )
            }
        )

    return unique_categories


@transaction.atomic
def create_service(
    *,
    actor: User,
    command: CreateServiceCommand,
) -> Service:
    """Create a service with applicability and an initial price.

    Args:
        actor: Authenticated employee creating the service.
        command: Service definition and initial-price information.

    Returns:
        The newly created service.

    Raises:
        PermissionDenied: If the employee cannot create services.
        ValidationError: If catalogue information is invalid.
    """

    _require_permission(
        actor=actor,
        permission=ServicePermissionName.ADD_SERVICE,
    )

    categories = _normalize_categories(command.applicable_categories)

    service = Service(
        code=command.code,
        name=command.name,
        description=command.description.strip(),
        estimated_duration_minutes=(command.estimated_duration_minutes),
        created_by=actor,
        updated_by=actor,
    )

    service.full_clean()
    service.save()

    for category in categories:
        applicability = ServiceApplicability(
            service=service,
            vehicle_category=category,
        )
        applicability.full_clean()
        applicability.save()

    price = ServicePrice(
        service=service,
        amount=command.initial_price,
        currency=command.currency,
        changed_by=actor,
        notes=command.price_notes.strip(),
    )
    price.full_clean()
    price.save()

    return service


@transaction.atomic
def change_service_price(
    *,
    actor: User,
    service_id: int,
    command: ChangeServicePriceCommand,
) -> ServicePrice:
    """Close the current price and create a new price period.

    Args:
        actor: Authenticated employee changing the price.
        service_id: Primary key of the service.
        command: New price information.

    Returns:
        The new current price.

    Raises:
        PermissionDenied: If the employee cannot change prices.
        Service.DoesNotExist: If the service does not exist.
        ValidationError: If the service or price state is invalid.
    """

    _require_permission(
        actor=actor,
        permission=(ServicePermissionName.CHANGE_SERVICE_PRICE),
    )

    service = Service.objects.select_for_update().get(pk=service_id)

    if not service.is_active:
        raise ValidationError(
            {"service": ("The price of an inactive service cannot be changed.")}
        )

    current_price = (
        ServicePrice.objects.select_for_update()
        .filter(
            service=service,
            effective_until__isnull=True,
        )
        .first()
    )

    normalized_currency = command.currency.strip().upper()

    if (
        current_price is not None
        and current_price.amount == command.amount
        and current_price.currency == normalized_currency
    ):
        raise ValidationError(
            {"amount": ("The new service price must differ from the current price.")}
        )

    change_time = timezone.now()

    if current_price is not None:
        current_price.effective_until = change_time
        current_price.full_clean()
        current_price.save(
            update_fields=(
                "effective_until",
                "updated_at",
            )
        )

    new_price = ServicePrice(
        service=service,
        amount=command.amount,
        currency=normalized_currency,
        effective_from=change_time,
        changed_by=actor,
        notes=command.notes.strip(),
    )
    new_price.full_clean()
    new_price.save()

    return new_price
