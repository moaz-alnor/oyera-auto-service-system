"""Tests for customer-management HTTP workflows."""

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.accounts.constants import RoleName
from apps.accounts.models import User
from apps.accounts.services.roles import ensure_default_roles
from apps.customers.constants import CustomerType
from apps.customers.models import Customer
from apps.customers.services.customers import (
    RegisterCustomerCommand,
    register_customer,
)


@pytest.fixture
def receptionist() -> User:
    """Create an employee with customer-management permission."""

    ensure_default_roles()

    employee = User.objects.create_user(
        username="view.receptionist",
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=RoleName.RECEPTIONIST.value))

    return employee


@pytest.fixture
def technician() -> User:
    """Create an employee without customer permissions."""

    ensure_default_roles()

    employee = User.objects.create_user(
        username="view.technician",
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=RoleName.TECHNICIAN.value))

    return employee


@pytest.fixture
def existing_customer(
    receptionist: User,
) -> Customer:
    """Create an existing customer through the application service."""

    return register_customer(
        actor=receptionist,
        command=RegisterCustomerCommand(
            customer_type=CustomerType.INDIVIDUAL,
            name="Daniel Kato",
            phone_number="0700123456",
            email="daniel@example.com",
        ),
    )


@pytest.mark.django_db
def test_customer_list_requires_authentication(client) -> None:
    """Redirect anonymous visitors to employee login."""

    response = client.get(reverse("customers:list"))

    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


@pytest.mark.django_db
def test_receptionist_can_view_customer_list(
    client,
    receptionist: User,
    existing_customer: Customer,
) -> None:
    """Display customer records to an authorized receptionist."""

    client.force_login(receptionist)

    response = client.get(
        reverse("customers:list"),
        {"q": "Daniel"},
    )

    assert response.status_code == 200
    assert existing_customer.name.encode() in response.content


@pytest.mark.django_db
def test_technician_cannot_view_customers(
    client,
    technician: User,
) -> None:
    """Return HTTP 403 for unauthorized technicians."""

    client.force_login(technician)

    response = client.get(reverse("customers:list"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_duplicate_warning_does_not_create_customer(
    client,
    receptionist: User,
    existing_customer: Customer,
) -> None:
    """Require confirmation before creating a possible duplicate."""

    client.force_login(receptionist)

    response = client.post(
        reverse("customers:create"),
        {
            "customer_type": CustomerType.INDIVIDUAL,
            "name": "Daniel Kato",
            "phone_number": "0700 123 456",
            "email": "daniel@example.com",
            "address": "",
            "notes": "",
        },
    )

    assert response.status_code == 200
    assert b"Possible duplicate customer" in response.content
    assert Customer.objects.count() == 1


@pytest.mark.django_db
def test_confirmed_duplicate_can_be_created(
    client,
    receptionist: User,
    existing_customer: Customer,
) -> None:
    """Create a duplicate only after explicit employee confirmation."""

    client.force_login(receptionist)

    response = client.post(
        reverse("customers:create"),
        {
            "customer_type": CustomerType.INDIVIDUAL,
            "name": "Daniel Kato",
            "phone_number": "0700123456",
            "email": "daniel@example.com",
            "address": "",
            "notes": "Confirmed separate customer.",
            "confirm_duplicate": "true",
        },
    )

    assert response.status_code == 302
    assert Customer.objects.count() == 2


@pytest.mark.django_db
def test_customer_detail_is_available(
    client,
    receptionist: User,
    existing_customer: Customer,
) -> None:
    """Display one customer record to authorized staff."""

    client.force_login(receptionist)

    response = client.get(
        reverse(
            "customers:detail",
            args=(existing_customer.pk,),
        )
    )

    customer_number = existing_customer.customer_number

    assert response.status_code == 200
    assert customer_number is not None
    assert customer_number.encode() in response.content
    assert existing_customer.name.encode() in response.content


@pytest.fixture
def administrator() -> User:
    """Create an employee with full customer permissions."""

    ensure_default_roles()

    employee = User.objects.create_user(
        username="view.administrator",
        password="Strong-Test-Password-2026",
    )
    employee.groups.add(Group.objects.get(name=RoleName.ADMINISTRATOR.value))

    return employee


@pytest.mark.django_db
def test_customer_can_be_updated_without_matching_itself(
    client,
    receptionist: User,
    existing_customer: Customer,
) -> None:
    """Save unchanged identifying details without a false warning."""

    client.force_login(receptionist)

    response = client.post(
        reverse(
            "customers:update",
            args=(existing_customer.pk,),
        ),
        {
            "customer_type": CustomerType.INDIVIDUAL,
            "name": "Daniel Kato Updated",
            "phone_number": "0700123456",
            "email": "daniel@example.com",
            "address": "Kampala",
            "notes": "Updated record.",
        },
    )

    existing_customer.refresh_from_db()

    assert response.status_code == 302
    assert existing_customer.name == "Daniel Kato Updated"
    assert existing_customer.address == "Kampala"


@pytest.mark.django_db
def test_technician_cannot_update_customer(
    client,
    technician: User,
    existing_customer: Customer,
) -> None:
    """Return HTTP 403 when a technician opens customer editing."""

    client.force_login(technician)

    response = client.get(
        reverse(
            "customers:update",
            args=(existing_customer.pk,),
        )
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_deactivation_requires_post(
    client,
    administrator: User,
    existing_customer: Customer,
) -> None:
    """Reject GET requests to the deactivation endpoint."""

    client.force_login(administrator)

    response = client.get(
        reverse(
            "customers:deactivate",
            args=(existing_customer.pk,),
        )
    )

    assert response.status_code == 405


@pytest.mark.django_db
def test_administrator_can_deactivate_customer(
    client,
    administrator: User,
    existing_customer: Customer,
) -> None:
    """Deactivate a customer through a protected POST request."""

    client.force_login(administrator)

    response = client.post(
        reverse(
            "customers:deactivate",
            args=(existing_customer.pk,),
        )
    )

    existing_customer.refresh_from_db()

    assert response.status_code == 302
    assert not existing_customer.is_active


@pytest.mark.django_db
def test_administrator_can_reactivate_customer(
    client,
    administrator: User,
    existing_customer: Customer,
) -> None:
    """Reactivate a previously inactive customer."""

    existing_customer.is_active = False
    existing_customer.save(
        update_fields=(
            "is_active",
            "updated_at",
        )
    )

    client.force_login(administrator)

    response = client.post(
        reverse(
            "customers:reactivate",
            args=(existing_customer.pk,),
        )
    )

    existing_customer.refresh_from_db()

    assert response.status_code == 302
    assert existing_customer.is_active
