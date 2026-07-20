"""Create the default employee roles required by the application."""

from django.core.management.base import BaseCommand

from apps.accounts.services.roles import ensure_default_roles


class Command(BaseCommand):
    """Create missing default roles without duplicating existing roles."""

    help = "Create the default Oyera Auto Service employee roles."

    def handle(self, *args: object, **options: object) -> None:
        """Execute the role-seeding operation."""

        result = ensure_default_roles()

        for role_name in result.created_roles:
            self.stdout.write(self.style.SUCCESS(f"Created role: {role_name}"))

        for role_name in result.existing_roles:
            self.stdout.write(f"Role already exists: {role_name}")

        self.stdout.write(self.style.SUCCESS("Default role configuration is complete."))
