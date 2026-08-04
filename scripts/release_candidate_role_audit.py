"""Run strict read-only role navigation checks against demo data."""

from __future__ import annotations

import logging
from html.parser import HTMLParser
from pathlib import Path

import django
from django.conf import settings
from django.test import Client

django.setup()

REPORT_PATH = Path("/tmp/oyera-role-navigation-audit.md")
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

SCENARIO_PATHS = (
    "/purchasing/purchase-orders/",
    "/purchasing/goods-receipts/",
    "/purchasing/purchase-orders/1/",
    "/purchasing/purchase-orders/2/",
    "/purchasing/purchase-orders/3/",
    "/purchasing/purchase-orders/3/receipts/new/",
    "/purchasing/purchase-orders/4/",
    "/purchasing/goods-receipts/1/",
    "/purchasing/purchase-orders/5/",
    "/purchasing/goods-receipts/2/",
    "/inventory/requirements/1/reserve/",
    "/inventory/reservations/1/issue/",
    "/inventory/movements/4/return/",
    "/inventory/1/",
    "/purchasing/supplier-invoices/",
    ("/purchasing/supplier-invoices/new/?purchase_order=5"),
    "/purchasing/supplier-invoices/1/",
    "/purchasing/supplier-invoices/2/",
    "/purchasing/supplier-invoices/3/",
    "/purchasing/supplier-payments/1/void/",
    "/jobs/4/release/",
    "/jobs/5/release/",
    "/billing/1/",
    "/billing/2/",
)


class LinkParser(HTMLParser):
    """Collect internal links from rendered HTML."""

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


def _classification(status_code: int) -> str:
    """Classify one HTTP response."""
    if 200 <= status_code < 300:
        return "SUCCESS"

    if 300 <= status_code < 400:
        return "REDIRECT"

    if status_code == 400:
        return "BAD REQUEST"

    if status_code == 403:
        return "FORBIDDEN"

    if status_code == 404:
        return "NOT FOUND"

    if status_code >= 500:
        return "SERVER ERROR"

    return "OTHER"


def _is_expected_scenario_status(
    status_code: int,
) -> bool:
    """Allow successful, redirect, and permission-denied responses."""
    return 200 <= status_code < 400 or status_code == 403


def main() -> None:
    """Run all role checks and write a strict report."""
    if AUDIT_HOST not in settings.ALLOWED_HOSTS and "*" not in settings.ALLOWED_HOSTS:
        raise RuntimeError(
            f"{AUDIT_HOST!r} is not present in ALLOWED_HOSTS: "
            f"{settings.ALLOWED_HOSTS!r}"
        )

    # Expected 403 responses are audit evidence, not terminal errors.
    logging.getLogger("django.request").setLevel(logging.CRITICAL)

    report: list[str] = [
        "# OYERA Release-Candidate Role Navigation Audit",
        "",
        f"- Audit host: `{AUDIT_HOST}`",
        "",
        ("| Role | Login | Dashboard | Links | 2xx | 3xx | 403 | 400 | 404 | Other |"),
        ("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"),
    ]
    details: list[str] = []
    failures: list[str] = []

    for role, credentials in ACCOUNTS.items():
        username, password = credentials

        client = Client(
            HTTP_HOST=AUDIT_HOST,
        )

        logged_in = client.login(
            username=username,
            password=password,
        )

        if not logged_in:
            failures.append(f"{role}: login failed for {username}.")
            report.append(f"| {role} | FAIL | - | - | - | - | - | - | - | - |")
            continue

        dashboard = client.get(
            "/",
            follow=False,
        )

        if dashboard.status_code != 200:
            failures.append(
                f"{role}: dashboard returned {dashboard.status_code}; expected 200."
            )

        parser = LinkParser()

        if dashboard.status_code == 200:
            parser.feed(
                dashboard.content.decode(
                    "utf-8",
                    errors="replace",
                )
            )

        counts = {
            "SUCCESS": 0,
            "REDIRECT": 0,
            "FORBIDDEN": 0,
            "BAD REQUEST": 0,
            "NOT FOUND": 0,
            "OTHER": 0,
        }

        details.extend(
            [
                "",
                f"## {role}",
                "",
                f"- Username: `{username}`",
                "- Login: PASS",
                f"- Dashboard: `{dashboard.status_code}`",
                "",
                "### Visible internal links",
                "",
            ]
        )

        if parser.links:
            details.extend(f"- `{link}`" for link in sorted(parser.links))
        else:
            details.append("- No internal links detected.")

        details.extend(
            [
                "",
                "### Seeded scenario responses",
                "",
                ("| Status | Classification | Path | Redirect destination |"),
                "|---:|---|---|---|",
            ]
        )

        for scenario_path in SCENARIO_PATHS:
            response = client.get(
                scenario_path,
                follow=False,
            )
            classification = _classification(response.status_code)
            location = response.headers.get(
                "Location",
                "",
            )

            if classification in counts:
                counts[classification] += 1
            else:
                counts["OTHER"] += 1

            if not _is_expected_scenario_status(response.status_code):
                failures.append(
                    f"{role}: {scenario_path} returned "
                    f"unexpected status "
                    f"{response.status_code}."
                )

            details.append(
                f"| {response.status_code} "
                f"| {classification} "
                f"| `{scenario_path}` "
                f"| `{location}` |"
            )

        report.append(
            f"| {role} "
            f"| PASS "
            f"| {dashboard.status_code} "
            f"| {len(parser.links)} "
            f"| {counts['SUCCESS']} "
            f"| {counts['REDIRECT']} "
            f"| {counts['FORBIDDEN']} "
            f"| {counts['BAD REQUEST']} "
            f"| {counts['NOT FOUND']} "
            f"| {counts['OTHER']} |"
        )

    report.extend(details)
    report.extend(
        [
            "",
            "## Automated result",
            "",
        ]
    )

    if failures:
        report.append("**FAIL**")
        report.extend(f"- {failure}" for failure in failures)
    else:
        report.append(
            "**PASS — all six accounts logged in, "
            "all dashboards returned 200, and every "
            "scenario returned an expected response.**"
        )

    REPORT_PATH.write_text(
        "\n".join(report) + "\n",
        encoding="utf-8",
    )

    print(
        REPORT_PATH.read_text(
            encoding="utf-8",
        )
    )

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
