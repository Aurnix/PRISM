"""Job board enrichment — Greenhouse and Lever public APIs.

Both APIs are public (no authentication required) and return published
job listings.  Finance/accounting keyword detection creates hiring signals.
"""

import logging
import re
from datetime import date
from typing import Optional

import httpx

from prism.models.account import Account
from prism.models.content import ContentItem
from prism.models.signal import Signal
from prism.services.enrichment.base import EnrichmentResult, EnrichmentSource

logger = logging.getLogger(__name__)

FINANCE_KEYWORDS = re.compile(
    r"(?i)\b(financ|account|controller|cfo|bookkeep|treasury|"
    r"revenue recognition|asc\s*606|month.end|audit|ledger|"
    r"quickbooks|netsuite|xero|sage|erp)\b"
)

TECH_KEYWORDS = re.compile(
    r"(?i)\b(data engineer|data scientist|machine learning|platform|"
    r"infrastructure|devops|sre|cloud|backend|fullstack)\b"
)


def _slug_from_domain(domain: str) -> str:
    """Best-guess Greenhouse/Lever board slug from domain."""
    return domain.split(".")[0].lower().replace("-", "")


class JobBoardEnrichment(EnrichmentSource):
    """Job posting enrichment from Greenhouse and Lever public APIs."""

    def source_name(self) -> str:
        return "job_boards"

    def is_available(self) -> bool:
        return True  # Public APIs

    async def enrich(
        self,
        domain: str,
        existing_account: Optional[Account] = None,
    ) -> EnrichmentResult:
        result = EnrichmentResult(source=self.source_name())
        board_slug = _slug_from_domain(domain)

        async with httpx.AsyncClient(timeout=10.0) as client:
            await self._try_greenhouse(client, board_slug, domain, result)
            await self._try_lever(client, board_slug, domain, result)

        logger.info(
            "Job boards found %d content items and %d signals for %s",
            len(result.content_items),
            len(result.signals),
            domain,
        )
        return result

    async def _try_greenhouse(
        self,
        client: httpx.AsyncClient,
        board_slug: str,
        domain: str,
        result: EnrichmentResult,
    ) -> None:
        url = f"https://boards-api.greenhouse.io/v1/boards/{board_slug}/jobs"
        try:
            resp = await client.get(url, params={"content": "true"})
            if resp.status_code != 200:
                return
            data = resp.json()
            jobs = data.get("jobs", [])
            self._process_jobs(jobs, "greenhouse", domain, result)
        except Exception as e:
            logger.debug("Greenhouse lookup failed for %s: %s", board_slug, e)

    async def _try_lever(
        self,
        client: httpx.AsyncClient,
        board_slug: str,
        domain: str,
        result: EnrichmentResult,
    ) -> None:
        url = f"https://api.lever.co/v0/postings/{board_slug}"
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return
            jobs = resp.json()
            if not isinstance(jobs, list):
                return
            normalised = []
            for j in jobs:
                normalised.append({
                    "title": j.get("text", ""),
                    "content": j.get("descriptionPlain", j.get("description", "")),
                    "updated_at": j.get("createdAt"),
                    "absolute_url": j.get("hostedUrl", ""),
                })
            self._process_jobs(normalised, "lever", domain, result)
        except Exception as e:
            logger.debug("Lever lookup failed for %s: %s", board_slug, e)

    def _process_jobs(
        self,
        jobs: list[dict],
        source: str,
        domain: str,
        result: EnrichmentResult,
    ) -> None:
        today = date.today()

        for job in jobs:
            title = job.get("title", "")
            content = job.get("content", "")
            url = job.get("absolute_url", "")
            full_text = f"{title}\n\n{content}"

            result.content_items.append(ContentItem(
                source_type="job_posting",
                title=title,
                raw_text=full_text[:5000],
                url=url,
                publish_date=today,
            ))

            if FINANCE_KEYWORDS.search(full_text):
                signal_type = "job_posting_finance"
                desc = f"Finance/accounting job posting: {title}"
            elif TECH_KEYWORDS.search(full_text):
                signal_type = "job_posting_technical"
                desc = f"Technical job posting: {title}"
            else:
                continue

            result.signals.append(Signal(
                signal_type=signal_type,
                description=desc,
                source=f"{source}:{domain}",
                detected_date=today,
                confidence="extracted",
            ))
