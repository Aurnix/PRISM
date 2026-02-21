"""Scoring engine — ICP fit, buying readiness, timing, and composite scoring.

All scoring logic reads weights from config.py. Component scores are
calculated from account data and content intelligence outputs.
"""

import logging
from datetime import date
from typing import Optional

from prism.config import (
    COMPOSITE_WEIGHTS,
    FUNDING_STAGE_SCORES,
    ICP_WEIGHTS,
    INDUSTRY_SCORES,
    MAJOR_TECH_HUBS,
    READINESS_WEIGHTS,
    TIER_THRESHOLDS,
    TIMING_WEIGHTS,
)
from prism.models.account import Account
from prism.models.analysis import ScoreBreakdown, Stage2Synthesis
from prism.models.contact import ContactRecord
from prism.models.signal import Signal
from prism.analysis.signal_decay import calculate_decay_weight, calculate_signal_freshness_avg

logger = logging.getLogger(__name__)


# ─── ICP Fit Component Scoring ──────────────────────────────────────────────


def score_funding_stage(funding_stage: Optional[str], total_raised: Optional[int] = None) -> float:
    """Score funding stage fit.

    Series A with >$5M gets 0.70; Seed with >$2M gets 0.30.
    """
    if not funding_stage:
        return 0.50  # Unknown

    # Exact match first
    if funding_stage in FUNDING_STAGE_SCORES:
        score = FUNDING_STAGE_SCORES[funding_stage]
        # Adjust Series A based on total raised
        if funding_stage == "Series A" and total_raised is not None:
            if total_raised < 5_000_000:
                score = 0.40
        if funding_stage == "Seed" and total_raised is not None:
            if total_raised < 2_000_000:
                score = 0.15
        return score

    # Fuzzy matching for common variants
    stage_lower = funding_stage.lower()
    for key, val in FUNDING_STAGE_SCORES.items():
        if key.lower() in stage_lower:
            return val

    return 0.50


def score_growth_rate(growth_rate: Optional[float]) -> float:
    """Score headcount growth rate (YoY as decimal, e.g., 0.34 = 34%)."""
    if growth_rate is None:
        return 0.50

    if growth_rate > 0.50:
        return 1.0
    elif growth_rate > 0.30:
        return 0.85
    elif growth_rate > 0.15:
        return 0.60
    elif growth_rate > 0.05:
        return 0.35
    else:
        return 0.10


def score_tech_stack(
    erp_accounting: Optional[str],
    headcount: Optional[int],
    migration_signals: Optional[list[str]] = None,
) -> float:
    """Score tech stack fit based on current accounting tool and headcount."""
    score = 0.50  # Default for unknown

    erp = (erp_accounting or "").lower()
    hc = headcount or 0

    if any(tool in erp for tool in ["quickbooks", "qbo", "xero"]):
        if hc > 100:
            score = 1.0
        elif hc > 50:
            score = 0.85
        else:
            score = 0.65
    elif "spreadsheet" in erp or "manual" in erp or "excel" in erp:
        score = 0.90
    elif "netsuite" in erp:
        # Check for migration signals suggesting dissatisfaction
        if migration_signals:
            score = 0.70
        else:
            score = 0.30
    elif any(tool in erp for tool in ["sap", "oracle"]):
        score = 0.10
    elif erp == "" or erp == "unknown":
        score = 0.50

    # Migration signal boost
    if migration_signals and len(migration_signals) > 0:
        score = min(1.0, score + 0.20)

    return score


def score_headcount(headcount: Optional[int]) -> float:
    """Score headcount fit."""
    if headcount is None:
        return 0.50

    if 100 <= headcount <= 300:
        return 1.0
    elif 50 <= headcount < 100:
        return 0.85
    elif 300 < headcount <= 500:
        return 0.75
    elif 30 <= headcount < 50:
        return 0.40
    elif 500 < headcount <= 1000:
        return 0.35
    elif headcount < 30:
        return 0.10
    else:  # > 1000
        return 0.15


def score_industry(industry: Optional[str]) -> float:
    """Score industry fit."""
    if not industry:
        return 0.50

    # Exact match first
    if industry in INDUSTRY_SCORES:
        return INDUSTRY_SCORES[industry]

    # Fuzzy matching
    industry_lower = industry.lower()
    for key, val in INDUSTRY_SCORES.items():
        if key.lower() in industry_lower or industry_lower in key.lower():
            return val

    # Check broad categories
    if any(t in industry_lower for t in ["software", "tech", "digital", "ai", "ml", "data"]):
        return 0.60
    return 0.30


