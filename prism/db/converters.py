"""Bidirectional conversion between Pydantic models and SQLAlchemy rows.

All conversion logic is centralized here — not scattered across models.
"""

from datetime import date
from typing import Optional
from uuid import UUID

from prism.db.models import (
    AccountRow,
    AnalysisRow,
    ContactRow,
    ContentItemRow,
    LinkedInPostRow,
    SignalRow,
)
from prism.models.account import Account, Firmographics, TechStack
from prism.models.analysis import (
    AnalyzedAccount,
    ConfidenceAssessment,
    ContentIntelligenceSummary,
    ScoreBreakdown,
    WhyNowHypothesis,
)
from prism.models.contact import ContactRecord, LinkedInPost
from prism.models.content import ContentItem
from prism.models.signal import Signal


# ─── Account ────────────────────────────────────────────────────────────────


def row_to_account(row: AccountRow) -> Account:
    """Convert AccountRow to Pydantic Account."""
    return Account(
        slug=row.slug,
        company_name=row.company_name,
        domain=row.domain,
        blog_url=row.blog_url,
        blog_rss=row.blog_rss,
        firmographics=Firmographics(**(row.firmographics or {})),
        tech_stack=TechStack(**(row.tech_stack or {})),
    )


def account_to_row_dict(account: Account) -> dict:
    """Convert Pydantic Account to dict for insert/update."""
    return {
        "slug": account.slug,
        "company_name": account.company_name,
        "domain": account.domain,
        "blog_url": account.blog_url,
        "blog_rss": account.blog_rss,
        "firmographics": account.firmographics.model_dump(mode="json"),
        "tech_stack": account.tech_stack.model_dump(mode="json"),
    }


# ─── Contact ────────────────────────────────────────────────────────────────


def row_to_contact(row: ContactRow) -> ContactRecord:
    """Convert ContactRow (with loaded linkedin_posts) to Pydantic ContactRecord."""
    posts = [
        LinkedInPost(date=p.post_date, text=p.text)
        for p in (row.linkedin_posts or [])
    ]
    return ContactRecord(
        name=row.name,
        title=row.title,
        linkedin_url=row.linkedin_url,
        email=row.email,
        start_date_current_role=row.start_date_current_role,
        previous_company=row.previous_company,
        previous_title=row.previous_title,
        buying_role=row.buying_role,
        buying_role_confidence=row.buying_role_confidence,
        linkedin_posts=posts,
    )


def contact_to_row_dict(account_id: UUID, contact: ContactRecord) -> dict:
    """Convert Pydantic ContactRecord to dict for insert/update."""
    return {
        "account_id": account_id,
        "name": contact.name,
        "title": contact.title,
        "email": contact.email,
        "linkedin_url": contact.linkedin_url,
        "start_date_current_role": contact.start_date_current_role,
        "previous_company": contact.previous_company,
        "previous_title": contact.previous_title,
        "buying_role": contact.buying_role,
        "buying_role_confidence": contact.buying_role_confidence,
    }


# ─── Signal ──────────────────────────────────────────────────────────────────


def row_to_signal(row: SignalRow) -> Signal:
    """Convert SignalRow to Pydantic Signal."""
    return Signal(
        signal_type=row.signal_type,
        description=row.summary,
        source=row.source,
        detected_date=row.detected_date,
        confidence=row.confidence,
        decay_weight=0.0,  # Calculated at analysis time
    )


def signal_to_row_dict(account_id: UUID, signal: Signal) -> dict:
    """Convert Pydantic Signal to dict for insert."""
    return {
        "account_id": account_id,
        "signal_type": signal.signal_type,
        "summary": signal.description,
        "source": signal.source,
        "detected_date": signal.detected_date,
        "confidence": signal.confidence,
    }


# ─── Content ─────────────────────────────────────────────────────────────────


def row_to_content_item(row: ContentItemRow) -> ContentItem:
    """Convert ContentItemRow to Pydantic ContentItem."""
    return ContentItem(
        source_type=row.source_type,
        url=row.url,
        title=row.title,
        author=row.author,
        author_role=row.author_role,
        publish_date=row.publish_date,
        raw_text=row.body_text,
        word_count=row.word_count or 0,
        is_authored=row.is_authored,
    )


def content_item_to_row_dict(account_id: UUID, item: ContentItem) -> dict:
    """Convert Pydantic ContentItem to dict for insert."""
    return {
        "account_id": account_id,
        "source_type": item.source_type,
        "url": item.url,
        "title": item.title,
        "author": item.author,
        "author_role": item.author_role,
        "publish_date": item.publish_date,
        "body_text": item.raw_text,
        "word_count": item.word_count,
        "is_authored": item.is_authored,
    }


# ─── Analysis ────────────────────────────────────────────────────────────────


def row_to_analyzed_account(row: AnalysisRow, account: Account) -> AnalyzedAccount:
    """Convert AnalysisRow + Account to Pydantic AnalyzedAccount."""
    scores_data = row.scores or {}
    scores = ScoreBreakdown(
        icp_fit_score=scores_data.get("icp_fit_score", 0.0),
        buying_readiness_score=scores_data.get("buying_readiness_score", 0.0),
        timing_score=scores_data.get("timing_score", 0.0),
        composite_score=scores_data.get("composite_score", 0.0),
        priority_tier=scores_data.get("priority_tier", "not_qualified"),
        icp_components=scores_data.get("icp_components", {}),
        readiness_components=scores_data.get("readiness_components", {}),
        timing_components=scores_data.get("timing_components", {}),
    )

    why_now_data = row.why_now or {}
    why_now = WhyNowHypothesis(
        headline=why_now_data.get("headline", ""),
        narrative=why_now_data.get("narrative", ""),
        trigger_event=why_now_data.get("trigger_event"),
        window_estimate=why_now_data.get("window_estimate", ""),
    )

    confidence_data = row.confidence or {}
    confidence = ConfidenceAssessment(
        overall_confidence=confidence_data.get("overall_confidence", "low"),
        counter_signals=confidence_data.get("counter_signals", []),
        corpus_size=confidence_data.get("corpus_size", 0),
        corpus_quality=confidence_data.get("corpus_quality", "low"),
        corpus_sufficient=confidence_data.get("corpus_sufficient", False),
    )

    return AnalyzedAccount(
        account_slug=account.slug,
        company_name=account.company_name,
        domain=account.domain,
        analysis_date=row.created_at.date() if row.created_at else date.today(),
        prompt_version=row.prompt_version,
        scores=scores,
        journey_position=row.journey_position or 0.0,
        journey_position_label=row.journey_label or "status_quo",
        journey_velocity=row.journey_velocity or "stable",
        why_now=why_now,
        confidence=confidence,
        signals=[],
        total_input_tokens=row.total_input_tokens,
        total_output_tokens=row.total_output_tokens,
        total_api_calls=row.total_api_calls,
        estimated_cost_usd=row.estimated_cost_usd,
        limited_analysis=row.limited_analysis,
        limited_analysis_reason=row.limited_reason,
    )
