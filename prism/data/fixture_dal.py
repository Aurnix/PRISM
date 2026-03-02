"""Read-only DAL backed by fixture JSON files.

Wraps the existing data/loader.py for dev/testing. Write methods
raise NotImplementedError — fixture data is read-only.
"""

import uuid
from typing import Optional
from uuid import UUID

from prism.data.dal import DataAccessLayer
from prism.data.loader import (
    list_companies,
    load_account,
    load_additional_content,
    load_contacts,
    load_signals,
)
from prism.models.account import Account
from prism.models.contact import ContactRecord, LinkedInPost
from prism.models.content import ContentItem
from prism.models.signal import Signal


class FixtureDAL(DataAccessLayer):
    """Read-only DAL that loads from fixture JSON files.

    Used for testing and development when no database is available.
    """

    def __init__(self) -> None:
        # Generate stable UUIDs from slugs for consistent IDs
        self._slug_to_id: dict[str, UUID] = {}

    def _get_id(self, slug: str) -> UUID:
        if slug not in self._slug_to_id:
            self._slug_to_id[slug] = uuid.uuid5(uuid.NAMESPACE_DNS, f"prism.{slug}")
        return self._slug_to_id[slug]

    # ─── Accounts ───────────────────────────────────────────────

    async def get_account(self, slug: str) -> Optional[Account]:
        return load_account(slug)

    async def get_account_by_id(self, account_id: UUID) -> Optional[Account]:
        for slug, uid in self._slug_to_id.items():
            if uid == account_id:
                return load_account(slug)
        # Search all companies
        for slug in list_companies():
            if self._get_id(slug) == account_id:
                return load_account(slug)
        return None

    async def get_account_by_domain(self, domain: str) -> Optional[Account]:
        for slug in list_companies():
            account = load_account(slug)
            if account and account.domain == domain:
                return account
        return None

    async def list_accounts(
        self, status: str = "active", limit: int = 100, offset: int = 0
    ) -> list[Account]:
        slugs = list_companies()
        accounts = []
        for slug in slugs[offset:offset + limit]:
            account = load_account(slug)
            if account:
                accounts.append(account)
        return accounts

    async def upsert_account(self, account: Account) -> UUID:
        raise NotImplementedError("FixtureDAL is read-only")

    async def update_account_status(self, slug: str, status: str) -> None:
        raise NotImplementedError("FixtureDAL is read-only")

    # ─── Contacts ───────────────────────────────────────────────

    async def get_contacts(self, account_id: UUID) -> list[ContactRecord]:
        for slug in list_companies():
            if self._get_id(slug) == account_id:
                return load_contacts(slug)
        return []

    async def upsert_contact(self, account_id: UUID, contact: ContactRecord) -> UUID:
        raise NotImplementedError("FixtureDAL is read-only")

    async def add_linkedin_posts(self, contact_id: UUID, posts: list[LinkedInPost]) -> int:
        raise NotImplementedError("FixtureDAL is read-only")

    # ─── Signals ────────────────────────────────────────────────

    async def get_signals(self, account_id: UUID) -> list[Signal]:
        for slug in list_companies():
            if self._get_id(slug) == account_id:
                return load_signals(slug)
        return []

    async def add_signals(self, account_id: UUID, signals: list[Signal]) -> int:
        raise NotImplementedError("FixtureDAL is read-only")

    # ─── Content ────────────────────────────────────────────────

    async def get_content(
        self, account_id: UUID, source_type: Optional[str] = None, limit: int = 30
    ) -> list[ContentItem]:
        for slug in list_companies():
            if self._get_id(slug) == account_id:
                items = load_additional_content(slug)
                if source_type:
                    items = [i for i in items if i.source_type == source_type]
                return items[:limit]
        return []

    async def add_content(self, account_id: UUID, items: list[ContentItem]) -> int:
        raise NotImplementedError("FixtureDAL is read-only")

    async def get_content_by_url(self, url: str) -> Optional[ContentItem]:
        return None

    async def update_content_status(self, content_id: UUID, status: str) -> None:
        raise NotImplementedError("FixtureDAL is read-only")

    # ─── Analyses ───────────────────────────────────────────────

    async def create_analysis(self, account_id: UUID, prompt_version: str) -> UUID:
        raise NotImplementedError("FixtureDAL is read-only")

    async def update_analysis(self, analysis_id: UUID, **kwargs) -> None:
        raise NotImplementedError("FixtureDAL is read-only")

    async def get_latest_analysis(self, account_id: UUID) -> Optional[dict]:
        return None

    async def get_analysis_history(self, account_id: UUID, limit: int = 10) -> list[dict]:
        return []

    # ─── Dossiers ───────────────────────────────────────────────

    async def save_dossier(
        self, dossier_id: str, account_id: UUID, analysis_id: UUID, markdown_content: str
    ) -> UUID:
        raise NotImplementedError("FixtureDAL is read-only")

    async def get_dossier(self, dossier_id: str) -> Optional[str]:
        return None

    async def get_latest_dossier(self, account_id: UUID) -> Optional[str]:
        return None

    # ─── Raw Responses ──────────────────────────────────────────

    async def write_raw_response(self, account_id, source_type, url, http_status,
                                  raw_headers, raw_body, response_size_bytes=None) -> UUID:
        raise NotImplementedError("FixtureDAL is read-only")

    # ─── Enrichment Log ─────────────────────────────────────────

    async def log_enrichment(self, account_id, source, status, items_added=0, error=None) -> None:
        raise NotImplementedError("FixtureDAL is read-only")

    # ─── Scheduler Queries ──────────────────────────────────────

    async def get_accounts_for_reanalysis(self, max_signal_age_days: int = 7) -> list[Account]:
        return []

    async def get_stale_accounts(self, stale_after_days: int = 30) -> list[Account]:
        return await self.list_accounts()