def score_geo(hq_location: Optional[str]) -> float:
    """Score geographic fit."""
    if not hq_location:
        return 0.50

    loc_upper = hq_location.upper()

    # Check for major tech hubs
    for hub in MAJOR_TECH_HUBS:
        if hub.upper() in loc_upper:
            return 1.0

    # US locations
    if any(
        indicator in loc_upper
        for indicator in [", CA", ", NY", ", TX", ", WA", ", MA", ", CO", ", IL", ", FL", "USA", "UNITED STATES"]
    ):
        return 0.90

    # Canada
    if any(indicator in loc_upper for indicator in ["CANADA", ", ON", ", BC", ", QC", "TORONTO", "VANCOUVER"]):
        return 0.80

    # UK/Western Europe
    if any(
        indicator in loc_upper
        for indicator in ["UK", "UNITED KINGDOM", "LONDON", "GERMANY", "FRANCE", "NETHERLANDS", "IRELAND"]
    ):
        return 0.60

    # Other English-speaking
    if any(indicator in loc_upper for indicator in ["AUSTRALIA", "NEW ZEALAND", "SINGAPORE"]):
        return 0.50

    return 0.30


def calculate_icp_fit(account: Account) -> tuple[float, dict[str, float]]:
    """Calculate the composite ICP fit score.

    Returns:
        Tuple of (composite score, component scores dict).
    """
    f = account.firmographics
    t = account.tech_stack

    components = {
        "funding_stage_fit": score_funding_stage(f.funding_stage, f.total_raised),
        "growth_rate": score_growth_rate(f.headcount_growth_12mo),
        "tech_stack_fit": score_tech_stack(
            t.erp_accounting, f.headcount, t.migration_signals
        ),
        "headcount_fit": score_headcount(f.headcount),
        "industry_fit": score_industry(f.industry),
        "geo_fit": score_geo(f.hq_location),
    }

    composite = sum(
        components[key] * ICP_WEIGHTS[key]
        for key in ICP_WEIGHTS
    )

    return composite, components


# ─── Buying Readiness Component Scoring ─────────────────────────────────────


def score_new_leader(contacts: list[ContactRecord], current_date: date) -> float:
    """Score new leader signal based on contacts' tenure."""
    best_score = 0.0

    for contact in contacts:
        if contact.buying_role not in ("champion", "economic_buyer"):
            continue
        if not contact.start_date_current_role:
            continue

        days_in_role = (current_date - contact.start_date_current_role).days

        if 30 <= days_in_role <= 120:
            score = 1.0 if "finance" in contact.title.lower() or "controller" in contact.title.lower() else 0.95
        elif days_in_role < 30:
            score = 0.60
        elif 120 < days_in_role <= 180:
            score = 0.70
        elif 180 < days_in_role <= 365:
            score = 0.35
        else:
            score = 0.0

        best_score = max(best_score, score)

    return best_score


def score_active_evaluation(signals: list[Signal]) -> float:
    """Score active evaluation signals."""
    eval_signal_types = {
        "competitor_evaluation", "g2_research_activity",
        "pricing_page_visit", "content_engagement",
    }

    eval_signals = [s for s in signals if s.signal_type in eval_signal_types]

    if len(eval_signals) >= 2:
        return 1.0
    elif len(eval_signals) == 1:
        if eval_signals[0].signal_type == "competitor_evaluation":
            return 0.75
        return 0.45
    return 0.0


def calculate_buying_readiness(
    synthesis: Optional[Stage2Synthesis],
    contacts: list[ContactRecord],
    signals: list[Signal],
    current_date: date,
) -> tuple[float, dict[str, float]]:
    """Calculate buying readiness score.

    Components from Content Intelligence are passed through from
    the Stage 2 synthesis output. New leader signal and active
    evaluation are computed from structured data.

    Returns:
        Tuple of (composite score, component scores dict).
    """
    if synthesis:
        journey_raw = synthesis.pain_coherence.get("score", 0.0)
        # Map journey position to score
        if journey_raw >= 0.60:
            journey_score = 1.0
        elif journey_raw >= 0.40:
            journey_score = 0.80
        elif journey_raw >= 0.25:
            journey_score = 0.55
        elif journey_raw >= 0.15:
            journey_score = 0.30
        else:
            journey_score = 0.10

        pain_coherence_score = synthesis.pain_coherence.get("score", 0.0)

        stress_level = synthesis.stress_indicators.get("level", "low")
        stress_map = {"high": 1.0, "elevated": 0.70, "moderate": 0.40, "low": 0.10}
        stress_score = stress_map.get(stress_level, 0.10)

        sophistication = synthesis.solution_sophistication.get("level", "unaware")
        soph_map = {"decided": 1.0, "evaluating": 0.85, "articulate": 0.65, "frustrated": 0.30, "unaware": 0.05}
        soph_score = soph_map.get(sophistication, 0.05)
    else:
        journey_score = 0.10
        pain_coherence_score = 0.0
        stress_score = 0.10
        soph_score = 0.05

    components = {
        "journey_position": journey_score,
        "pain_coherence": pain_coherence_score,
        "new_leader_signal": score_new_leader(contacts, current_date),
        "org_stress_indicators": stress_score,
        "solution_sophistication": soph_score,
        "active_evaluation_signals": score_active_evaluation(signals),
    }

    composite = sum(
        components[key] * READINESS_WEIGHTS[key]
        for key in READINESS_WEIGHTS
    )

    return composite, components


