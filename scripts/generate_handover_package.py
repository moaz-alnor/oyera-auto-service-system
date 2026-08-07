"""Generate OYERA's final tester, role, and handover PDF package."""

from __future__ import annotations

import html
import re
import subprocess
import tempfile
from datetime import date
from pathlib import Path
from typing import Final

import markdown
from playwright.sync_api import sync_playwright

ROOT_DIR: Final = Path(__file__).resolve().parents[1]

UAT_DIR: Final = ROOT_DIR / "docs" / "uat"
EVIDENCE_DIR: Final = UAT_DIR / "evidence"
CSV_DIR: Final = EVIDENCE_DIR / "csv"

HANDOVER_DIR: Final = ROOT_DIR / "docs" / "handover"
ROLE_SOURCE_DIR: Final = HANDOVER_DIR / "roles"
PDF_DIR: Final = HANDOVER_DIR / "pdf"

CASEBOOK_PATH: Final = UAT_DIR / "role-uat-casebook.md"
BASELINE_PATH: Final = UAT_DIR / "uat-baseline.md"
LEDGER_PATH: Final = UAT_DIR / "uat-execution-results.md"

DATABASE_GUIDE_PATH: Final = (
    ROOT_DIR / "docs" / "operations" / "database-backup-restore.md"
)
DEPLOYMENT_GUIDE_PATH: Final = (
    ROOT_DIR / "docs" / "operations" / "production-deployment.md"
)
DEPLOYMENT_VALIDATION_PATH: Final = (
    ROOT_DIR / "docs" / "release" / "production-deployment-validation.md"
)

MASTER_SOURCE_PATH: Final = (
    HANDOVER_DIR / "OYERA_Final_Tester_and_Role_Handover_Guide.md"
)
MASTER_PDF_PATH: Final = PDF_DIR / "OYERA_Final_Tester_and_Role_Handover_Guide.pdf"

VERIFIED_AUTOMATED_TESTS: Final = 826
EXPECTED_UAT_CASES: Final = 32
EXPECTED_SCREENSHOTS: Final = 41
EXPECTED_CSV_FILES: Final = 10

ROLES: Final = (
    {
        "name": "Administrator",
        "slug": "administrator",
        "code": "ADM",
        "username": "admin",
        "password": "AdminDemo123!",
    },
    {
        "name": "Manager",
        "slug": "manager",
        "code": "MGR",
        "username": "manager",
        "password": "ManagerDemo123!",
    },
    {
        "name": "Receptionist",
        "slug": "receptionist",
        "code": "REC",
        "username": "receptionist",
        "password": "ReceptionDemo123!",
    },
    {
        "name": "Senior Technician",
        "slug": "senior-technician",
        "code": "SEN",
        "username": "senior_technician",
        "password": "SeniorTechDemo123!",
    },
    {
        "name": "Technician",
        "slug": "technician",
        "code": "TEC",
        "username": "technician",
        "password": "TechnicianDemo123!",
    },
    {
        "name": "Cashier",
        "slug": "cashier",
        "code": "CAS",
        "username": "cashier",
        "password": "CashierDemo123!",
    },
)

