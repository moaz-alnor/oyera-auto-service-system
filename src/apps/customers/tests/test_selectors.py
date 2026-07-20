"""Tests for customer read and search queries."""

import pytest

from apps.accounts.models import User
from apps.customers.constants import CustomerType
from apps.customers.models import Customer
from apps.customers.selectors import (
    find_possible_customer_duplicates,
    search_customers,
)


@pytest.fixture
def employee() -> User:
    """Create an employee used as the customer-record author."""

    return User.objects.create_user(
        username="customer.test.employee",
        password="Strong-Test-Password-2026",
    )


@pytest.fixture
def customers(employee: User) -> tuple[Customer, Customer]:
    """Create active and inactive customers for selector tests."""

    active_customer = Customer.objects.create(
        customer_number="CUS-000001",
        customer_type=CustomerType.INDIVIDUAL,
        name="Daniel Kato",
        phone_number="+256 700 123 456",
        normalized_phone_number="256700123456",
        email="daniel@example.com",
        created_by=employee,
        updated_by=employee,
    )

    inactive_customer = Customer.objects.create(
        customer_number="CUS-000002",
        customer_type=CustomerType.COMPANY,
        name="Oyera Transport Ltd",
        phone_number="0770 555 123",
        normalized_phone_number="0770555123",
        email="office@oyeratransport.com",
        is_active=False,
        created_by=employee,
        updated_by=employee,
    )

    return active_customer, inactive_customer


@pytest.mark.django_db
def test_search_returns_active_customers_by_name(
    customers: tuple[Customer, Customer],
) -> None:
    """Search active customer records using a partial name."""

    active_customer, _ = customers

    results = search_customers(query="Daniel")

    assert list(results) == [active_customer]


@pytest.mark.django_db
def test_search_normalizes_partial_phone_input(
    customers: tuple[Customer, Customer],
) -> None:
    """Find customers despite formatting in the search value."""

    active_customer, _ = customers

    results = search_customers(query="700-123")

    assert list(results) == [active_customer]


@pytest.mark.django_db
def test_search_excludes_inactive_customers_by_default(
    customers: tuple[Customer, Customer],
) -> None:
    """Hide inactive customers from normal operational searches."""

    _, inactive_customer = customers

    default_results = search_customers(query="Oyera")
    historical_results = search_customers(
        query="Oyera",
        include_inactive=True,
    )

    assert inactive_customer not in default_results
    assert inactive_customer in historical_results


@pytest.mark.django_db
def test_duplicate_detection_uses_phone_name_and_email(
    customers: tuple[Customer, Customer],
) -> None:
    """Return existing records that match proposed customer details."""

    active_customer, _ = customers

    results = find_possible_customer_duplicates(
        name="Daniel Kato",
        phone_number="+256-700-123-456",
        email="DANIEL@EXAMPLE.COM",
    )

    assert list(results) == [active_customer]


@pytest.mark.django_db
def test_duplicate_detection_can_exclude_current_customer(
    customers: tuple[Customer, Customer],
) -> None:
    """Avoid treating a customer as their own duplicate."""

    active_customer, _ = customers

    results = find_possible_customer_duplicates(
        name=active_customer.name,
        phone_number=active_customer.phone_number,
        email=active_customer.email,
        exclude_customer_id=active_customer.pk,
    )

    assert not results.exists()
