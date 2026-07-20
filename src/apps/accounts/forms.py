"""Forms used by the employee authentication interface."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm


class EmployeeAuthenticationForm(AuthenticationForm):
    """Authenticate an employee using their username and password."""

    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "autofocus": True,
                "class": "form-control",
                "placeholder": "Enter your username",
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "class": "form-control",
                "placeholder": "Enter your password",
            }
        ),
    )
