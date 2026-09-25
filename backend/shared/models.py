"""Ticket validation and assembly."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from .categories import CATEGORIES, suggest_category

STATUSES: List[str] = ["New", "Categorised", "In Progress", "Resolved"]
PRIORITIES: List[str] = ["Low", "Medium", "High"]

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ValidationError(Exception):
    def __init__(self, errors: Dict[str, str]):
        super().__init__("validation failed")
        self.errors = errors


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_ticket(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a submission payload and assemble a storable ticket record."""
    errors: Dict[str, str] = {}

    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip()
    title = str(payload.get("title", "")).strip()
    description = str(payload.get("description", "")).strip()
    priority = str(payload.get("priority", "") or "Medium").strip().title()
    category = str(payload.get("category", "") or "").strip()

    if not name:
        errors["name"] = "Name is required."
    if not email or not _EMAIL_RE.match(email):
        errors["email"] = "A valid email is required."
    if not title:
        errors["title"] = "Title is required."
    if not description:
        errors["description"] = "Description is required."
    if priority not in PRIORITIES:
        errors["priority"] = f"Priority must be one of {PRIORITIES}."

    if errors:
        raise ValidationError(errors)

    classification_method = "manual"
    confidence = 1.0
    if not category:
        category, confidence = suggest_category(title, description)
        classification_method = "keyword-rules"
    elif category not in CATEGORIES:
        errors["category"] = f"Category must be one of {CATEGORIES}."
        raise ValidationError(errors)

    now = _now_iso()
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "email": email,
        "title": title,
        "description": description,
        "priority": priority,
        "category": category,
        "classificationMethod": classification_method,
        "classificationConfidence": confidence,
        "status": "New" if classification_method == "manual" else "Categorised",
        "createdAt": now,
        "updatedAt": now,
        "statusHistory": [{"status": "New", "at": now}],
    }


def apply_update(ticket: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Apply an admin PATCH (status and/or category) to an existing ticket."""
    errors: Dict[str, str] = {}
    updated = dict(ticket)

    if "status" in payload:
        status = str(payload["status"]).strip()
        if status not in STATUSES:
            errors["status"] = f"Status must be one of {STATUSES}."
        else:
            updated["status"] = status
            history = list(updated.get("statusHistory", []))
            history.append({"status": status, "at": _now_iso()})
            updated["statusHistory"] = history

    if "category" in payload:
        category = str(payload["category"]).strip()
        if category not in CATEGORIES:
            errors["category"] = f"Category must be one of {CATEGORIES}."
        else:
            updated["category"] = category
            updated["classificationMethod"] = "manual"
            updated["classificationConfidence"] = 1.0

    if errors:
        raise ValidationError(errors)

    updated["updatedAt"] = _now_iso()
    return updated


def public_view(ticket: Dict[str, Any]) -> Dict[str, Any]:
    """Strip storage-only fields before returning a ticket over the API."""
    view = dict(ticket)
    view.pop("_rid", None)
    view.pop("_self", None)
    view.pop("_etag", None)
    view.pop("_attachments", None)
    view.pop("_ts", None)
    return view
