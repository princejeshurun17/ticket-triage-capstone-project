"""App configuration, read once from environment / Azure Function app settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _clean(value: str | None) -> str:
    return (value or "").strip()


@dataclass
class Settings:
    cosmos_endpoint: str = field(default_factory=lambda: _clean(os.environ.get("COSMOS_ENDPOINT")))
    cosmos_key: str = field(default_factory=lambda: _clean(os.environ.get("COSMOS_KEY")))
    cosmos_database: str = field(default_factory=lambda: _clean(os.environ.get("COSMOS_DATABASE")) or "tickettriage")
    cosmos_container: str = field(default_factory=lambda: _clean(os.environ.get("COSMOS_CONTAINER")) or "tickets")

    admin_api_key: str = field(default_factory=lambda: _clean(os.environ.get("ADMIN_API_KEY")))
    max_page_size: int = field(default_factory=lambda: int(_clean(os.environ.get("MAX_PAGE_SIZE")) or "100"))

    @property
    def cosmos_configured(self) -> bool:
        return bool(self.cosmos_endpoint and self.cosmos_key)

    def storage_mode(self) -> str:
        return "cosmos" if self.cosmos_configured else "in-memory"


_settings: Settings | None = None


def get_settings(refresh: bool = False) -> Settings:
    global _settings
    if _settings is None or refresh:
        _settings = Settings()
    return _settings
