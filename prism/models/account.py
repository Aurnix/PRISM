"""Account and company data models."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class Firmographics(BaseModel):
    """Company firmographic data."""

    founded_year: Optional[int] = None
    headcount: Optional[int] = None
    headcount_growth_12mo: Optional[float] = None
    funding_stage: Optional[str] = None
    total_raised: Optional[int] = None
    last_round_amount: Optional[int] = None
    last_round_date: Optional[date] = None
    last_round_lead: Optional[str] = None
    industry: Optional[str] = None
    hq_location: Optional[str] = None
    description: Optional[str] = None


class TechStack(BaseModel):
    """Company technology stack."""

    erp_accounting: Optional[str] = None
    crm: Optional[str] = None
    payment_processor: Optional[str] = None
    cloud_provider: Optional[str] = None
    primary_languages: list[str] = Field(default_factory=list)
    stack_maturity: Optional[str] = None  # "early" | "growing" | "mature" | "legacy"
    migration_signals: list[str] = Field(default_factory=list)


class Account(BaseModel):
    """Full account record for analysis."""

    slug: str
    company_name: str
    domain: str
    blog_url: Optional[str] = None
    blog_rss: Optional[str] = None
    firmographics: Firmographics = Field(default_factory=Firmographics)
    tech_stack: TechStack = Field(default_factory=TechStack)


class DiscoveredAccount(BaseModel):
    """Raw account from discovery, pre-enrichment."""

    company_name: str
    domain: str
    crunchbase_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    headcount_estimate: Optional[int] = None
    funding_stage: Optional[str] = None
    total_raised: Optional[int] = None
    last_funding_date: Optional[date] = None
    industry: Optional[str] = None
    hq_location: Optional[str] = None
    source: str
    discovery_date: date
    icp_filter_version: str = "v1"
    initial_boost_signals: list[str] = Field(default_factory=list)
    status: str = "discovered"
