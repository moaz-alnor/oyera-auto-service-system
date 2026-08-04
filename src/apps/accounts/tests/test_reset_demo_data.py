"""Safety tests for the destructive demo-data command."""

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings


@override_settings(DEBUG=False)
def test_reset_demo_data_is_blocked_outside_debug_mode() -> None:
    """Production-like settings must reject the destructive command."""
    with pytest.raises(
        CommandError,
        match="restricted to DEBUG mode",
    ):
        call_command(
            "reset_demo_data",
            yes=True,
            verbosity=0,
        )


@override_settings(DEBUG=True)
def test_reset_demo_data_requires_explicit_confirmation() -> None:
    """Debug mode alone must not authorize deletion."""
    with pytest.raises(
        CommandError,
        match="Run again with --yes",
    ):
        call_command(
            "reset_demo_data",
            verbosity=0,
        )
