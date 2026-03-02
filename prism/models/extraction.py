"""Extraction pipeline data models — structured output from raw content.

Defines ExtractionResult (output of LLM extraction) and signal typed_data
schemas for each signal category. Used by the extraction service to convert
raw HTML/text into structured signals and content items.
"""

from datetime import date
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


# ─── Signal Typed Data Schemas ───────────────────────────────────────────────


class FundingRoundData(BaseModel):
    """Typed data for funding_round signals."""

    signal_type: Literal["funding_round"] = "funding_round"
    amount: Optional[float] = None
    currency: str = "USD"
    round_type: Optional[str] = None  # seed, series_a, series_b, etc.
    lead_investors: list[str] = Field(default_factory=list)
    valuation: Optional[float] = None


class RevenueData(BaseModel):
    """Typed data for revenue milestone signals."""

    signal_type: Literal["revenue_milestone"] = "revenue_milestone"
    metric: Optional[str] = None  # ARR, MRR, revenue
    value: Optional[float] = None
    growth_rate: Optional[float] = None


class JobPostingData(BaseModel):
    """Typed data for job posting signals."""

    signal_type: Literal["job_posting"] = "job_posting"
    job_title: Optional[str] = None
    department: Optional[str] = None  # finance, engineering, sales
    seniority: Optional[str] = None  # junior, mid, senior, director, vp, c-level
    skills: list[str] = Field(default_factory=list)
    urgency_indicators: list[str] = Field(default_factory=list)


class KeyHireData(BaseModel):
    """Typed data for key hire signals."""

    signal_type: Literal["key_hire"] = "key_hire"
    name: Optional[str] = None
    title: Optional[str] = None
    previous_company: Optional[str] = None
    previous_title: Optional[str] = None
    department: Optional[str] = None


class TechDetectedData(BaseModel):
    """Typed data for technology detection signals."""

    signal_type: Literal["tech_detected"] = "tech_detected"
    technology: str
    category: Optional[str] = None  # erp, crm, cloud, etc.
    evidence: Optional[str] = None
    version: Optional[str] = None


class TechMigrationData(BaseModel):
    """Typed data for technology migration signals."""

    signal_type: Literal["tech_migration"] = "tech_migration"
    from_tech: Optional[str] = None
    to_tech: Optional[str] = None
    category: Optional[str] = None
    evidence: Optional[str] = None


class LeadershipChangeData(BaseModel):
    """Typed data for leadership change signals."""

    signal_type: Literal["leadership_change"] = "leadership_change"
    name: Optional[str] = None
    new_title: Optional[str] = None
    previous_title: Optional[str] = None
    change_type: Optional[str] = None  # hired, promoted, departed


class CompetitorMentionData(BaseModel):
    """Typed data for competitor mention signals."""

    signal_type: Literal["competitor_mention"] = "competitor_mention"
    competitor: str
    context: Optional[str] = None  # evaluation, switch, complaint, comparison
    sentiment: Optional[str] = None  # positive, negative, neutral


class ContentRemovedData(BaseModel):
    """Typed data for content removal (absence) signals."""

    signal_type: Literal["content_removed"] = "content_removed"
    url: Optional[str] = None
    original_title: Optional[str] = None
    detection_method: Optional[str] = None  # 404, redirect, content_change


# Union type for all signal typed data
SignalTypedData = Union[
    FundingRoundData,
    RevenueData,
    JobPostingData,
    KeyHireData,
    TechDetectedData,
    TechMigrationData,
    LeadershipChangeData,
    CompetitorMentionData,
    ContentRemovedData,
]


# ─── Extraction Result ──────────────────────────────────────────────────────


class PageClassification(BaseModel):
    """Classification of a web page."""

    page_type: str = "unknown"  # blog_post, job_listing, press_release, about_page, etc.
    content_category: str = "unknown"  # technical, hiring, financial, thought_leadership
    relevance: str = "medium"  # high, medium, low


class ExtractedContent(BaseModel):
    """Extracted text content from a page."""

    title: Optional[str] = None
    author: Optional[str] = None
    publish_date: Optional[date] = None
    body_text: str = ""
    word_count: int = 0


class ExtractedTechSignal(BaseModel):
    """Technology signal extracted from page content."""

    technology: str
    category: Optional[str] = None
    evidence: str = ""
    confidence: float = 0.5


class ExtractedSignal(BaseModel):
    """A signal extracted from content by the LLM."""

    signal_type: str
    summary: str
    evidence: Optional[str] = None
    confidence: float = 0.5
    typed_data: Optional[dict] = None


class ExtractionResult(BaseModel):
    """Full extraction result from the LLM extraction pipeline.

    This is the structured output of processing a single piece of raw content.
    """

    page_classification: PageClassification = Field(default_factory=PageClassification)
    content: ExtractedContent = Field(default_factory=ExtractedContent)
    tech_signals: list[ExtractedTechSignal] = Field(default_factory=list)
    signals: list[ExtractedSignal] = Field(default_factory=list)
    entities_mentioned: list[str] = Field(default_factory=list)
    extraction_notes: str = ""


# ─── Signal Type Mapping ─────────────────────────────────────────────────────

# Maps extraction signal types to Phase 0 scoring signal types.
# The scoring engine uses the Phase 0 types; extraction produces
# more granular types that need mapping.
EXTRACTION_TO_SCORING_TYPE: dict[str, str] = {
    "funding_round": "funding_round",
    "revenue_milestone": "earnings_mention",
    "job_posting": "job_posting_technical",
    "job_posting_finance": "job_posting_finance",
    "job_posting_urgent": "job_posting_urgent",
    "key_hire": "new_executive_other",
    "key_hire_finance": "new_executive_finance",
    "tech_detected": "tech_stack_change",
    "tech_migration": "migration_signal",
    "leadership_change": "new_executive_other",
    "leadership_change_finance": "new_executive_finance",
    "competitor_mention": "competitor_evaluation",
    "competitor_evaluation": "competitor_evaluation",
    "content_removed": "press_release_relevant",
    "partner_announced": "press_release_relevant",
    "acquisition": "press_release_relevant",
    "pricing_change": "press_release_relevant",
    "blog_post_pain": "blog_post_pain",
    "linkedin_post_pain": "linkedin_post_pain",
}


def map_signal_type(extraction_type: str) -> str:
    """Map extraction signal type to scoring signal type."""
    return EXTRACTION_TO_SCORING_TYPE.get(extraction_type, extraction_type)
