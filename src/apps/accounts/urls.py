"""URL routes for employee authentication and account access."""

from django.contrib.auth import views as auth_views
from django.urls import path

from apps.accounts.forms import EmployeeAuthenticationForm

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            authentication_form=EmployeeAuthenticationForm,
            template_name="registration/login.html",
        ),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
]
