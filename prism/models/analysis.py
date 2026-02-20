"""Analysis output data models."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from prism.models.signal import Signal


class Stage1Extraction(BaseModel):
    """Per-item content extraction output (Stage 1)."""

    content_title: Optional[str] = None
    source_type: str = ""
    publish_date: Optional[date] = None

    semantic: dict = Field(default_factory=lambda: {
        "announcements": [],
        "metrics": [],
        "claims": [],
    })
    pragmatic: dict = Field(default_factory=lambda: {
        "likely_motivation": "",
        "target_audience": "",
        "reactive_or_proactive": "",
    })
    tonal: dict = Field(default_factory=lambda: {
        "overall_tone": "",
        "certainty_level": "",
        "emotional_register": "",
    })
    structural: dict = Field(default_factory=lambda: {
        "emphasized_topics": [],
        "minimized_topics": [],
        "notable_absences": [],
    })
    raw_signals: list[str] = Field(default_factory=list)


class Stage2Synthesis(BaseModel):
    """Cross-corpus synthesis output (Stage 2)."""

    trajectory: dict = Field(default_factory=lambda: {
        "direction": "stable",
        "confidence_trend": "stable",
        "urgency_trend": "stable",
        "key_shifts": [],
    })
    absences: list[dict] = Field(default_factory=list)
    pain_coherence: dict = Field(default_factory=lambda: {
        "score": 0.0,
        "primary_pain_themes": [],
        "scattered_complaints": [],
    })
    stress_indicators: dict = Field(default_factory=lambda: {
        "level": "low",
        "evidence": [],
    })
    priority_alignment: dict = Field(default_factory=lambda: {
        "aligned": True,
        "stated": [],
        "actual": [],
        "gaps": [],
    })
    solution_sophistication: dict = Field(default_factory=lambda: {
        "level": "unaware",
        "evidence": "",
    })
    meta_signals: list[str] = Field(default_factory=list)


class PersonAnalysis(BaseModel):
    """Per-person analysis output (Stage 3)."""

    contact_name: str
    contact_title: str
    pain_alignment: dict = Field(default_factory=lambda: {
        "ahead_of_org": False,
        "aligned": False,
        "personal_pain_themes": [],
    })
    buying_readiness: dict = Field(default_factory=lambda: {
        "stage": "unaware",
        "confidence": 0.0,
        "evidence": [],
    })
    messaging_resonance: dict = Field(default_factory=lambda: {
        "primary": "pragmatist",
        "secondary": "",
        "avoid": "",
    })
    influence_level: dict = Field(default_factory=lambda: {
        "inferred_role": "unknown",
        "authority_signals": [],
        "confidence": 0.0,
    })
    recommended_approach: str = ""
    recommended_avoid: str = ""


class ContentIntelligenceSummary(BaseModel):
    """Summary of proprietary content analysis."""

    pain_coherence_score: float = 0.0
    primary_pain_themes: list[str] = Field(default_factory=list)
    org_stress_level: str = "low"  # low | moderate | elevated | high
    solution_sophistication: str = "unaware"
    stated_vs_actual_alignment: bool = True
    trajectory_direction: str = "stable"
    notable_absences: list[str] = Field(default_factory=list)


class WhyNowHypothesis(BaseModel):
    """Synthesized narrative of why this account is ready to buy NOW."""

    headline: str = ""
    supporting_signals: list[Signal] = Field(default_factory=list)
    trigger_event: Optional[str] = None
    trigger_date: Optional[date] = None
    window_estimate: str = "90 days"
    narrative: str = ""


class ConfidenceAssessment(BaseModel):
    """Honest assessment of signal quality."""

    overall_confidence: str = "low"  # high | medium | low
    extracted_signals: list[str] = Field(default_factory=list)
    interpolated_signals: list[str] = Field(default_factory=list)
    generated_signals: list[str] = Field(default_factory=list)
    counter_signals: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    corpus_size: int = 0
    corpus_quality: str = "low"  # high | medium | low
    corpus_sufficient: bool = False


class ScoreBreakdown(BaseModel):
    """Detailed score breakdown with component values."""

    icp_fit_score: float = 0.0
    icp_components: dict[str, float] = Field(default_factory=dict)
    buying_readiness_score: float = 0.0
    readiness_components: dict[str, float] = Field(default_factory=dict)
    timing_score: float = 0.0
    timing_components: dict[str, float] = Field(default_factory=dict)
    composite_score: float = 0.0
    priority_tier: str = "not_qualified"


class AnalyzedAccount(BaseModel):
    """Complete analysis output for a single account."""

    account_slug: str
    company_name: str
    domain: str
    analysis_date: date
    prompt_version: str = "v1"

    # Scores
    scores: ScoreBreakdown = Field(default_factory=ScoreBreakdown)

    # Buying journey
    journey_position: float = 0.0
    journey_position_label: str = "status_quo"
    journey_velocity: str = "stable"

    # Why now
    why_now: WhyNowHypothesis = Field(default_factory=WhyNowHypothesis)

    # Content Intelligence
    content_intelligence: Optional[ContentIntelligenceSummary] = None
    stage2_synthesis: Optional[Stage2Synthesis] = None

    # Person-level analyses
    person_analyses: list[PersonAnalysis] = Field(default_factory=list)

    # Confidence
    confidence: ConfidenceAssessment = Field(default_factory=ConfidenceAssessment)

    # Signals (with decay weights)
    signals: list[Signal] = Field(default_factory=list)

    # Token usage
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_api_calls: int = 0
    estimated_cost_usd: float = 0.0

    # Flags
    limited_analysis: bool = False
    limited_analysis_reason: Optional[str] = None
