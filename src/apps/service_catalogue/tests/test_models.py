"""Tests for service-catalogue models."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.service_catalogue.models import Service, ServicePrice


@pytest.fixture
def actor() -> User:
    """Create an employee for catalogue model tests."""

    return User.objects.create_user(
        username="catalogue.model.employee",
        password="Strong-Test-Password-2026",
    )


@pytest.mark.django_db
def test_service_information_is_normalized(
    actor: User,
) -> None:
    """Normalize service codes and display names."""

    service = Service(
        code=" oil_change ",
        name="  Engine   Oil Change  ",
        created_by=actor,
        updated_by=actor,
    )

    service.full_clean()

    assert service.code == "OIL-CHANGE"
    assert service.normalized_code == "OILCHANGE"
    assert service.name == "Engine Oil Change"


@pytest.mark.django_db
def test_service_price_rejects_non_positive_amount(
    actor: User,
) -> None:
    """Reject zero or negative catalogue prices."""

    service = Service.objects.create(
        code="OIL-CHANGE",
        normalized_code="OILCHANGE",
        name="Engine Oil Change",
        created_by=actor,
        updated_by=actor,
    )

    price = ServicePrice(
        service=service,
        amount=Decimal("0.00"),
        currency="UGX",
        changed_by=actor,
    )

    with pytest.raises(ValidationError):
        price.full_clean()
