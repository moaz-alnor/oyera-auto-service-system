"""Tests for vehicle-release forms."""

from apps.jobs.forms import VehicleReleaseForm


def _valid_data() -> dict[str, object]:
    """Return valid vehicle-handover form data."""

    return {
        "final_mileage": 45100,
        "final_condition": ("Vehicle clean and operating normally."),
        "received_by_name": "Amina Musa",
        "received_by_contact": "0700222333",
        "handover_notes": ("Keys and documents handed over."),
        "payment_override": "",
        "payment_override_reason": "",
    }


def test_release_form_accepts_valid_handover() -> None:
    """Accept complete vehicle-release information."""

    form = VehicleReleaseForm(
        data=_valid_data(),
        minimum_mileage=45000,
        allow_payment_override=False,
    )

    assert form.is_valid()
    assert form.cleaned_data["payment_override"] is False


def test_release_form_rejects_lower_mileage() -> None:
    """Reject a final odometer below the minimum."""

    data = _valid_data()
    data["final_mileage"] = 44999

    form = VehicleReleaseForm(
        data=data,
        minimum_mileage=45000,
        allow_payment_override=False,
    )

    assert not form.is_valid()
    assert "final_mileage" in form.errors


def test_release_override_requires_reason() -> None:
    """Require evidence for an unpaid release."""

    data = _valid_data()
    data["payment_override"] = "on"

    form = VehicleReleaseForm(
        data=data,
        minimum_mileage=45000,
        allow_payment_override=True,
    )

    assert not form.is_valid()
    assert "payment_override_reason" in (form.errors)


def test_release_override_fields_follow_permission() -> None:
    """Hide override controls from normal release staff."""

    receptionist_form = VehicleReleaseForm(
        minimum_mileage=45000,
        allow_payment_override=False,
    )
    manager_form = VehicleReleaseForm(
        minimum_mileage=45000,
        allow_payment_override=True,
    )

    assert "payment_override" not in (receptionist_form.fields)
    assert "payment_override_reason" not in (receptionist_form.fields)
    assert "payment_override" in manager_form.fields
    assert "payment_override_reason" in manager_form.fields
