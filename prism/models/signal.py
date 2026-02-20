"""Signal data models."""

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class SignalType(str, Enum):
    """Known signal types with decay configurations."""

    FUNDING_ROUND = "funding_round"
    NEW_EXECUTIVE_FINANCE = "new_executive_finance"
    NEW_EXECUTIVE_OTHER = "new_executive_other"
    CHAMPION_DEPARTED = "champion_departed"
    JOB_POSTING_FINANCE = "job_posting_finance"
    JOB_POSTING_TECHNICAL = "job_posting_technical"
    JOB_POSTING_URGENT = "job_posting_urgent"
    TECH_STACK_CHANGE = "tech_stack_change"
    MIGRATION_SIGNAL = "migration_signal"
    BLOG_POST_PAIN = "blog_post_pain"
    LINKEDIN_POST_PAIN = "linkedin_post_pain"
    EARNINGS_MENTION = "earnings_mention"
    PRESS_RELEASE_RELEVANT = "press_release_relevant"
    PRICING_PAGE_VISIT = "pricing_page_visit"
    CONTENT_ENGAGEMENT = "content_engagement"
    G2_RESEARCH_ACTIVITY = "g2_research_activity"
    COMPETITOR_EVALUATION = "competitor_evaluation"
    COMPETITOR_CONTRACT_RENEWAL = "competitor_contract_renewal"
    GLASSDOOR_TREND = "glassdoor_trend"


class Signal(BaseModel):
    """A detected signal for an account."""

    signal_type: str
    description: str
    source: str
    detected_date: date
    decay_weight: float = 0.0
    confidence: str = "interpolated"  # extracted | interpolated | generated
    contact_name: Optional[str] = None
