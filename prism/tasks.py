"""Background task definitions for PRISM.

Provides async task functions for enrichment, analysis, and dossier
generation.  These can be called directly (in-process) or dispatched
through a task queue (arq + Redis) when available.

Usage (in-process):
    result = await enrich_company_task(slug="acme-corp")

Usage (arq worker):
    # worker.py
    from prism.tasks import WorkerSettings
    # Then: arq prism.tasks.WorkerSettings
"""

import logging
from datetime import date
from typing import Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


# ─── Task Functions ───────────────────────────────────────────────────────────


async def enrich_company_task(
    ctx: Optional[dict] = None,
    *,
    slug: str,
    domain: Optional[str] = None,
) -> dict:
    """Run all enrichment sources for a company.

    Args:
        ctx: arq context (unused in direct calls).
        slug: Account slug.
        domain: Company domain. If not given, looks up from account.

    Returns:
        Summary dict with counts per source.
    """
    from prism.data import get_dal
    from prism.services.enrichment.orchestrator import EnrichmentOrchestrator

    dal = get_dal()
    account = await dal.get_account(slug)

    if not account:
        return {"error": f"Account '{slug}' not found"}

    effective_domain = domain or account.domain
    orchestrator = EnrichmentOrchestrator(dal)
    summary = await orchestrator.enrich_company(effective_domain, slug=slug)

    logger.info("Enrichment complete for %s: %s", slug, summary)
    return summary


async def analyze_company_task(
    ctx: Optional[dict] = None,
    *,
    slug: str,
    run_llm: bool = True,
) -> dict:
    """Run the full Content Intelligence pipeline for a company.

    Args:
        ctx: arq context (unused in direct calls).
        slug: Account slug.
        run_llm: Whether to run LLM analysis (False = rules-only).

    Returns:
        Dict with analysis results summary.
    """
    from prism.data import get_dal
    from prism.data.loader import load_contacts, load_signals, load_additional_content
    from prism.models.content import ContentItem as CI
    from prism.pipeline import AnalysisPipeline
    from prism.services import get_llm_backend

    dal = get_dal()
    account = await dal.get_account(slug)

    if not account:
        return {"error": f"Account '{slug}' not found"}

    # Load data
    contacts = load_contacts(slug)
    signals = load_signals(slug)
    content_items = load_additional_content(slug)

    # Add LinkedIn posts as content
    for contact in contacts:
        for post in contact.linkedin_posts:
            content_items.append(CI(
                source_type="linkedin",
                title=f"LinkedIn post by {contact.name}",
                author=contact.name,
                author_role=contact.title,
                publish_date=post.date,
                raw_text=post.text,
                is_authored=True,
            ))

    llm = get_llm_backend()
    pipeline = AnalysisPipeline(llm)

    analyzed, play, brief = await pipeline.analyze(
        account=account,
        contacts=contacts,
        signals=signals,
        content_items=content_items,
        run_llm=run_llm,
    )

    return {
        "status": "complete",
        "account_slug": slug,
        "tier": analyzed.scores.priority_tier,
        "composite_score": round(analyzed.scores.composite_score, 3),
        "play": play.play_name,
    }


