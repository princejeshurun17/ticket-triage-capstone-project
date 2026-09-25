"""Ticket Triage backend API.

Azure Functions Python v2 (decorator) programming model, deployed as the
managed API behind an Azure Static Web App (Free plan).

Routes:
    POST   /api/tickets            submit a ticket
    GET    /api/tickets            list/filter tickets (admin view)
    GET    /api/tickets/{id}       fetch one ticket
    PATCH  /api/tickets/{id}       update status/category (admin, key-guarded)
    GET    /api/categories         category list for the submission form
    GET    /api/health             diagnostics: storage backend, counts
"""

from __future__ import annotations

import json
import logging

import azure.functions as func

from shared.categories import CATEGORIES
from shared.config import get_settings
from shared.models import STATUSES, PRIORITIES, ValidationError, apply_update, build_ticket, public_view
from shared.repository import get_repository

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

log = logging.getLogger("tickettriage.api")


def _json(body, status: int = 200) -> func.HttpResponse:
    return func.HttpResponse(json.dumps(body), status_code=status, mimetype="application/json")


def _error(message: str, status: int = 400, errors=None) -> func.HttpResponse:
    payload = {"error": message}
    if errors:
        payload["details"] = errors
    return _json(payload, status)


def _is_admin(req: func.HttpRequest) -> bool:
    settings = get_settings()
    if not settings.admin_api_key:
        return True  # no key configured: classroom-safe default, open admin
    return req.headers.get("x-admin-key") == settings.admin_api_key


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    settings = get_settings()
    repo = get_repository()
    return _json({
        "status": "ok",
        "storage": repo.mode,
        "adminKeyConfigured": bool(settings.admin_api_key),
    })


@app.route(route="categories", methods=["GET"])
def categories(req: func.HttpRequest) -> func.HttpResponse:
    return _json({"categories": CATEGORIES, "priorities": PRIORITIES, "statuses": STATUSES})


@app.route(route="tickets", methods=["POST"])
def create_ticket(req: func.HttpRequest) -> func.HttpResponse:
    try:
        payload = req.get_json()
    except ValueError:
        return _error("Request body must be JSON.")

    try:
        ticket = build_ticket(payload)
    except ValidationError as exc:
        return _error("Validation failed.", 422, exc.errors)

    repo = get_repository()
    created = repo.create(ticket)
    return _json(created, 201)


@app.route(route="tickets", methods=["GET"])
def list_tickets(req: func.HttpRequest) -> func.HttpResponse:
    settings = get_settings()
    repo = get_repository()

    limit = min(int(req.params.get("limit", settings.max_page_size)), settings.max_page_size)
    rows = repo.list(
        category=req.params.get("category", ""),
        status=req.params.get("status", ""),
        search=req.params.get("search", ""),
        limit=limit,
    )
    return _json({"tickets": rows, "count": len(rows)})


@app.route(route="tickets/{id}", methods=["GET"])
def get_ticket(req: func.HttpRequest) -> func.HttpResponse:
    repo = get_repository()
    ticket = repo.get(req.route_params["id"])
    if not ticket:
        return _error("Ticket not found.", 404)
    return _json(public_view(ticket))


@app.route(route="tickets/{id}", methods=["PATCH"])
def update_ticket(req: func.HttpRequest) -> func.HttpResponse:
    if not _is_admin(req):
        return _error("Admin key required.", 401)

    repo = get_repository()
    ticket = repo.get(req.route_params["id"])
    if not ticket:
        return _error("Ticket not found.", 404)

    try:
        payload = req.get_json()
    except ValueError:
        return _error("Request body must be JSON.")

    try:
        updated = apply_update(ticket, payload)
    except ValidationError as exc:
        return _error("Validation failed.", 422, exc.errors)

    saved = repo.replace(updated)
    return _json(saved)