# ─── Timing Component Scoring ───────────────────────────────────────────────


def calculate_timing(
    signals: list[Signal],
    urgency_score: float = 0.10,
    window_closing_score: float = 1.0,
    current_date: date = date.today(),
) -> tuple[float, dict[str, float]]:
    """Calculate timing score.

    Args:
        signals: Account signals with decay weights pre-calculated.
        urgency_score: From Content Intelligence (0.0-1.0).
        window_closing_score: Inverted — 1.0 = window open, 0.0 = closing.
        current_date: Reference date.

    Returns:
        Tuple of (composite score, component scores dict).
    """
    # Trigger event recency — best signal decay weight
    trigger_types = {
        "funding_round", "new_executive_finance", "new_executive_other",
        "job_posting_finance", "tech_stack_change", "migration_signal",
        "earnings_mention", "competitor_contract_renewal",
    }
    trigger_weights = [
        s.decay_weight for s in signals
        if s.signal_type in trigger_types and s.decay_weight > 0
    ]
    trigger_recency = max(trigger_weights) if trigger_weights else 0.0

    # Signal freshness average
    all_weights = [s.decay_weight for s in signals if s.decay_weight > 0]
    freshness_avg = calculate_signal_freshness_avg(all_weights)

    components = {
        "trigger_event_recency": trigger_recency,
        "signal_freshness_avg": freshness_avg,
        "urgency_indicators": urgency_score,
        "window_closing_signals": window_closing_score,
    }

    composite = sum(
        components[key] * TIMING_WEIGHTS[key]
        for key in TIMING_WEIGHTS
    )

    return composite, components


# ─── Composite Scoring ──────────────────────────────────────────────────────


def calculate_composite(
    icp_fit: float,
    buying_readiness: float,
    timing: float,
) -> tuple[float, str]:
    """Calculate composite priority score and tier assignment.

    Returns:
        Tuple of (composite score, tier label).
    """
    composite = (
        icp_fit * COMPOSITE_WEIGHTS["icp_fit"]
        + buying_readiness * COMPOSITE_WEIGHTS["buying_readiness"]
        + timing * COMPOSITE_WEIGHTS["timing"]
    )

    if composite >= TIER_THRESHOLDS["tier_1"]:
        tier = "tier_1"
    elif composite >= TIER_THRESHOLDS["tier_2"]:
        tier = "tier_2"
    elif composite >= TIER_THRESHOLDS["tier_3"]:
        tier = "tier_3"
    else:
        tier = "not_qualified"

    return composite, tier


def score_account(
    account: Account,
    contacts: list[ContactRecord],
    signals: list[Signal],
    synthesis: Optional[Stage2Synthesis] = None,
    urgency_score: float = 0.10,
    window_closing_score: float = 1.0,
    current_date: Optional[date] = None,
) -> ScoreBreakdown:
    """Full scoring pipeline for an account.

    Calculates ICP fit, buying readiness, timing, and composite scores.

    Returns:
        Complete ScoreBreakdown with all components.
    """
    if current_date is None:
        current_date = date.today()

    # Calculate decay weights for all signals
    for signal in signals:
        signal.decay_weight = calculate_decay_weight(
            signal.signal_type, signal.detected_date, current_date
        )

    icp_score, icp_components = calculate_icp_fit(account)
    readiness_score, readiness_components = calculate_buying_readiness(
        synthesis, contacts, signals, current_date
    )
    timing_score, timing_components = calculate_timing(
        signals, urgency_score, window_closing_score, current_date
    )
    composite, tier = calculate_composite(icp_score, readiness_score, timing_score)

    return ScoreBreakdown(
        icp_fit_score=round(icp_score, 4),
        icp_components={k: round(v, 4) for k, v in icp_components.items()},
        buying_readiness_score=round(readiness_score, 4),
        readiness_components={k: round(v, 4) for k, v in readiness_components.items()},
        timing_score=round(timing_score, 4),
        timing_components={k: round(v, 4) for k, v in timing_components.items()},
        composite_score=round(composite, 4),
        priority_tier=tier,
    )
