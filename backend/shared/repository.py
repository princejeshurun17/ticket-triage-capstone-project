"""Ticket persistence.

Two interchangeable backends:

    CosmosTicketRepository    Azure Cosmos DB for NoSQL (free tier).
    InMemoryTicketRepository  Process memory. Used automatically whenever
                              COSMOS_ENDPOINT / COSMOS_KEY are not set, so the
                              app runs and tests offline with no Azure account.

The container is partitioned on /id: every ticket is its own partition, which
keeps point reads/updates single-partition and lets the admin change a
ticket's category freely (Cosmos forbids changing the partition key value of
an existing document). Listing becomes a cross-partition query, which is
cheap at classroom scale.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

from .config import Settings, get_settings
from .models import public_view

log = logging.getLogger("tickettriage.repository")


class TicketRepository:
    def create(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def get(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def replace(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def list(self, category: str = "", status: str = "", search: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        raise NotImplementedError


class InMemoryTicketRepository(TicketRepository):
    mode = "in-memory"

    def __init__(self) -> None:
        self._items: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._items[ticket["id"]] = dict(ticket)
        return public_view(ticket)

    def get(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            found = self._items.get(ticket_id)
            return dict(found) if found else None

    def replace(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            if ticket["id"] not in self._items:
                raise KeyError(ticket["id"])
            self._items[ticket["id"]] = dict(ticket)
        return public_view(ticket)

    def list(self, category: str = "", status: str = "", search: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            rows = [dict(v) for v in self._items.values()]

        needle = search.strip().lower()

        def keep(row: Dict[str, Any]) -> bool:
            if category and row.get("category") != category:
                return False
            if status and row.get("status") != status:
                return False
            if needle and needle not in f"{row.get('title','')} {row.get('description','')}".lower():
                return False
            return True

        rows = [r for r in rows if keep(r)]
        rows.sort(key=lambda r: r.get("createdAt", ""), reverse=True)
        return [public_view(r) for r in rows[:limit]]


class CosmosTicketRepository(TicketRepository):
    mode = "cosmos"

    def __init__(self, settings: Settings) -> None:
        from azure.cosmos import CosmosClient, PartitionKey  # imported lazily

        self._client = CosmosClient(settings.cosmos_endpoint, credential=settings.cosmos_key)
        database = self._client.create_database_if_not_exists(id=settings.cosmos_database)
        self._container = database.create_container_if_not_exists(
            id=settings.cosmos_container,
            partition_key=PartitionKey(path="/id"),
        )

    def create(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        created = self._container.create_item(body=ticket)
        return public_view(created)

    def get(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        from azure.cosmos import exceptions

        try:
            return self._container.read_item(item=ticket_id, partition_key=ticket_id)
        except exceptions.CosmosResourceNotFoundError:
            return None

    def replace(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        updated = self._container.replace_item(item=ticket["id"], body=ticket)
        return public_view(updated)

    def list(self, category: str = "", status: str = "", search: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        clauses: List[str] = []
        params: List[Dict[str, Any]] = []

        if category:
            clauses.append("c.category = @category")
            params.append({"name": "@category", "value": category})
        if status:
            clauses.append("c.status = @status")
            params.append({"name": "@status", "value": status})
        if search:
            clauses.append("(CONTAINS(LOWER(c.title), @q) OR CONTAINS(LOWER(c.description), @q))")
            params.append({"name": "@q", "value": search.strip().lower()})

        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT * FROM c{where} ORDER BY c.createdAt DESC OFFSET 0 LIMIT @limit"
        params.append({"name": "@limit", "value": int(limit)})

        rows = self._container.query_items(query=query, parameters=params, enable_cross_partition_query=True)
        return [public_view(r) for r in rows]


_repository: Optional[TicketRepository] = None
_repo_lock = threading.Lock()


def get_repository(settings: Optional[Settings] = None, refresh: bool = False) -> TicketRepository:
    """Shared repository instance. Falls back to in-memory if Cosmos is
    misconfigured so a bad key degrades the demo instead of crashing it."""
    global _repository
    settings = settings or get_settings()

    with _repo_lock:
        if _repository is not None and not refresh:
            return _repository

        if settings.cosmos_configured:
            try:
                _repository = CosmosTicketRepository(settings)
                log.info("Using Cosmos DB repository (%s)", settings.cosmos_database)
            except Exception as exc:  # noqa: BLE001
                log.error("Cosmos DB unavailable, falling back to in-memory: %s", exc)
                _repository = InMemoryTicketRepository()
        else:
            _repository = InMemoryTicketRepository()

        return _repository
