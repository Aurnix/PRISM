"""Fixture data loader.

Loads company fixture data from JSON files in fixtures/companies/.
"""

import json
import logging
from datetime import date
from pathlib import Path
from typing import Optional

from prism.config import COMPANIES_DIR, SCRAPED_CONTENT_DIR
from prism.models.account import Account, Firmographics, TechStack
from prism.models.contact import ContactRecord, LinkedInPost
from prism.models.content import ContentItem
from prism.models.signal import Signal

logger = logging.getLogger(__name__)


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse an ISO date string."""
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        logger.warning("Could not parse date: %s", date_str)
        return None


def load_account(slug: str) -> Optional[Account]:
    """Load account data from fixture JSON.

    Args:
        slug: Company slug (filename without .json).

    Returns:
        Account model or None if not found.
    """
    filepath = COMPANIES_DIR / f"{slug}.json"
    if not filepath.exists():
        logger.error("Fixture file not found: %s", filepath)
        return None

    try:
        data = json.loads(filepath.read_text())
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in %s: %s", filepath, e)
        return None

    firm_data = data.get("firmographics", {})
    firmographics = Firmographics(
        founded_year=firm_data.get("founded_year"),
        headcount=firm_data.get("headcount"),
        headcount_growth_12mo=firm_data.get("headcount_growth_12mo"),
        funding_stage=firm_data.get("funding_stage"),
        total_raised=firm_data.get("total_raised"),
        last_round_amount=firm_data.get("last_round_amount"),
        last_round_date=_parse_date(firm_data.get("last_round_date")),
        last_round_lead=firm_data.get("last_round_lead"),
        industry=firm_data.get("industry"),
        hq_location=firm_data.get("hq_location"),
        description=firm_data.get("description"),
    )

    tech_data = data.get("tech_stack", {})
    tech_stack = TechStack(
        erp_accounting=tech_data.get("erp_accounting"),
        crm=tech_data.get("crm"),
        payment_processor=tech_data.get("payment_processor"),
        cloud_provider=tech_data.get("cloud_provider"),
        primary_languages=tech_data.get("primary_languages", []),
        stack_maturity=tech_data.get("stack_maturity"),
        migration_signals=tech_data.get("migration_signals", []),
    )

    return Account(
        slug=data.get("slug", slug),
        company_name=data.get("company_name", slug),
        domain=data.get("domain", ""),
        blog_url=data.get("blog_url"),
        blog_rss=data.get("blog_rss"),
        firmographics=firmographics,
        tech_stack=tech_stack,
    )


def load_contacts(slug: str) -> list[ContactRecord]:
    """Load contacts from fixture JSON.

    Args:
        slug: Company slug.

    Returns:
        List of ContactRecord models.
    """
    filepath = COMPANIES_DIR / f"{slug}.json"
    if not filepath.exists():
        return []

    data = json.loads(filepath.read_text())
    contacts = []

    for c in data.get("contacts", []):
        posts = [
            LinkedInPost(
                date=date.fromisoformat(p["date"]),
                text=p["text"],
            )
            for p in c.get("linkedin_posts", [])
            if p.get("date") and p.get("text")
        ]

        contacts.append(ContactRecord(
            name=c["name"],
            title=c["title"],
            linkedin_url=c.get("linkedin_url"),
            email=c.get("email"),
            start_date_current_role=_parse_date(c.get("start_date_current_role")),
            previous_company=c.get("previous_company"),
            previous_title=c.get("previous_title"),
            buying_role=c.get("buying_role", "unknown"),
            buying_role_confidence=c.get("buying_role_confidence", 0.5),
            linkedin_posts=posts,
        ))

    return contacts


def load_signals(slug: str) -> list[Signal]:
    """Load signals from fixture JSON.

    Args:
        slug: Company slug.

    Returns:
        List of Signal models.
    """
    filepath = COMPANIES_DIR / f"{slug}.json"
    if not filepath.exists():
        return []

    data = json.loads(filepath.read_text())
    signals = []

    for s in data.get("signals", []):
        signals.append(Signal(
            signal_type=s["signal_type"],
            description=s["description"],
            source=s.get("source", "fixture"),
            detected_date=date.fromisoformat(s["detected_date"]),
            confidence=s.get("confidence", "extracted"),
        ))

    return signals


def load_additional_content(slug: str) -> list[ContentItem]:
    """Load additional content items from fixture JSON.

    Args:
        slug: Company slug.

    Returns:
        List of ContentItem models.
    """
    filepath = COMPANIES_DIR / f"{slug}.json"
    if not filepath.exists():
        return []

    data = json.loads(filepath.read_text())
    items = []

    for c in data.get("additional_content", []):
        items.append(ContentItem(
            source_type=c["source_type"],
            url=c.get("url"),
            title=c.get("title"),
            author=c.get("author"),
            author_role=c.get("author_role"),
            publish_date=date.fromisoformat(c["date"]),
            raw_text=c["text"],
            is_authored=bool(c.get("author")),
        ))

    return items


def load_scraped_content(slug: str) -> list[ContentItem]:
    """Load previously scraped and cached content.

    Args:
        slug: Company slug.

    Returns:
        List of ContentItem models from cached scrapes.
    """
    cache_dir = SCRAPED_CONTENT_DIR / slug
    blog_file = cache_dir / "blog_posts.json"

    if not blog_file.exists():
        return []

    try:
        posts = json.loads(blog_file.read_text())
    except json.JSONDecodeError:
        logger.warning("Invalid JSON in cached blog posts for %s", slug)
        return []

    items = []
    for post in posts:
        items.append(ContentItem(
            source_type="blog",
            url=post.get("url"),
            title=post.get("title"),
            author=post.get("author"),
            author_role=post.get("author_role"),
            publish_date=date.fromisoformat(post["date"]),
            raw_text=post["text"],
            is_authored=bool(post.get("author")),
        ))

    return items


def list_companies() -> list[str]:
    """List all available company slugs in fixtures directory.

    Returns:
        Sorted list of company slugs.
    """
    if not COMPANIES_DIR.exists():
        return []

    slugs = []
    for f in sorted(COMPANIES_DIR.glob("*.json")):
        if f.stem != "_template":
            slugs.append(f.stem)
    return slugs
