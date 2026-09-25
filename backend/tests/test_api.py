"""HTTP-layer tests exercising function_app.py handlers directly with
azure.functions.HttpRequest, without needing a running host."""

import json

import azure.functions as func

import function_app as api
from shared import repository


def setup_function():
    repository._repository = repository.InMemoryTicketRepository()


def _req(method, route, body=None, params=None, route_params=None, headers=None):
    return func.HttpRequest(
        method=method,
        url=f"http://localhost/api/{route}",
        body=json.dumps(body).encode() if body is not None else b"",
        params=params or {},
        route_params=route_params or {},
        headers=headers or {},
    )


def test_health_reports_in_memory_storage():
    resp = api.health(_req("GET", "health"))
    payload = json.loads(resp.get_body())
    assert payload["storage"] == "in-memory"


def test_create_then_list_ticket():
    body = {
        "name": "Aiman Rahman",
        "email": "aiman@example.com",
        "title": "Cannot access campus Wi-Fi",
        "description": "I cannot connect to the campus Wi-Fi from my laptop.",
    }
    created_resp = api.create_ticket(_req("POST", "tickets", body=body))
    assert created_resp.status_code == 201
    created = json.loads(created_resp.get_body())
    assert created["category"] == "IT Support"

    list_resp = api.list_tickets(_req("GET", "tickets"))
    listed = json.loads(list_resp.get_body())
    assert listed["count"] == 1


def test_create_ticket_validation_error():
    resp = api.create_ticket(_req("POST", "tickets", body={"name": ""}))
    assert resp.status_code == 422


def test_patch_ticket_status():
    body = {
        "name": "Aiman Rahman",
        "email": "aiman@example.com",
        "title": "Cannot access campus Wi-Fi",
        "description": "I cannot connect to the campus Wi-Fi from my laptop.",
    }
    created = json.loads(api.create_ticket(_req("POST", "tickets", body=body)).get_body())

    patch_resp = api.update_ticket(
        _req("PATCH", f"tickets/{created['id']}", body={"status": "Resolved"}, route_params={"id": created["id"]})
    )
    assert patch_resp.status_code == 200
    updated = json.loads(patch_resp.get_body())
    assert updated["status"] == "Resolved"


def test_get_missing_ticket_returns_404():
    resp = api.get_ticket(_req("GET", "tickets/does-not-exist", route_params={"id": "does-not-exist"}))
    assert resp.status_code == 404
