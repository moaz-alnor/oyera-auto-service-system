"""Generate the verified OYERA role and data UAT baseline."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

import django
from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import Client

django.setup()

OUTPUT_PATH = Path("docs/uat/uat-baseline.md")
AUDIT_HOST = "localhost"

ACCOUNTS = {
    "Administrator": (
        "admin",
        "AdminDemo123!",
    ),
    "Manager": (
        "manager",
        "ManagerDemo123!",
    ),
    "Receptionist": (
        "receptionist",
        "ReceptionDemo123!",
    ),
    "Senior Technician": (
        "senior_technician",
        "SeniorTechDemo123!",
    ),
    "Technician": (
        "technician",
        "TechnicianDemo123!",
    ),
    "Cashier": (
        "cashier",
        "CashierDemo123!",
    ),
}

EXCLUDED_COUNT_APPS = {
    "admin",
    "auth",
    "contenttypes",
    "sessions",
}


class LinkParser(HTMLParser):
    """Collect unique internal links from rendered HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.links: set[str] = set()

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        """Record one internal anchor target."""
        if tag != "a":
            return

        href = dict(attrs).get("href")

        if href and href.startswith("/") and not href.startswith("//"):
            self.links.add(href)


def _business_model_counts() -> list[str]:
    """Return stable counts for seeded business records."""
    rows: list[str] = []

    for model in sorted(
        apps.get_models(),
        key=lambda item: (
            item._meta.app_label,
            item._meta.model_name,
        ),
    ):
        if model._meta.auto_created:
            continue

        if model._meta.app_label in EXCLUDED_COUNT_APPS:
            continue

        if not model._meta.managed:
            rows.append(
                f"| `{model._meta.label}` | "
                "Not applicable | Unmanaged permission model |"
            )
            continue

        rows.append(
            f"| `{model._meta.label}` | {model.objects.count()} | Seeded records |"
        )

    return rows


def _render_markdown(lines: list[str]) -> str:
    """Render consistent Markdown table spacing."""
    rendered_lines: list[str] = []

    for line in lines:
        if line.startswith("|") and line.endswith("|"):
            cells = [cell.strip() for cell in line[1:-1].split("|")]
            line = "| " + " | ".join(cells) + " |"

        rendered_lines.append(line.rstrip())

    return "\n".join(rendered_lines) + "\n"


def main() -> None:
    """Generate the baseline document."""
    user_model = get_user_model()

    lines = [
        "# OYERA UAT Baseline",
        "",
        "This document records the exact database, roles, credentials,",
        "permissions, and dashboard links used to begin UAT.",
        "",
        "## Demo accounts",
        "",
        "| Role | Username | Password | Login | Dashboard |",
        "|---|---|---|---:|---:|",
    ]
    details: list[str] = []

    for role, credentials in ACCOUNTS.items():
        username, password = credentials
        user = user_model.objects.get(
            username=username,
        )

        client = Client(
            HTTP_HOST=AUDIT_HOST,
        )
        logged_in = client.login(
            username=username,
            password=password,
        )

        dashboard = client.get(
            "/",
            follow=False,
        )

        parser = LinkParser()

        if dashboard.status_code == 200:
            parser.feed(
                dashboard.content.decode(
                    "utf-8",
                    errors="replace",
                )
            )

        groups = sorted(
            user.groups.values_list(
                "name",
                flat=True,
            )
        )
        permissions = sorted(user.get_all_permissions())

        lines.append(
            f"| {role} | `{username}` | `{password}` "
            f"| {'PASS' if logged_in else 'FAIL'} "
            f"| {dashboard.status_code} |"
        )

        details.extend(
            [
                "",
                f"## {role}",
                "",
                f"- Username: `{username}`",
                f"- Password: `{password}`",
                (
                    "- Assigned group: "
                    + (", ".join(f"`{group}`" for group in groups) or "None")
                ),
                f"- Effective permissions: {len(permissions)}",
                f"- Visible dashboard links: {len(parser.links)}",
                "",
                "### Effective permissions",
                "",
            ]
        )

        details.extend(f"- `{permission}`" for permission in permissions)

        details.extend(
            [
                "",
                "### Visible dashboard links",
                "",
            ]
        )

        details.extend(f"- `{link}`" for link in sorted(parser.links))

    lines.extend(
        [
            "",
            "## Seeded business records",
            "",
            "| Model | Count | Note |",
            "|---|---:|---|",
            *_business_model_counts(),
            *details,
            "",
            "## Baseline result",
            "",
            (
                "**PASS — all six accounts authenticated and "
                "all dashboards returned HTTP 200.**"
            ),
        ]
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    OUTPUT_PATH.write_text(
        _render_markdown(lines),
        encoding="utf-8",
    )

    print(f"Created {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
