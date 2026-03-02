"""Abstract enrichment source interface.

Each enrichment source is optional.  If the required API key or
configuration is missing, ``is_available()`` returns ``False`` and the
orchestrator skips it automatically.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from prism.models.account import Account
from prism.models.contact import ContactRecord
from prism.models.content import ContentItem
from prism.models.signal import Signal


@dataclass
class EnrichmentResult:
    """Standardised result from any enrichment source."""

    source: str  # 'apollo', 'blog_scraper', 'job_boards', …
    account_updates: Optional[dict] = None  # Firmographics / tech_stack deltas
    contacts: list[ContactRecord] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)
    content_items: list[ContentItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class EnrichmentSource(ABC):
    """Abstract interface for data enrichment sources."""

    @abstractmethod
    def source_name(self) -> str:
        """Human-readable source name for logging."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """True if this source is configured and ready."""
        ...

    @abstractmethod
    async def enrich(
        self,
        domain: str,
        existing_account: Optional[Account] = None,
    ) -> EnrichmentResult:
        """Enrich a company by domain.

        Args:
            domain: Company domain (e.g. 'velocitypay.com').
            existing_account: Pass existing data so the source can avoid
                redundant lookups and merge intelligently.

        Returns:
            EnrichmentResult with whatever data this source provides.
        """
        ...
