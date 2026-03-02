"""Pydantic schemas for API request/response models."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class AccountCreate(BaseModel):
    """Request body for creating an account."""

    slug: str
    company_name: str
    domain: str
    blog_url: Optional[str] = None
    blog_rss: Optional[str] = None
    firmographics: dict = Field(default_factory=dict)
    tech_stack: dict = Field(default_factory=dict)


class AccountUpdate(BaseModel):
    """Request body for updating an account."""

    company_name: Optional[str] = None
    domain: Optional[str] = None
    blog_url: Optional[str] = None
    blog_rss: Optional[str] = None
    firmographics: Optional[dict] = None
    tech_stack: Optional[dict] = None
    status: Optional[str] = None


class AccountResponse(BaseModel):
    """Response model for an account."""

    slug: str
    company_name: str
    domain: str
    blog_url: Optional[str] = None
    blog_rss: Optional[str] = None
    firmographics: dict = Field(default_factory=dict)
    tech_stack: dict = Field(default_factory=dict)
    latest_scores: Optional[dict] = None
    latest_tier: Optional[str] = None


class AccountListItem(BaseModel):
    """Lightweight account info for list endpoints."""

    slug: str
    company_name: str
    domain: str
    industry: Optional[str] = None
    funding_stage: Optional[str] = None
    headcount: Optional[int] = None
    latest_tier: Optional[str] = None
    composite_score: Optional[float] = None


class SignalResponse(BaseModel):
    """Response model for a signal."""

    signal_type: str
    description: str
    source: str
    detected_date: date
    confidence: str = "extracted"
    decay_weight: float = 0.0


class ContentUpload(BaseModel):
    """Request body for uploading content."""

    source_type: str
    title: Optional[str] = None
    author: Optional[str] = None
    publish_date: date
    raw_text: str
    url: Optional[str] = None


class AnalyzeRequest(BaseModel):
    """Request body for triggering analysis."""

    skip_scraping: bool = False


class AnalyzeResponse(BaseModel):
    """Response after triggering analysis."""

    status: str
    message: str
    account_slug: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    database: str


class DossierResponse(BaseModel):
    """Response model for a dossier."""

    dossier_id: Optional[str] = None
    account_slug: str
    markdown_content: str
    created_at: Optional[str] = None
