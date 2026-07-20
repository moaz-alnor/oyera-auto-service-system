"""Tests for customer-domain models."""

import pytest

from apps.accounts.models import User
from apps.customers.constants import CustomerType
from apps.customers.models import Customer


@pytest.mark.django_db
def test_customer_information_is_normalized() -> None:
    """Normalize customer names, phone numbers, and emails."""

    actor = User.objects.create_user(
        username="test.employee",
        password="Strong-Test-Password-2026",
    )

    customer = Customer(
        customer_type=CustomerType.INDIVIDUAL,
        name="  Daniel    Kato  ",
        phone_number="+256 700-123-456",
        email="  DANIEL@EXAMPLE.COM ",
        created_by=actor,
    )

    customer.full_clean()

    assert customer.name == "Daniel Kato"
    assert customer.normalized_phone_number == "256700123456"
    assert customer.email == "daniel@example.com"


@pytest.mark.django_db
def test_unsaved_customer_displays_name() -> None:
    """Display the name before a customer number is generated."""

    actor = User.objects.create_user(
        username="test.employee",
        password="Strong-Test-Password-2026",
    )

    customer = Customer(
        customer_type=CustomerType.COMPANY,
        name="Oyera Transport Ltd",
        phone_number="0700123456",
        created_by=actor,
    )

    assert str(customer) == "Oyera Transport Ltd"
