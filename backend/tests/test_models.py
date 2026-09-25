import pytest

from shared.models import ValidationError, apply_update, build_ticket


def _valid_payload(**overrides):
    payload = {
        "name": "Aiman Rahman",
        "email": "aiman@example.com",
        "title": "Cannot access campus Wi-Fi",
        "description": "I cannot connect to the campus Wi-Fi from my laptop.",
    }
    payload.update(overrides)
    return payload


def test_build_ticket_assigns_category_and_status():
    ticket = build_ticket(_valid_payload())
    assert ticket["category"] == "IT Support"
    assert ticket["status"] == "Categorised"
    assert ticket["classificationMethod"] == "keyword-rules"
    assert "id" in ticket and "createdAt" in ticket


def test_build_ticket_rejects_missing_fields():
    with pytest.raises(ValidationError) as exc:
        build_ticket({"name": "", "email": "not-an-email", "title": "", "description": ""})
    assert set(exc.value.errors) == {"name", "email", "title", "description"}


def test_build_ticket_honours_explicit_category():
    ticket = build_ticket(_valid_payload(category="Facilities"))
    assert ticket["category"] == "Facilities"
    assert ticket["classificationMethod"] == "manual"
    assert ticket["status"] == "New"


def test_apply_update_changes_status_and_records_history():
    ticket = build_ticket(_valid_payload())
    updated = apply_update(ticket, {"status": "In Progress"})
    assert updated["status"] == "In Progress"
    assert len(updated["statusHistory"]) == 2


def test_apply_update_rejects_invalid_status():
    ticket = build_ticket(_valid_payload())
    with pytest.raises(ValidationError):
        apply_update(ticket, {"status": "Not A Real Status"})
