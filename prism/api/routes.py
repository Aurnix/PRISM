"""FastAPI routes for PRISM REST API."""

import logging
import re
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from prism.api.deps import get_dal_dep, get_llm_dep, verify_api_key
from prism.api.schemas import (
    AccountCreate,
    AccountListItem,
    AccountResponse,
    AccountUpdate,
    AnalyzeRequest,
    AnalyzeResponse,
    ContentUpload,
    DossierResponse,
    HealthResponse,
    SignalResponse,
)
from prism.data.dal import DataAccessLayer
from prism.models.account import Account, Firmographics, TechStack
from prism.models.content import ContentItem
from prism.services.llm_backend import LLMBackend

logger = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")

router = APIRouter(dependencies=[Depends(verify_api_key)])


def _validate_slug(slug: str) -> str:
    """Validate slug is safe for filesystem and database use."""
    if not _SLUG_RE.match(slug):
        raise HTTPException(
            status_code=400,
            detail="Invalid slug: must be alphanumeric with hyphens/underscores, 1-64 chars",
        )
    return slug


# ─── Health ──────────────────────────────────────────────────────────────────


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness check."""
    from prism.config import DATABASE_URL
    db_status = "connected" if DATABASE_URL else "not_configured (using fixtures)"
    return HealthResponse(status="ok", version="1.0.0", database=db_status)


# ─── Accounts ────────────────────────────────────────────────────────────────


@router.get("/accounts", response_model=list[AccountListItem])
async def list_accounts(
    status: str = "active",
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    dal: DataAccessLayer = Depends(get_dal_dep),
) -> list[AccountListItem]:
    """List tracked companies with latest scores/tiers."""
    accounts = await dal.list_accounts(status=status, limit=limit, offset=offset)
    items = []
    for acct in accounts:
        f = acct.firmographics
        items.append(AccountListItem(
            slug=acct.slug,
            company_name=acct.company_name,
            domain=acct.domain,
            industry=f.industry,
            funding_stage=f.funding_stage,
            headcount=f.headcount,
        ))
    return items


@router.post("/accounts", response_model=AccountResponse, status_code=201)
async def create_account(
    body: AccountCreate,
    dal: DataAccessLayer = Depends(get_dal_dep),
) -> AccountResponse:
    """Add a company to track."""
    _validate_slug(body.slug)
    account = Account(
        slug=body.slug,
        company_name=body.company_name,
        domain=body.domain,
        blog_url=body.blog_url,
        blog_rss=body.blog_rss,
        firmographics=Firmographics(**body.firmographics),
        tech_stack=TechStack(**body.tech_stack),
    )
    try:
        await dal.upsert_account(account)
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="Write operations require database configuration")

    return AccountResponse(
        slug=account.slug,
        company_name=account.company_name,
        domain=account.domain,
        blog_url=account.blog_url,
        blog_rss=account.blog_rss,
        firmographics=account.firmographics.model_dump(mode="json"),
        tech_stack=account.tech_stack.model_dump(mode="json"),
    )


@router.get("/accounts/{slug}", response_model=AccountResponse)
async def get_account(
    slug: str,
    dal: DataAccessLayer = Depends(get_dal_dep),
) -> AccountResponse:
    """Full account detail with latest analysis."""
    _validate_slug(slug)
    account = await dal.get_account(slug)
    if not account:
        raise HTTPException(status_code=404, detail=f"Account '{slug}' not found")

    return AccountResponse(
        slug=account.slug,
        company_name=account.company_name,
        domain=account.domain,
        blog_url=account.blog_url,
        blog_rss=account.blog_rss,
        firmographics=account.firmographics.model_dump(mode="json"),
        tech_stack=account.tech_stack.model_dump(mode="json"),
    )


@router.patch("/accounts/{slug}", response_model=AccountResponse)
async def update_account(
    slug: str,
    body: AccountUpdate,
    dal: DataAccessLayer = Depends(get_dal_dep),
) -> AccountResponse:
    """Update account data."""
    _validate_slug(slug)
    account = await dal.get_account(slug)
    if not account:
        raise HTTPException(status_code=404, detail=f"Account '{slug}' not found")

    if body.status:
        try:
            await dal.update_account_status(slug, body.status)
        except NotImplementedError:
            raise HTTPException(status_code=501, detail="Write operations require database configuration")

    # Re-fetch after update
    account = await dal.get_account(slug)
    return AccountResponse(
        slug=account.slug,
        company_name=account.company_name,
        domain=account.domain,
        blog_url=account.blog_url,
        blog_rss=account.blog_rss,
        firmographics=account.firmographics.model_dump(mode="json"),
        tech_stack=account.tech_stack.model_dump(mode="json"),
    )


@router.delete("/accounts/{slug}", status_code=204)
async def delete_account(
    slug: str,
    dal: DataAccessLayer = Depends(get_dal_dep),
) -> None:
    """Archive (soft delete) an account."""
    _validate_slug(slug)
    account = await dal.get_account(slug)
    if not account:
        raise HTTPException(status_code=404, detail=f"Account '{slug}' not found")
    try:
        await dal.update_account_status(slug, "archived")
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="Write operations require database configuration")


# ─── Analysis ────────────────────────────────────────────────────────────────


@router.post("/accounts/{slug}/analyze", response_model=AnalyzeResponse)
async def trigger_analysis(
    slug: str,
    body: AnalyzeRequest = AnalyzeRequest(),
    dal: DataAccessLayer = Depends(get_dal_dep),
    llm: LLMBackend = Depends(get_llm_dep),
) -> AnalyzeResponse:
    """Trigger analysis for an account. Runs synchronously in v1."""
    _validate_slug(slug)
    from prism.data.loader import load_contacts, load_signals, load_additional_content
    from prism.models.content import ContentItem as CI
    from prism.pipeline import AnalysisPipeline
    from prism.output.dossier import render_dossier
    from prism.config import DOSSIERS_DIR

    account = await dal.get_account(slug)
    if not account:
        raise HTTPException(status_code=404, detail=f"Account '{slug}' not found")

    # Load data — from DAL or fixture loader
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

    pipeline = AnalysisPipeline(llm)
    analyzed, play, brief = await pipeline.analyze(
        account=account,
        contacts=contacts,
        signals=signals,
        content_items=content_items,
        run_llm=True,
    )

    # Save dossier
    dossier = render_dossier(
        account=account, analyzed=analyzed, contacts=contacts, play=play, brief=brief,
    )
    DOSSIERS_DIR.mkdir(parents=True, exist_ok=True)
    (DOSSIERS_DIR / f"{slug}_dossier.md").write_text(dossier)

    return AnalyzeResponse(
        status="complete",
        message=f"Analysis complete. Tier: {analyzed.scores.priority_tier}, Composite: {analyzed.scores.composite_score:.0%}",
        account_slug=slug,
    )


@router.post("/accounts/{slug}/enrich")
async def trigger_enrichment(
    slug: str,
    dal: DataAccessLayer = Depends(get_dal_dep),
) -> dict:
    """Run enrichment sources for an account."""
    _validate_slug(slug)
    from prism.services.enrichment.orchestrator import EnrichmentOrchestrator

    account = await dal.get_account(slug)
    if not account:
        raise HTTPException(status_code=404, detail=f"Account '{slug}' not found")

    orchestrator = EnrichmentOrchestrator(dal)
    summary = await orchestrator.enrich_company(account.domain, slug=slug)

    return {"status": "complete", "account_slug": slug, "sources": summary}


@router.get("/accounts/{slug}/analyses")
async def get_analyses(
    slug: str,
    limit: int = 10,
    dal: DataAccessLayer = Depends(get_dal_dep),
) -> list[dict]:
    """Get analysis history for an account."""
    _validate_slug(slug)
    account = await dal.get_account(slug)
    if not account:
        raise HTTPException(status_code=404, detail=f"Account '{slug}' not found")

    # For fixture DAL, return empty list
    try:
        from prism.data.fixture_dal import FixtureDAL
        if isinstance(dal, FixtureDAL):
            return []
    except ImportError:
        pass

    return []


# ─── Signals ─────────────────────────────────────────────────────────────────


@router.get("/accounts/{slug}/signals", response_model=list[SignalResponse])
async def get_signals(
    slug: str,
    dal: DataAccessLayer = Depends(get_dal_dep),
) -> list[SignalResponse]:
    """List signals for an account with decay weights."""
    _validate_slug(slug)
    from prism.analysis.signal_decay import calculate_decay_weight
    from prism.data.loader import load_signals

    account = await dal.get_account(slug)
    if not account:
        raise HTTPException(status_code=404, detail=f"Account '{slug}' not found")

    signals = load_signals(slug)
    current = date.today()

    return [
        SignalResponse(
            signal_type=s.signal_type,
            description=s.description,
            source=s.source,
            detected_date=s.detected_date,
            confidence=s.confidence,
            decay_weight=calculate_decay_weight(s.signal_type, s.detected_date, current),
        )
        for s in signals
    ]


# ─── Content ─────────────────────────────────────────────────────────────────


@router.post("/accounts/{slug}/content", status_code=201)
async def upload_content(
    slug: str,
    body: ContentUpload,
    dal: DataAccessLayer = Depends(get_dal_dep),
) -> dict:
    """Upload content manually for an account."""
    _validate_slug(slug)
    account = await dal.get_account(slug)
    if not account:
        raise HTTPException(status_code=404, detail=f"Account '{slug}' not found")

    item = ContentItem(
        source_type=body.source_type,
        title=body.title,
        author=body.author,
        publish_date=body.publish_date,
        raw_text=body.raw_text,
        url=body.url,
    )

    try:
        # For fixture mode, just acknowledge receipt
        return {"status": "received", "source_type": body.source_type}
    except Exception as e:
        logger.exception("Error uploading content for %s", slug)
        raise HTTPException(status_code=500, detail="Failed to process content upload")


# ─── Dossiers ────────────────────────────────────────────────────────────────


@router.get("/accounts/{slug}/dossier", response_model=DossierResponse)
async def get_latest_dossier(
    slug: str,
    dal: DataAccessLayer = Depends(get_dal_dep),
) -> DossierResponse:
    """Get the latest dossier for an account."""
    _validate_slug(slug)
    from prism.config import DOSSIERS_DIR

    account = await dal.get_account(slug)
    if not account:
        raise HTTPException(status_code=404, detail=f"Account '{slug}' not found")

    # Check filesystem for dossier — resolve to prevent path traversal
    dossier_path = (DOSSIERS_DIR / f"{slug}_dossier.md").resolve()
    if not str(dossier_path).startswith(str(DOSSIERS_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Invalid slug")
    if dossier_path.exists():
        return DossierResponse(
            account_slug=slug,
            markdown_content=dossier_path.read_text(),
        )

    raise HTTPException(status_code=404, detail=f"No dossier found for '{slug}'")


@router.get("/dossiers/{dossier_id}", response_model=DossierResponse)
async def get_dossier_by_id(
    dossier_id: str,
    dal: DataAccessLayer = Depends(get_dal_dep),
) -> DossierResponse:
    """Retrieve dossier by PRISM-YYYY-NNNN ID."""
    content = await dal.get_dossier(dossier_id)
    if not content:
        raise HTTPException(status_code=404, detail=f"Dossier '{dossier_id}' not found")
    return DossierResponse(
        dossier_id=dossier_id,
        account_slug="",
        markdown_content=content,
    )
