from shared.models import build_ticket
from shared.repository import InMemoryTicketRepository


def _payload(title, description, **overrides):
    payload = {
        "name": "Test User",
        "email": "test@example.com",
        "title": title,
        "description": description,
    }
    payload.update(overrides)
    return payload


def test_create_and_get():
    repo = InMemoryTicketRepository()
    created = repo.create(build_ticket(_payload("Wifi issue", "Cannot connect to campus wifi")))
    fetched = repo.get(created["id"])
    assert fetched["title"] == "Wifi issue"


def test_list_filters_by_status():
    repo = InMemoryTicketRepository()
    t1 = repo.create(build_ticket(_payload("Wifi issue", "Cannot connect to campus wifi")))
    repo.create(build_ticket(_payload("Library fine", "My library fine seems wrong")))

    rows = repo.list(category="IT Support")
    assert len(rows) == 1
    assert rows[0]["id"] == t1["id"]


def test_list_respects_limit():
    repo = InMemoryTicketRepository()
    for i in range(5):
        repo.create(build_ticket(_payload(f"Ticket {i}", "Generic description text")))
    rows = repo.list(limit=2)
    assert len(rows) == 2
