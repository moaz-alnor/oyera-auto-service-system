"""Tests for the custom employee user model."""

import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_project_uses_custom_user_model() -> None:
    """Confirm that Django uses the accounts.User model."""

    user_model = get_user_model()

    assert user_model._meta.label == "accounts.User"


@pytest.mark.django_db
def test_user_password_is_hashed() -> None:
    """Confirm that user passwords are never stored as readable text."""

    user_model = get_user_model()

    user = user_model.objects.create_user(
        username="test.employee",
        password="Strong-Test-Password-2026",
    )

    assert user.password != "Strong-Test-Password-2026"
    assert user.check_password("Strong-Test-Password-2026")


@pytest.mark.django_db
def test_user_display_name_prefers_full_name() -> None:
    """Return the full employee name when it is available."""

    user_model = get_user_model()

    user = user_model(
        username="test.employee",
        first_name="Test",
        last_name="Employee",
    )

    assert str(user) == "Test Employee"


@pytest.mark.django_db
def test_user_display_name_falls_back_to_username() -> None:
    """Return the username when the employee has no recorded name."""

    user_model = get_user_model()

    user = user_model(username="test.employee")

    assert str(user) == "test.employee"
