"""Contact and buying committee data models."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class LinkedInPost(BaseModel):
    """A single LinkedIn post from a contact."""

    date: date
    text: str


class ContactRecord(BaseModel):
    """Individual contact within a target account."""

    name: str
    title: str
    linkedin_url: Optional[str] = None
    email: Optional[str] = None
    start_date_current_role: Optional[date] = None
    previous_company: Optional[str] = None
    previous_title: Optional[str] = None
    buying_role: str = "unknown"  # champion | economic_buyer | technical_gatekeeper | user | unknown
    buying_role_confidence: float = 0.5
    linkedin_posts: list[LinkedInPost] = Field(default_factory=list)


class BuyingCommittee(BaseModel):
    """Mapped buying committee for the account."""

    contacts: list[ContactRecord] = Field(default_factory=list)
    likely_champion: Optional[str] = None
    champion_confidence: float = 0.0
    likely_economic_buyer: Optional[str] = None
    economic_buyer_confidence: float = 0.0
    likely_technical_gatekeeper: Optional[str] = None
    champion_ahead_of_org: bool = False
    new_leader_in_seat: bool = False
    committee_alignment: str = "unknown"  # aligned | mixed_signals | unknown
    gaps: list[str] = Field(default_factory=list)