CSS: Final = r"""
@page {
    size: A4;
    margin: 18mm 15mm 21mm 15mm;
}

* {
    box-sizing: border-box;
}

html {
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Arial,
        sans-serif;
    color: #17202a;
    background: #ffffff;
}

body {
    margin: 0;
    font-size: 10.2pt;
    line-height: 1.48;
}

.cover {
    min-height: 245mm;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 24mm 18mm;
    color: #ffffff;
    background:
        linear-gradient(
            145deg,
            #111820 0%,
            #1d2732 58%,
            #263643 100%
        );
    page-break-after: always;
    position: relative;
    overflow: hidden;
}

.cover::before {
    content: "";
    position: absolute;
    width: 95mm;
    height: 95mm;
    right: -35mm;
    top: -30mm;
    border: 14mm solid #f2c230;
    transform: rotate(18deg);
    opacity: 0.95;
}

.cover::after {
    content: "";
    position: absolute;
    left: 18mm;
    right: 18mm;
    bottom: 24mm;
    height: 3px;
    background: #f2c230;
}

.cover-kicker {
    color: #f2c230;
    font-size: 11pt;
    font-weight: 700;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    margin-bottom: 14mm;
}

.cover h1 {
    color: #ffffff;
    font-size: 31pt;
    line-height: 1.1;
    margin: 0 0 8mm 0;
    max-width: 155mm;
    border: 0;
}

.cover-subtitle {
    font-size: 15pt;
    color: #dfe6ec;
    max-width: 145mm;
    margin-bottom: 24mm;
}

.cover-meta {
    font-size: 10.5pt;
    color: #d6dde3;
    line-height: 1.8;
}

.cover-meta strong {
    color: #ffffff;
}

main {
    width: 100%;
}

h1,
h2,
h3,
h4 {
    color: #18232d;
    page-break-after: avoid;
}

h1 {
    font-size: 23pt;
    margin: 0 0 10mm 0;
    padding-bottom: 4mm;
    border-bottom: 4px solid #f2c230;
}

h2 {
    font-size: 17pt;
    margin: 11mm 0 4mm 0;
    padding-left: 4mm;
    border-left: 5px solid #f2c230;
}

h3 {
    font-size: 13pt;
    margin: 8mm 0 3mm 0;
    color: #263746;
}

h4 {
    font-size: 11pt;
    margin: 6mm 0 2mm 0;
}

p {
    margin: 0 0 3.2mm 0;
    orphans: 3;
    widows: 3;
}

ul,
ol {
    margin: 2mm 0 4mm 7mm;
    padding-left: 5mm;
}

li {
    margin-bottom: 1.2mm;
}

a {
    color: #165f8e;
    text-decoration: none;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 4mm 0 6mm 0;
    font-size: 8.8pt;
    page-break-inside: auto;
}

thead {
    display: table-header-group;
}

tr {
    page-break-inside: avoid;
}

th {
    background: #263746;
    color: #ffffff;
    text-align: left;
    padding: 2.5mm;
    border: 1px solid #425462;
}

td {
    padding: 2.3mm;
    vertical-align: top;
    border: 1px solid #c9d1d7;
}

tbody tr:nth-child(even) {
    background: #f4f6f7;
}

code {
    font-family:
        "SFMono-Regular",
        Consolas,
        "Liberation Mono",
        monospace;
    font-size: 8.8pt;
    color: #7a3e00;
    background: #f5f2ec;
    padding: 0.3mm 1mm;
    border-radius: 2px;
}

pre {
    color: #edf2f5;
    background: #17202a;
    border-left: 5px solid #f2c230;
    padding: 4mm;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    page-break-inside: avoid;
}

pre code {
    color: inherit;
    background: transparent;
    padding: 0;
}

blockquote {
    margin: 5mm 0;
    padding: 4mm 5mm;
    color: #36454f;
    background: #fff8df;
    border-left: 5px solid #f2c230;
}

.toc {
    background: #f3f5f6;
    border: 1px solid #d5dce1;
    padding: 5mm 7mm;
    margin: 5mm 0 8mm;
}

.toc ul {
    margin-bottom: 0;
}

.evidence-section {
    page-break-before: always;
}

.evidence-summary {
    padding: 4mm 5mm;
    margin-bottom: 6mm;
    background: #eef4f7;
    border-left: 5px solid #28749d;
}

figure {
    margin: 0 0 9mm 0;
    page-break-inside: avoid;
}

figure img {
    display: block;
    width: 100%;
    max-height: 225mm;
    object-fit: contain;
    border: 1px solid #c4ccd2;
    box-shadow: 0 2px 7px rgba(0, 0, 0, 0.12);
}

figcaption {
    margin-top: 2mm;
    color: #52606b;
    font-size: 8.5pt;
    text-align: center;
}

.status-pass {
    display: inline-block;
    color: #155724;
    background: #dff0e3;
    border: 1px solid #a8d4b2;
    border-radius: 3px;
    padding: 1.4mm 3mm;
    font-weight: 700;
}

.small {
    font-size: 8.5pt;
    color: #5d6972;
}
"""


def read_required(path: Path) -> str:
    """Read one required UTF-8 source file."""
    if not path.is_file():
        raise SystemExit(f"Required handover source was not found: {path}")

    return path.read_text(encoding="utf-8")


