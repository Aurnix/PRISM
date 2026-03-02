"""Apollo enrichment — contacts, firmographics, and signals via Apollo API.

Requires APOLLO_API_KEY to be configured. If missing, is_available() returns
False and the enrichment orchestrator skips this source.
"""

import logging
from datetime import date
from typing import Optional

import httpx

from prism.models.account import Account
from prism.models.contact import ContactRecord
from prism.models.signal import Signal
from prism.services.enrichment.base import EnrichmentResult, EnrichmentSource

logger = logging.getLogger(__name__)

APOLLO_BASE_URL = "https://api.apollo.io/v1"


class ApolloEnrichment(EnrichmentSource):
    """Contact and firmographic enrichment via Apollo API."""

    def __init__(self) -> None:
        from prism.config import APOLLO_API_KEY

        self._api_key = APOLLO_API_KEY

    def source_name(self) -> str:
        return "apollo"

    def is_available(self) -> bool:
        return bool(self._api_key)

    async def enrich(
        self,
        domain: str,
        existing_account: Optional[Account] = None,
    ) -> EnrichmentResult:
        result = EnrichmentResult(source=self.source_name())
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
        }

        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            await self._enrich_org(client, domain, result)
            await self._enrich_people(client, domain, result)

        return result

    async def _enrich_org(
        self,
        client: httpx.AsyncClient,
        domain: str,
        result: EnrichmentResult,
    ) -> None:
        """Fetch organisation firmographics."""
        try:
            resp = await client.get(
                f"{APOLLO_BASE_URL}/organizations/enrich",
                params={"api_key": self._api_key, "domain": domain},
            )
            if resp.status_code != 200:
                result.errors.append(f"Apollo org enrich returned {resp.status_code}")
                return

            org = resp.json().get("organization", {})
            if not org:
                return

            updates: dict = {}
            if org.get("estimated_num_employees"):
                updates["headcount"] = org["estimated_num_employees"]
            if org.get("industry"):
                updates["industry"] = org["industry"]
            if org.get("short_description"):
                updates["description"] = org["short_description"]
            if org.get("founded_year"):
                updates["founded_year"] = org["founded_year"]

            funding = org.get("total_funding")
            if funding:
                updates["total_raised"] = funding

            latest_round = org.get("latest_funding_round_date")
            if latest_round:
                updates["last_round_date"] = latest_round
                result.signals.append(Signal(
                    signal_type="funding_round",
                    description=f"Latest funding round detected via Apollo",
                    source="apollo",
                    detected_date=date.today(),
                    confidence="extracted",
                ))

            if updates:
                result.account_updates = updates

        except Exception as e:
            msg = f"Apollo org enrichment failed for {domain}: {e}"
            logger.warning(msg)
            result.errors.append(msg)

    async def _enrich_people(
        self,
        client: httpx.AsyncClient,
        domain: str,
        result: EnrichmentResult,
    ) -> None:
        """Search for key contacts at the company."""
        try:
            resp = await client.post(
                f"{APOLLO_BASE_URL}/mixed_people/search",
                json={
                    "api_key": self._api_key,
                    "q_organization_domains": domain,
                    "person_titles": [
                        "VP Finance",
                        "CFO",
                        "Chief Financial Officer",
                        "Controller",
                        "Head of Finance",
                        "CTO",
                        "VP Engineering",
                        "CEO",
                    ],
                    "per_page": 25,
                },
            )
            if resp.status_code != 200:
                result.errors.append(f"Apollo people search returned {resp.status_code}")
                return

            people = resp.json().get("people", [])
            for person in people:
                name = person.get("name", "")
                title = person.get("title", "")
                if not name:
                    continue

                contact = ContactRecord(
                    name=name,
                    title=title,
                    email=person.get("email"),
                    linkedin_url=person.get("linkedin_url"),
                )
                result.contacts.append(contact)

                # Detect new-hire signals from employment history
                months_in_role = person.get("months_in_current_role")
                if months_in_role is not None and months_in_role <= 6:
                    is_finance = any(
                        kw in title.lower()
                        for kw in ("finance", "cfo", "controller", "accounting")
                    )
                    sig_type = (
                        "new_executive_finance" if is_finance else "new_executive_other"
                    )
                    result.signals.append(Signal(
                        signal_type=sig_type,
                        description=f"New hire detected: {name} as {title}",
                        source="apollo",
                        detected_date=date.today(),
                        confidence="extracted",
                    ))

        except Exception as e:
            msg = f"Apollo people search failed for {domain}: {e}"
            logger.warning(msg)
            result.errors.append(msg)
