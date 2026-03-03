"""Pydantic schemas for API request/response models."""

import re
from datetime import date, datetime
from typing import Annotated, Optional

from pydantic import BaseModel, Field, field_validator


# Slug must be alphanumeric with hyphens/underscores, 1-64 chars
_SLUG_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")

VALID_SOURCE_TYPES = {"blog", "linkedin", "job_posting", "press", "news", "earnings", "glassdoor"}
VALID_ACCOUNT_STATUSES = {"active", "archived", "inactive", "pending"}


class AccountCreate(BaseModel):
    """Request body for creating an account."""

    slug: str = Field(..., min_length=1, max_length=64)
    company_name: str = Field(..., min_length=1, max_length=255)
    domain: str = Field(..., min_length=1, max_length=255)
    blog_url: Optional[str] = None
    blog_rss: Optional[str] = None
    firmographics: dict = Field(default_factory=dict)
    tech_stack: dict = Field(default_factory=dict)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not _SLUG_RE.match(v):
            raise ValueError("Slug must be alphanumeric with hyphens/underscores, 1-64 chars")
        return v


class AccountUpdate(BaseModel):
    """Request body for updating an account."""

    company_name: Optional[str] = Field(None, max_length=255)
    domain: Optional[str] = Field(None, max_length=255)
    blog_url: Optional[str] = None
    blog_rss: Optional[str] = None
    firmographics: Optional[dict] = None
    tech_stack: Optional[dict] = None
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_ACCOUNT_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(sorted(VALID_ACCOUNT_STATUSES))}")
        return v


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
    title: Optional[str] = Field(None, max_length=500)
    author: Optional[str] = Field(None, max_length=255)
    publish_date: date
    raw_text: str = Field(..., max_length=1_000_000)
    url: Optional[str] = None

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        if v not in VALID_SOURCE_TYPES:
            raise ValueError(f"source_type must be one of: {', '.join(sorted(VALID_SOURCE_TYPES))}")
        return v


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
