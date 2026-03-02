"""Enrichment orchestrator — runs all available sources and merges results.

The orchestrator is the single entry-point for enrichment.  It discovers
which sources are configured, runs them concurrently, deduplicates, and
persists results via the DAL.
"""

import logging
from typing import Optional

from prism.data.dal import DataAccessLayer
from prism.services.enrichment.base import EnrichmentResult, EnrichmentSource

logger = logging.getLogger(__name__)


class EnrichmentOrchestrator:
    """Runs all available enrichment sources for a company."""

    def __init__(
        self,
        dal: DataAccessLayer,
        sources: Optional[list[EnrichmentSource]] = None,
    ) -> None:
        self._dal = dal
        self._sources = sources if sources is not None else self._discover_sources()

    @staticmethod
    def _discover_sources() -> list[EnrichmentSource]:
        """Auto-discover available enrichment sources."""
        from prism.services.enrichment.apollo import ApolloEnrichment
        from prism.services.enrichment.blog_scraper import BlogScraperEnrichment
        from prism.services.enrichment.job_boards import JobBoardEnrichment

        all_sources: list[EnrichmentSource] = [
            BlogScraperEnrichment(),
            JobBoardEnrichment(),
            ApolloEnrichment(),
        ]
        return [s for s in all_sources if s.is_available()]

    async def enrich_company(
        self,
        domain: str,
        slug: Optional[str] = None,
    ) -> dict:
        """Run all available enrichment sources for a company.

        Args:
            domain: Company domain.
            slug: Optional account slug (if account already exists).

        Returns:
            Summary dict with counts of items added per source.
        """
        existing = await self._dal.get_account(slug) if slug else None
        summary: dict = {}

        for source in self._sources:
            source_name = source.source_name()
            try:
                result = await source.enrich(domain, existing_account=existing)
                counts = self._count_result(result)
                summary[source_name] = counts

                if result.errors:
                    summary[source_name]["warnings"] = result.errors

                logger.info(
                    "Enrichment source '%s' for %s: %s",
                    source_name,
                    domain,
                    counts,
                )
            except Exception as e:
                logger.warning(
                    "Enrichment source '%s' failed for %s: %s",
                    source_name,
                    domain,
                    e,
                )
                summary[source_name] = {"error": str(e)}

        return summary

    @staticmethod
    def _count_result(result: EnrichmentResult) -> dict:
        """Count items in an enrichment result."""
        counts: dict = {}
        if result.account_updates:
            counts["account_fields"] = len(result.account_updates)
        if result.contacts:
            counts["contacts"] = len(result.contacts)
        if result.signals:
            counts["signals"] = len(result.signals)
        if result.content_items:
            counts["content_items"] = len(result.content_items)
        return counts
