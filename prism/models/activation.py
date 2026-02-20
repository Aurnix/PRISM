"""Activation output data models — plays, angles, account briefs."""

from typing import Optional

from pydantic import BaseModel, Field


class Angle(BaseModel):
    """Personalized outreach angle for a specific contact."""

    contact_name: str
    contact_title: str
    opening_angle: str = ""
    value_prop: str = ""
    call_to_action: str = ""
    avoid_topics: list[str] = Field(default_factory=list)
    likely_objection: str = ""
    objection_response: str = ""
    confidence: str = "medium"  # high | medium | low
    notes_for_ae: str = ""


class Play(BaseModel):
    """Recommended sales play for an account."""

    play_name: str = ""
    description: str = ""
    sequence: list[str] = Field(default_factory=list)
    timeline: str = ""
    entry_point: Optional[str] = None
    fallback_play: Optional[str] = None
    angles: list[Angle] = Field(default_factory=list)


class AccountBrief(BaseModel):
    """The full brief an AE reads before engaging."""

    company_name: str
    priority_tier: str
    composite_score: float
    one_line_why_now: str = ""
    company_summary: str = ""
    why_now_narrative: str = ""
    signal_confidence: str = "low"
    counter_signals: list[str] = Field(default_factory=list)
    recommended_entry_point: str = ""
    competitive_situation: str = "unknown"
    play: Play = Field(default_factory=Play)
    discovery_questions: list[str] = Field(default_factory=list)
    collection_gaps: list[str] = Field(default_factory=list)