async def generate_dossier_task(
    ctx: Optional[dict] = None,
    *,
    slug: str,
    run_llm: bool = True,
) -> dict:
    """Run analysis and generate dossier markdown file.

    Args:
        ctx: arq context (unused in direct calls).
        slug: Account slug.
        run_llm: Whether to run LLM analysis.

    Returns:
        Dict with dossier path and summary.
    """
    from prism.config import DOSSIERS_DIR
    from prism.data import get_dal
    from prism.data.loader import load_contacts, load_signals, load_additional_content
    from prism.models.content import ContentItem as CI
    from prism.output.dossier import render_dossier
    from prism.pipeline import AnalysisPipeline
    from prism.services import get_llm_backend

    dal = get_dal()
    account = await dal.get_account(slug)

    if not account:
        return {"error": f"Account '{slug}' not found"}

    contacts = load_contacts(slug)
    signals = load_signals(slug)
    content_items = load_additional_content(slug)

    for contact in contacts:
        for post in contact.linkedin_posts:
            content_items.append(CI(
                source_type="linkedin",
                title=f"LinkedIn post by {contact.name}",
                author=contact.name,
                author_role=contact.title,
                publish_date=post.date,
                raw_text=post.text,
                is_authored=True,
            ))

    llm = get_llm_backend()
    pipeline = AnalysisPipeline(llm)

    analyzed, play, brief = await pipeline.analyze(
        account=account,
        contacts=contacts,
        signals=signals,
        content_items=content_items,
        run_llm=run_llm,
    )

    dossier = render_dossier(
        account=account,
        analyzed=analyzed,
        contacts=contacts,
        play=play,
        brief=brief,
    )

    DOSSIERS_DIR.mkdir(parents=True, exist_ok=True)
    dossier_path = DOSSIERS_DIR / f"{slug}_dossier.md"
    dossier_path.write_text(dossier)

    return {
        "status": "complete",
        "account_slug": slug,
        "dossier_path": str(dossier_path),
        "tier": analyzed.scores.priority_tier,
    }


async def full_pipeline_task(
    ctx: Optional[dict] = None,
    *,
    slug: str,
    domain: Optional[str] = None,
    run_llm: bool = True,
) -> dict:
    """Run complete pipeline: enrich → analyze → generate dossier.

    Args:
        ctx: arq context (unused in direct calls).
        slug: Account slug.
        domain: Company domain (for enrichment).
        run_llm: Whether to run LLM analysis.

    Returns:
        Combined summary dict.
    """
    enrichment_summary = await enrich_company_task(ctx, slug=slug, domain=domain)
    dossier_result = await generate_dossier_task(ctx, slug=slug, run_llm=run_llm)

    return {
        "enrichment": enrichment_summary,
        "dossier": dossier_result,
    }


# ─── Scheduler Functions ─────────────────────────────────────────────────────


async def daily_reanalyze(ctx: Optional[dict] = None) -> dict:
    """Re-analyze active accounts with recent signals (< 7 days old)."""
    from prism.data import get_dal
    from prism.data.loader import load_signals

    dal = get_dal()
    accounts = await dal.list_accounts(status="active")
    today = date.today()
    reanalyzed: list[str] = []

    for account in accounts:
        signals = load_signals(account.slug)
        has_recent = any(
            (today - s.detected_date).days < 7 for s in signals
        )
        if has_recent:
            await analyze_company_task(ctx, slug=account.slug, run_llm=False)
            reanalyzed.append(account.slug)

    logger.info("Daily reanalyze: processed %d accounts", len(reanalyzed))
    return {"reanalyzed": reanalyzed}


async def weekly_scrape(ctx: Optional[dict] = None) -> dict:
    """Re-scrape blogs for all active accounts."""
    from prism.data import get_dal

    dal = get_dal()
    accounts = await dal.list_accounts(status="active")
    scraped: list[str] = []

    for account in accounts:
        if account.blog_url or account.blog_rss:
            await enrich_company_task(ctx, slug=account.slug)
            scraped.append(account.slug)

    logger.info("Weekly scrape: processed %d accounts", len(scraped))
    return {"scraped": scraped}


# ─── arq Worker Settings ─────────────────────────────────────────────────────


class WorkerSettings:
    """arq worker configuration.

    Start with: ``arq prism.tasks.WorkerSettings``

    Requires REDIS_URL environment variable to be set.
    """

    functions = [
        enrich_company_task,
        analyze_company_task,
        generate_dossier_task,
        full_pipeline_task,
        daily_reanalyze,
        weekly_scrape,
    ]

    @staticmethod
    def redis_settings():
        """Build arq RedisSettings from environment."""
        import os
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        try:
            from arq.connections import RedisSettings
            # Parse redis://host:port/db
            from urllib.parse import urlparse
            parsed = urlparse(redis_url)
            return RedisSettings(
                host=parsed.hostname or "localhost",
                port=parsed.port or 6379,
                database=int(parsed.path.lstrip("/") or 0),
                password=parsed.password,
            )
        except ImportError:
            logger.warning("arq not installed — task queue unavailable")
            return None
