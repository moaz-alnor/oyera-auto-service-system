"""Tests for reusable employee authorization controls."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.core.exceptions import PermissionDenied
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
)
from django.urls import reverse

from apps.accounts.constants import RoleName
from apps.accounts.decorators import employee_permission_required
from apps.accounts.services.roles import ensure_default_roles


@employee_permission_required("accounts.view_user")
def protected_view(request: HttpRequest) -> HttpResponse:
    """Provide a small protected view used by authorization tests."""

    return HttpResponse("Permission granted.")


def test_anonymous_user_is_redirected_to_login(rf) -> None:
    """Redirect anonymous users before evaluating permissions."""

    request = rf.get("/protected/")
    request.user = AnonymousUser()

    response = protected_view(request)

    expected_url = f"{reverse('accounts:login')}?next=/protected/"

    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == 302
    assert response.url == expected_url


@pytest.mark.django_db
def test_employee_without_permission_is_denied(rf) -> None:
    """Raise PermissionDenied for an unauthorized employee."""

    user_model = get_user_model()
    employee = user_model.objects.create_user(
        username="unauthorized.employee",
        password="Strong-Test-Password-2026",
    )

    request = rf.get("/protected/")
    request.user = employee

    with pytest.raises(PermissionDenied):
        protected_view(request)


@pytest.mark.django_db
def test_administrator_group_grants_permission(rf) -> None:
    """Allow an administrator through group-based permissions."""

    ensure_default_roles()

    user_model = get_user_model()
    employee = user_model.objects.create_user(
        username="administrator.employee",
        password="Strong-Test-Password-2026",
    )

    administrator = Group.objects.get(name=RoleName.ADMINISTRATOR.value)
    employee.groups.add(administrator)

    request = rf.get("/protected/")
    request.user = employee

    response = protected_view(request)

    assert isinstance(response, HttpResponse)
    assert response.status_code == 200
    assert response.content == b"Permission granted."
