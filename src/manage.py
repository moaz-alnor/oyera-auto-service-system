#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys


def main() -> None:
    """Execute Django administrative commands."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django could not be imported. Confirm that it is installed "
            "and that the virtual environment is active."
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
