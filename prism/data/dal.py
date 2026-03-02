"""Abstract Data Access Layer interface.

Two implementations: DatabaseDAL (PostgreSQL) and FixtureDAL (JSON files).
The analysis pipeline, CLI, and API all use this interface — never talk
directly to the database or fixture loader.
"""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from prism.models.account import Account
from prism.models.contact import ContactRecord, LinkedInPost
from prism.models.content import ContentItem
from prism.models.signal import Signal


class DataAccessLayer(ABC):
    """Abstract data access interface."""

    # ─── Accounts ───────────────────────────────────────────────

    @abstractmethod
    async def get_account(self, slug: str) -> Optional[Account]:
        ...

    @abstractmethod
    async def get_account_by_id(self, account_id: UUID) -> Optional[Account]:
        ...

    @abstractmethod
    async def get_account_by_domain(self, domain: str) -> Optional[Account]:
        ...

    @abstractmethod
    async def list_accounts(
        self, status: str = "active", limit: int = 100, offset: int = 0
    ) -> list[Account]:
        ...

    @abstractmethod
    async def upsert_account(self, account: Account) -> UUID:
        ...

    @abstractmethod
    async def update_account_status(self, slug: str, status: str) -> None:
        ...

    # ─── Contacts ───────────────────────────────────────────────

    @abstractmethod
    async def get_contacts(self, account_id: UUID) -> list[ContactRecord]:
        ...

    @abstractmethod
    async def upsert_contact(self, account_id: UUID, contact: ContactRecord) -> UUID:
        ...

    @abstractmethod
    async def add_linkedin_posts(self, contact_id: UUID, posts: list[LinkedInPost]) -> int:
        ...

    # ─── Signals ────────────────────────────────────────────────

    @abstractmethod
    async def get_signals(self, account_id: UUID) -> list[Signal]:
        ...

    @abstractmethod
    async def add_signals(self, account_id: UUID, signals: list[Signal]) -> int:
        ...

    # ─── Content ────────────────────────────────────────────────

    @abstractmethod
    async def get_content(
        self, account_id: UUID, source_type: Optional[str] = None, limit: int = 30
    ) -> list[ContentItem]:
        ...

    @abstractmethod
    async def add_content(self, account_id: UUID, items: list[ContentItem]) -> int:
        ...

    @abstractmethod
    async def get_content_by_url(self, url: str) -> Optional[ContentItem]:
        ...

    @abstractmethod
    async def update_content_status(self, content_id: UUID, status: str) -> None:
        ...

    # ─── Analyses ───────────────────────────────────────────────

    @abstractmethod
    async def create_analysis(self, account_id: UUID, prompt_version: str) -> UUID:
        ...

    @abstractmethod
    async def update_analysis(self, analysis_id: UUID, **kwargs) -> None:
        ...

    @abstractmethod
    async def get_latest_analysis(self, account_id: UUID) -> Optional[dict]:
        ...

    @abstractmethod
    async def get_analysis_history(self, account_id: UUID, limit: int = 10) -> list[dict]:
        ...

    # ─── Dossiers ───────────────────────────────────────────────

    @abstractmethod
    async def save_dossier(
        self, dossier_id: str, account_id: UUID, analysis_id: UUID, markdown_content: str
    ) -> UUID:
        ...

    @abstractmethod
    async def get_dossier(self, dossier_id: str) -> Optional[str]:
        ...

    @abstractmethod
    async def get_latest_dossier(self, account_id: UUID) -> Optional[str]:
        ...

    # ─── Raw Responses ──────────────────────────────────────────

    @abstractmethod
    async def write_raw_response(
        self,
        account_id: Optional[UUID],
        source_type: str,
        url: Optional[str],
        http_status: Optional[int],
        raw_headers: Optional[dict],
        raw_body: Optional[str],
        response_size_bytes: Optional[int] = None,
    ) -> UUID:
        ...

    # ─── Enrichment Log ─────────────────────────────────────────

    @abstractmethod
    async def log_enrichment(
        self, account_id: UUID, source: str, status: str,
        items_added: int = 0, error: Optional[str] = None,
    ) -> None:
        ...

    # ─── Scheduler Queries ──────────────────────────────────────

    @abstractmethod
    async def get_accounts_for_reanalysis(self, max_signal_age_days: int = 7) -> list[Account]:
        ...

    @abstractmethod
    async def get_stale_accounts(self, stale_after_days: int = 30) -> list[Account]:
        ...
