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
class UpdateServiceCommand:
    """Contain validated replacement service information."""

    code: str
    name: str
    applicable_categories: tuple[VehicleCategory, ...]
    description: str = ""
    estimated_duration_minutes: int | None = None


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
def update_service(
    *,
    actor: User,
    service_id: int,
    command: UpdateServiceCommand,
) -> Service:
    """Update a service definition without changing price history.

    Args:
        actor: Authenticated employee performing the update.
        service_id: Primary key of the service.
        command: Replacement service information.

    Returns:
        The updated service.

    Raises:
        PermissionDenied: If the employee cannot update services.
        ValidationError: If the service information is invalid.
    """

    _require_permission(
        actor=actor,
        permission=ServicePermissionName.CHANGE_SERVICE,
    )

    categories = _normalize_categories(command.applicable_categories)

    service = Service.objects.select_for_update().get(pk=service_id)

    service.code = command.code
    service.name = command.name
    service.description = command.description.strip()
    service.estimated_duration_minutes = command.estimated_duration_minutes
    service.updated_by = actor

    service.full_clean()
    service.save(
        update_fields=(
            "code",
            "normalized_code",
            "name",
            "description",
            "estimated_duration_minutes",
            "updated_by",
            "updated_at",
        )
    )

    existing_categories = set(
        ServiceApplicability.objects.select_for_update()
        .filter(service=service)
        .values_list(
            "vehicle_category",
            flat=True,
        )
    )
    requested_categories = {category.value for category in categories}

    removed_categories = existing_categories - requested_categories

    if removed_categories:
        ServiceApplicability.objects.filter(
            service=service,
            vehicle_category__in=removed_categories,
        ).delete()

    for category in categories:
        if category.value in existing_categories:
            continue

        applicability = ServiceApplicability(
            service=service,
            vehicle_category=category,
        )
        applicability.full_clean()
        applicability.save()

    return service


@transaction.atomic
def deactivate_service(
    *,
    actor: User,
    service_id: int,
) -> Service:
    """Deactivate a service without deleting its price history."""

    _require_permission(
        actor=actor,
        permission=(ServicePermissionName.DEACTIVATE_SERVICE),
    )

    service = Service.objects.select_for_update().get(pk=service_id)

    if not service.is_active:
        return service

    service.is_active = False
    service.updated_by = actor
    service.save(
        update_fields=(
            "is_active",
            "updated_by",
            "updated_at",
        )
    )

    return service


@transaction.atomic
def reactivate_service(
    *,
    actor: User,
    service_id: int,
) -> Service:
    """Reactivate a complete and usable catalogue service."""

    _require_permission(
        actor=actor,
        permission=(ServicePermissionName.REACTIVATE_SERVICE),
    )

    service = Service.objects.select_for_update().get(pk=service_id)

    if service.is_active:
        return service

    has_applicability = ServiceApplicability.objects.filter(service=service).exists()

    if not has_applicability:
        raise ValidationError(
            {
                "is_active": (
                    "This service cannot be reactivated until at "
                    "least one vehicle category is configured."
                )
            }
        )

    has_current_price = ServicePrice.objects.filter(
        service=service,
        effective_until__isnull=True,
    ).exists()

    if not has_current_price:
        raise ValidationError(
            {
                "is_active": (
                    "This service cannot be reactivated without a current price."
                )
            }
        )

    service.is_active = True
    service.updated_by = actor
    service.save(
        update_fields=(
            "is_active",
            "updated_by",
            "updated_at",
        )
    )

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