def read_optional(path: Path) -> str:
    """Read an optional source or return an explanatory note."""
    if path.is_file():
        return path.read_text(encoding="utf-8")

    return f"> Optional source was not found at `{path.relative_to(ROOT_DIR)}`."


def normalize_text(value: str) -> str:
    """Normalize source text for consistent PDF rendering."""
    return (
        value.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("—", " - ")
        .replace("–", "-")
    )


def demote_headings(
    value: str,
    *,
    levels: int = 1,
) -> str:
    """Demote Markdown headings while preserving structure."""

    def replacement(match: re.Match[str]) -> str:
        hashes = match.group(1)
        spacing = match.group(2)
        target_length = min(
            6,
            len(hashes) + levels,
        )
        return "#" * target_length + spacing

    return re.sub(
        r"^(#{1,6})(\s+)",
        replacement,
        value,
        flags=re.MULTILINE,
    )


def git_output(*arguments: str) -> str:
    """Return one Git value without failing document generation."""
    completed = subprocess.run(
        ["git", *arguments],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.returncode != 0:
        return "unknown"

    return completed.stdout.strip() or "unknown"


def extract_role_section(
    casebook: str,
    *,
    role_name: str,
) -> str:
    """Extract one role's complete casebook section."""
    heading = f"# {role_name} UAT"

    start_match = re.search(
        rf"^{re.escape(heading)}\s*$",
        casebook,
        flags=re.MULTILINE,
    )

    if start_match is None:
        raise SystemExit(f"Could not find the {role_name} section in the UAT casebook.")

    next_heading = re.search(
        r"^# .+$",
        casebook[start_match.end() :],
        flags=re.MULTILINE,
    )

    if next_heading is None:
        end = len(casebook)
    else:
        end = start_match.end() + next_heading.start()

    return casebook[start_match.start() : end].strip()


def casebook_preamble(casebook: str) -> str:
    """Return the global preparation before Administrator UAT."""
    marker = "# Administrator UAT"
    index = casebook.find(marker)

    if index == -1:
        raise SystemExit("Administrator section was not found in the UAT casebook.")

    return casebook[:index].strip()


def role_results_table(
    ledger: str,
    *,
    role_code: str,
) -> str:
    """Extract verified ledger rows for one role."""
    rows = [
        line for line in ledger.splitlines() if line.startswith(f"| UAT-{role_code}-")
    ]

    if not rows:
        raise SystemExit(f"No execution rows were found for {role_code}.")

    header = (
        "| Case | Status | Evidence | Issue | Notes |\n| --- | --- | --- | --- | --- |"
    )

    return header + "\n" + "\n".join(rows)


def count_passed_cases(ledger: str) -> int:
    """Count PASS rows in the final execution ledger."""
    return len(
        re.findall(
            r"^\| UAT-[A-Z]+-\d+ \| PASS \|",
            ledger,
            flags=re.MULTILINE,
        )
    )


def evidence_files_for_role(
    role_slug: str,
) -> list[Path]:
    """Return all PNG evidence for one role."""
    return sorted((EVIDENCE_DIR / role_slug).glob("UAT-*.png"))


def csv_files_for_role(
    role_code: str,
) -> list[Path]:
    """Return CSV evidence belonging to one role."""
    return sorted(CSV_DIR.glob(f"UAT-{role_code}-*.csv"))


def markdown_to_html(value: str) -> str:
    """Convert supported Markdown into print-ready HTML."""
    return markdown.markdown(
        normalize_text(value),
        extensions=[
            "extra",
            "toc",
            "sane_lists",
        ],
        output_format="html5",
    )


def evidence_gallery_html(
    paths: list[Path],
) -> str:
    """Build a visual gallery from real evidence screenshots."""
    if not paths:
        return ""

    figures: list[str] = []

    for path in paths:
        figures.append(
            "\n".join(
                [
                    "<figure>",
                    (
                        f'<img src="{html.escape(path.resolve().as_uri())}" '
                        f'alt="{html.escape(path.name)}">'
                    ),
                    (f"<figcaption>{html.escape(path.name)}</figcaption>"),
                    "</figure>",
                ]
            )
        )

    return "\n".join(
        [
            '<section class="evidence-section">',
            "<h1>Verified Evidence Gallery</h1>",
            (
                '<div class="evidence-summary">'
                f"{len(paths)} non-empty PNG evidence files are "
                "included in this guide."
                "</div>"
            ),
            *figures,
            "</section>",
        ]
    )


def csv_inventory_markdown(
    paths: list[Path],
) -> str:
    """Create a readable inventory of exported CSV evidence."""
    if not paths:
        return "No CSV evidence is required for this role."

    return "\n".join(f"- `{path.relative_to(ROOT_DIR)}`" for path in paths)


def document_html(
    *,
    title: str,
    subtitle: str,
    markdown_source: str,
    screenshots: list[Path],
    branch: str,
    commit: str,
) -> str:
    """Create one complete HTML document."""
    body = markdown_to_html(markdown_source)
    gallery = evidence_gallery_html(screenshots)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
<section class="cover">
    <div class="cover-kicker">OYERA Auto Service System</div>
    <h1>{html.escape(title)}</h1>
    <div class="cover-subtitle">{html.escape(subtitle)}</div>
    <div class="cover-meta">
        <strong>Release branch:</strong> {html.escape(branch)}<br>
        <strong>Source commit:</strong> {html.escape(commit)}<br>
        <strong>Generated:</strong> {date.today().isoformat()}<br>
        <strong>Acceptance result:</strong>
        <span class="status-pass">32 / 32 PASS</span>
    </div>
</section>
<main>
{body}
{gallery}
</main>
</body>
</html>
"""


def validate_inputs(
    *,
    ledger: str,
) -> tuple[int, int, int]:
    """Validate UAT results and evidence totals."""
    passed_cases = count_passed_cases(ledger)
    screenshots = sorted(EVIDENCE_DIR.glob("*/*.png"))
    csv_files = sorted(CSV_DIR.glob("*.csv"))

    if passed_cases != EXPECTED_UAT_CASES:
        raise SystemExit(
            f"Expected {EXPECTED_UAT_CASES} PASS cases; found {passed_cases}."
        )

    if len(screenshots) != EXPECTED_SCREENSHOTS:
        raise SystemExit(
            f"Expected {EXPECTED_SCREENSHOTS} screenshots; found {len(screenshots)}."
        )

    if len(csv_files) != EXPECTED_CSV_FILES:
        raise SystemExit(
            f"Expected {EXPECTED_CSV_FILES} CSV files; found {len(csv_files)}."
        )

    for screenshot in screenshots:
        data = screenshot.read_bytes()

        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise SystemExit(f"Invalid PNG evidence: {screenshot}")

    for csv_file in csv_files:
        if not csv_file.read_bytes():
            raise SystemExit(f"Empty CSV evidence: {csv_file}")

    return (
        passed_cases,
        len(screenshots),
        len(csv_files),
    )


def render_pdfs(
    documents: list[
        tuple[
            str,
            str,
            str,
            list[Path],
            Path,
        ]
    ],
    *,
    branch: str,
    commit: str,
) -> None:
    """Render master and role PDFs using local Google Chrome."""
    PDF_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.TemporaryDirectory(prefix="oyera-handover-") as temporary_directory:
        temporary_root = Path(temporary_directory)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                channel="chrome",
                headless=True,
                args=[
                    "--allow-file-access-from-files",
                ],
            )

            for (
                title,
                subtitle,
                markdown_source,
                screenshots,
                pdf_path,
            ) in documents:
                html_document = document_html(
                    title=title,
                    subtitle=subtitle,
                    markdown_source=markdown_source,
                    screenshots=screenshots,
                    branch=branch,
                    commit=commit,
                )

                html_path = temporary_root / f"{pdf_path.stem}.html"
                html_path.write_text(
                    html_document,
                    encoding="utf-8",
                )

                page = browser.new_page(
                    viewport={
                        "width": 1440,
                        "height": 1000,
                    },
                )

                page.goto(
                    html_path.resolve().as_uri(),
                    wait_until="networkidle",
                )

                page.wait_for_function(
                    """
                    () => Array.from(document.images).every(
                        (image) => (
                            image.complete
                            && image.naturalWidth > 0
                        )
                    )
                    """
                )

                page.emulate_media(
                    media="print",
                )

                page.pdf(
                    path=str(pdf_path),
                    format="A4",
                    print_background=True,
                    display_header_footer=True,
                    header_template=(
                        '<div style="font-size:8px;'
                        "width:100%;padding:0 15mm;"
                        'color:#66727a;">'
                        f"{html.escape(title)}"
                        "</div>"
                    ),
                    footer_template=(
                        '<div style="font-size:8px;'
                        "width:100%;padding:0 15mm;"
                        'color:#66727a;text-align:right;">'
                        'Page <span class="pageNumber"></span>'
                        ' of <span class="totalPages"></span>'
                        "</div>"
                    ),
                    margin={
                        "top": "20mm",
                        "right": "15mm",
                        "bottom": "20mm",
                        "left": "15mm",
                    },
                )

                page.close()

                data = pdf_path.read_bytes()

                if not data.startswith(b"%PDF-"):
                    raise SystemExit(f"Invalid PDF output: {pdf_path}")

                if len(data) < 10_000:
                    raise SystemExit(f"Unexpectedly small PDF: {pdf_path}")

                print(f"Created {pdf_path.relative_to(ROOT_DIR)} ({len(data):,} bytes)")

            browser.close()


def main() -> int:
    """Generate the complete OYERA handover package."""
    HANDOVER_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    ROLE_SOURCE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    PDF_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    casebook = read_required(CASEBOOK_PATH)
    baseline = read_required(BASELINE_PATH)
    ledger = read_required(LEDGER_PATH)

    database_guide = read_optional(DATABASE_GUIDE_PATH)
    deployment_guide = read_optional(DEPLOYMENT_GUIDE_PATH)
    deployment_validation = read_optional(DEPLOYMENT_VALIDATION_PATH)

    (
        passed_cases,
        screenshot_count,
        csv_count,
    ) = validate_inputs(
        ledger=ledger,
    )

    branch = git_output(
        "branch",
        "--show-current",
    )
    commit = git_output(
        "rev-parse",
        "--short",
        "HEAD",
    )

    common_preamble = casebook_preamble(casebook)

    release_validation_source = f"""# OYERA Release Validation Record

| Item | Verified result |
| --- | ---: |
| Role-based UAT cases | {passed_cases} / {EXPECTED_UAT_CASES} PASS |
| Evidence screenshots | {screenshot_count} |
| CSV evidence exports | {csv_count} |
| Automated project tests | {VERIFIED_AUTOMATED_TESTS} PASS |
| Django system check | No issues |
| Migration drift check | No changes detected |
| Ruff linting | PASS |
| Ruff formatting | PASS |
| Shell-script syntax checks | PASS |
| Release branch | `{branch}` |
| UAT source commit | `{commit}` |

> The role automation resets the local demonstration database before
> each role. The final local database reflects the last executed role,
> while all verified role outcomes remain preserved in the execution
> ledger and evidence directories.

## Security note

All credentials in these guides are demonstration credentials created by
`reset_demo_data`. They must never be reused for a production deployment.
Production users must receive unique accounts and independently generated
passwords.
"""

    (HANDOVER_DIR / "release-validation.md").write_text(
        release_validation_source,
        encoding="utf-8",
    )

    defect_template = """# OYERA UAT Defect Report

| Field | Entry |
| --- | --- |
| Defect ID | |
| Date and time | |
| Tester | |
| Role/account | |
| UAT case | |
| Environment | |
| Browser and version | |
| Page URL | |
| Severity | Critical / High / Medium / Low |
| Status | Open / Retest / Closed |

## Summary

Describe what failed in one sentence.

## Exact steps to reproduce

1.
2.
3.

## Input values used

Record every value entered by the tester.

## Expected result

Copy the expected result from the relevant role guide.

## Actual result

Describe the exact visible and stored result.

## Evidence

- Screenshot filename:
- CSV filename:
- Server-log extract:
- Relevant database verification:

## Reset and retest record

- Demo database reset performed:
- Fix version/commit:
- Retest result:
- Closed by:
"""

    (HANDOVER_DIR / "uat-defect-report-template.md").write_text(
        defect_template,
        encoding="utf-8",
    )

    acceptance_checklist = """# OYERA Final Acceptance Checklist

## Technical acceptance

- [ ] Production deployment guide reviewed.
- [ ] Production environment values are unique and secret.
- [ ] HTTPS and domain configuration verified.
- [ ] Database backup created before deployment.
- [ ] Restore procedure tested.
- [ ] Health endpoints return expected results.
- [ ] Static files load correctly.
- [ ] Uploaded media uses persistent storage.
- [ ] All migrations are applied.
- [ ] Production administrator account created securely.

## Functional acceptance

- [ ] Administrator guide accepted.
- [ ] Manager guide accepted.
- [ ] Receptionist guide accepted.
- [ ] Senior Technician guide accepted.
- [ ] Technician guide accepted.
- [ ] Cashier guide accepted.
- [ ] All 32 UAT cases reviewed.
- [ ] Evidence files reviewed.
- [ ] Open defects documented and accepted.

## Handover acceptance

| Responsibility | Name | Signature | Date |
| --- | --- | --- | --- |
| Tester | | | |
| Business representative | | | |
| System owner | | | |
| Developer | | | |
"""

    (HANDOVER_DIR / "final-acceptance-checklist.md").write_text(
        acceptance_checklist,
        encoding="utf-8",
    )

    master_source = f"""# OYERA Final Tester and Role Handover Guide

[TOC]

## Document control

| Field | Value |
| --- | --- |
| System | OYERA Auto Service System |
| Document | Final Tester and Role Handover Guide |
| Generated | {date.today().isoformat()} |
| Branch | `{branch}` |
| Source commit | `{commit}` |
| UAT result | **{passed_cases}/{EXPECTED_UAT_CASES} PASS** |
| Automated tests | **{VERIFIED_AUTOMATED_TESTS} PASS** |
| Evidence | {screenshot_count} screenshots and {csv_count} CSV files |

## Purpose and use

This is the authoritative handover guide for testing, demonstrating,
operating, deploying, and accepting OYERA.

The tester should not infer missing values or invent test data. Each role
section provides the account, exact path, values to enter, expected result,
forbidden result, and required evidence.

## Demonstration-data warning

The listed usernames and passwords are for local demonstration and UAT only.
They are intentionally predictable so that the acceptance suite can be
repeated. They are not production credentials.

## Verified release status

{demote_headings(release_validation_source, levels=1)}

## Exact UAT baseline

{demote_headings(baseline, levels=1)}

## Complete role-by-role test casebook

{demote_headings(casebook, levels=1)}

## Verified UAT execution ledger

{demote_headings(ledger, levels=1)}

## Database backup and restore guide

{demote_headings(database_guide, levels=1)}

## Production deployment and initial setup

{demote_headings(deployment_guide, levels=1)}

## Production deployment validation

{demote_headings(deployment_validation, levels=1)}

## Defect reporting procedure

Use the editable template:

`docs/handover/uat-defect-report-template.md`

{demote_headings(defect_template, levels=1)}

## Final acceptance checklist

{demote_headings(acceptance_checklist, levels=1)}

## Evidence inventory

The master PDF includes all {screenshot_count} verified screenshots.

The following CSV evidence files are retained in the repository:

{csv_inventory_markdown(sorted(CSV_DIR.glob("*.csv")))}

## Regeneration

Run:

```bash
DJANGO_SETTINGS_MODULE=config.settings.development \\
PYTHONPATH=src \\
python scripts/generate_handover_package.py
```

The generated PDFs are written to:

`docs/handover/pdf/`
"""

    MASTER_SOURCE_PATH.write_text(
        master_source,
        encoding="utf-8",
    )

    documents: list[
        tuple[
            str,
            str,
            str,
            list[Path],
            Path,
        ]
    ] = []

    documents.append(
        (
            "OYERA Final Tester and Role Handover Guide",
            (
                "Complete verified acceptance, operating, "
                "deployment, evidence, and role instructions"
            ),
            master_source,
            sorted(EVIDENCE_DIR.glob("*/*.png")),
            MASTER_PDF_PATH,
        )
    )

    generated_role_files: list[tuple[str, Path, Path]] = []

    for role in ROLES:
        role_name = role["name"]
        role_slug = role["slug"]
        role_code = role["code"]
        username = role["username"]
        password = role["password"]

        section = extract_role_section(
            casebook,
            role_name=role_name,
        )
        result_table = role_results_table(
            ledger,
            role_code=role_code,
        )

        screenshots = evidence_files_for_role(role_slug)
        csv_files = csv_files_for_role(role_code)

        role_source = f"""# OYERA {role_name} Tester and User Guide

[TOC]

## Role identification

| Field | Exact value |
| --- | --- |
| Role | {role_name} |
| Username | `{username}` |
| Password | `{password}` |
| Login URL | `http://127.0.0.1:8000/accounts/login/` |
| Database reset | `python src/manage.py reset_demo_data --yes` |
| Evidence directory | `docs/uat/evidence/{role_slug}/` |

> This is a local demonstration account. Replace it with a unique,
> securely managed account in production.

## Preparation and shared test rules

{demote_headings(common_preamble, levels=1)}

## Exact {role_name} procedures

{demote_headings(section, levels=1)}

## Verified execution results

{result_table}

## CSV evidence

{csv_inventory_markdown(csv_files)}

## Tester completion record

| Field | Entry |
| --- | --- |
| Tester | |
| Test date | |
| Environment | |
| Result | PASS / FAIL / BLOCKED |
| Defect IDs | |
| Signature | |
"""

        role_source_path = ROLE_SOURCE_DIR / f"OYERA_{role_slug}_guide.md"
        role_source_path.write_text(
            role_source,
            encoding="utf-8",
        )

        role_pdf_path = PDF_DIR / f"OYERA_{role_slug}_guide.pdf"

        documents.append(
            (
                f"OYERA {role_name} Tester and User Guide",
                (
                    "Exact account, permitted and forbidden "
                    "actions, test data, expected results, "
                    "and verified evidence"
                ),
                role_source,
                screenshots,
                role_pdf_path,
            )
        )

        generated_role_files.append(
            (
                role_name,
                role_source_path,
                role_pdf_path,
            )
        )

    render_pdfs(
        documents,
        branch=branch,
        commit=commit,
    )

    index_lines = [
        "# OYERA Handover Package",
        "",
        (
            f"Generated on `{date.today().isoformat()}` "
            f"from branch `{branch}` at commit `{commit}`."
        ),
        "",
        "## Master guide",
        "",
        ("- `OYERA_Final_Tester_and_Role_Handover_Guide.md`"),
        ("- `pdf/OYERA_Final_Tester_and_Role_Handover_Guide.pdf`"),
        "",
        "## Role guides",
        "",
    ]

    for (
        role_name,
        role_source_path,
        role_pdf_path,
    ) in generated_role_files:
        index_lines.append(
            "- "
            f"**{role_name}:** "
            f"`{role_source_path.relative_to(HANDOVER_DIR)}`; "
            f"`{role_pdf_path.relative_to(HANDOVER_DIR)}`"
        )

    index_lines.extend(
        [
            "",
            "## Supporting documents",
            "",
            "- `release-validation.md`",
            "- `uat-defect-report-template.md`",
            "- `final-acceptance-checklist.md`",
            "",
            "## Verified totals",
            "",
            f"- UAT: **{passed_cases}/{EXPECTED_UAT_CASES} PASS**",
            f"- Screenshots: **{screenshot_count}**",
            f"- CSV evidence: **{csv_count}**",
            (f"- Automated project tests: **{VERIFIED_AUTOMATED_TESTS} PASS**"),
            "",
        ]
    )

    (HANDOVER_DIR / "README.md").write_text(
        "\n".join(index_lines),
        encoding="utf-8",
    )

    print()
    print("OYERA handover package generated successfully.")
    print(f"Master PDF: {MASTER_PDF_PATH}")
    print(f"Role PDFs: {len(ROLES)}")
    print(f"UAT result: {passed_cases}/{EXPECTED_UAT_CASES} PASS")
    print(f"Evidence: {screenshot_count} PNG, {csv_count} CSV")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
