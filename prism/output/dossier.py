"""Dossier renderer — generates the markdown intelligence brief.

The dossier is the primary deliverable. It follows an intelligence
brief format with ASCII box-drawing characters for structure.
"""

import logging
from datetime import date, datetime
from typing import Optional

from prism.models.account import Account
from prism.models.analysis import (
    AnalyzedAccount,
    ConfidenceAssessment,
    ContentIntelligenceSummary,
    PersonAnalysis,
    ScoreBreakdown,
    Stage2Synthesis,
    WhyNowHypothesis,
)
from prism.models.activation import AccountBrief, Angle, Play
from prism.models.contact import ContactRecord
from prism.models.signal import Signal

logger = logging.getLogger(__name__)


def render_dossier(
    account: Account,
    analyzed: AnalyzedAccount,
    contacts: list[ContactRecord],
    play: Optional[Play] = None,
    brief: Optional[AccountBrief] = None,
    dossier_number: int = 1,
) -> str:
    """Render a full intelligence dossier as markdown.

    Args:
        account: Source account data.
        analyzed: Complete analysis output.
        contacts: Known contacts.
        play: Recommended play.
        brief: Account brief.
        dossier_number: Sequential dossier number.

    Returns:
        Complete dossier as markdown string.
    """
    scores = analyzed.scores
    now = datetime.now()
    year = now.year
    dossier_id = f"PRISM-{year}-{dossier_number:04d}"

    tier_labels = {
        "tier_1": "TIER 1 — IMMEDIATE ACTION",
        "tier_2": "TIER 2 — ACTIVE OUTREACH",
        "tier_3": "TIER 3 — MONITOR & NURTURE",
        "not_qualified": "NOT QUALIFIED",
    }
    tier_label = tier_labels.get(scores.priority_tier, "UNCLASSIFIED")

    confidence_label = analyzed.confidence.overall_confidence.upper()

    sections = []

    # ─── Header ────────────────────────────────────────────────────────────

    sections.append(f"""\
═══════════════════════════════════════════════════════════════════
                    P R I S M
        Predictive Revenue Intelligence & Signal Mapping
═══════════════════════════════════════════════════════════════════

ACCOUNT DOSSIER: {account.company_name.upper()}
Classification: {tier_label}
Dossier ID: {dossier_id}
Generated: {now.isoformat(timespec='seconds')}
Analyst Confidence: {confidence_label}
Prompt Chain Version: {analyzed.prompt_version}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""")

    # ─── Section 1: Executive Summary ──────────────────────────────────────

    composite_pct = f"{scores.composite_score:.0%}"
    icp_pct = f"{scores.icp_fit_score:.0%}"
    readiness_pct = f"{scores.buying_readiness_score:.0%}"
    timing_pct = f"{scores.timing_score:.0%}"

    why_now_headline = analyzed.why_now.headline or "Analysis pending"

    summary_text = f"""\

SECTION 1: EXECUTIVE SUMMARY
─────────────────────────────

{why_now_headline}

Composite Score: {composite_pct}
├── ICP Fit:          {icp_pct}  (weight: 25%)
├── Buying Readiness: {readiness_pct}  (weight: 50%)
└── Timing:           {timing_pct}  (weight: 25%)

Journey Position: {analyzed.journey_position_label.replace('_', ' ').title()} ({analyzed.journey_position:.2f})
Journey Velocity: {analyzed.journey_velocity.title()}"""

    if analyzed.limited_analysis:
        summary_text += f"\n\n⚠️  LIMITED ANALYSIS — {analyzed.limited_analysis_reason}"

    sections.append(summary_text)

    # ─── Section 2: Subject Profile ────────────────────────────────────────

    f = account.firmographics
    t = account.tech_stack

    migration_text = ""
    if t.migration_signals:
        migration_text = "\n  Migration Signals:\n" + "\n".join(
            f"    ► {sig}" for sig in t.migration_signals
        )

    sections.append(f"""\

SECTION 2: SUBJECT PROFILE
──────────────────────────

Company:     {account.company_name}
Domain:      {account.domain}
Industry:    {f.industry or 'Unknown'}
Founded:     {f.founded_year or 'Unknown'}
HQ:          {f.hq_location or 'Unknown'}

Headcount:   {f.headcount or 'Unknown'}
Growth:      {_fmt_pct(f.headcount_growth_12mo)} (12mo)

Funding:     {f.funding_stage or 'Unknown'}
Total Raised: {_fmt_money(f.total_raised)}
Last Round:  {_fmt_money(f.last_round_amount)} ({f.last_round_date or 'Unknown'})
Lead:        {f.last_round_lead or 'Unknown'}

Tech Stack:
  ERP/Accounting:  {t.erp_accounting or 'Unknown'}
  CRM:             {t.crm or 'Unknown'}
  Payments:        {t.payment_processor or 'Unknown'}
  Cloud:           {t.cloud_provider or 'Unknown'}
  Languages:       {', '.join(t.primary_languages) if t.primary_languages else 'Unknown'}
  Maturity:        {t.stack_maturity or 'Unknown'}{migration_text}

ICP Fit Breakdown:
{_render_score_tree(scores.icp_components, '  ')}""")

    # ─── Section 3: Organizational Intelligence ───────────────────────────

    ci = analyzed.content_intelligence
    s2 = analyzed.stage2_synthesis

    if ci:
        pain_themes_text = ", ".join(ci.primary_pain_themes) if ci.primary_pain_themes else "None identified"
        absences_text = ", ".join(ci.notable_absences) if ci.notable_absences else "None identified"

        org_intel_text = f"""\

SECTION 3: ORGANIZATIONAL INTELLIGENCE ASSESSMENT
─────────────────────────────────────────────────

Pain Coherence Score: {ci.pain_coherence_score:.2f} / 1.00
  Primary Themes: {pain_themes_text}

Organizational Stress: {ci.org_stress_level.upper()}
Solution Sophistication: {ci.solution_sophistication.title()}
Trajectory: {ci.trajectory_direction.title()}
Priority Alignment: {'Aligned' if ci.stated_vs_actual_alignment else 'MISALIGNED'}
Notable Absences: {absences_text}

Buying Readiness Breakdown:
{_render_score_tree(scores.readiness_components, '  ')}"""

        if s2 and s2.absences:
            org_intel_text += "\n\n  Absence Analysis:"
            for absence in s2.absences[:5]:
                topic = absence.get("expected_topic", "Unknown")
                reason = absence.get("likely_reason", "Unknown")
                conf = absence.get("confidence", 0.0)
                org_intel_text += f"\n    ◆ {topic}"
                org_intel_text += f"\n      Likely reason: {reason} [confidence: {conf:.0%}]"

        if s2 and s2.trajectory.get("key_shifts"):
            org_intel_text += "\n\n  Key Trajectory Shifts:"
            for shift in s2.trajectory["key_shifts"][:5]:
                org_intel_text += f"\n    ► [{shift.get('date_approx', '?')}] {shift.get('description', '')}"

    else:
        org_intel_text = """\

SECTION 3: ORGANIZATIONAL INTELLIGENCE ASSESSMENT
─────────────────────────────────────────────────

⚠️  Content Intelligence analysis unavailable.
Scoring based on firmographic and signal data only.

Buying Readiness Breakdown:
""" + _render_score_tree(scores.readiness_components, '  ')

    sections.append(org_intel_text)

    # ─── Section 4: Buying Committee ──────────────────────────────────────

    committee_text = """\

SECTION 4: KEY PERSONNEL — BUYING COMMITTEE MAP
────────────────────────────────────────────────"""

    if analyzed.person_analyses:
        for pa in analyzed.person_analyses:
            readiness_stage = pa.buying_readiness.get("stage", "unknown")
            resonance = pa.messaging_resonance.get("primary", "unknown")
            approach = pa.recommended_approach or "Not available"
            avoid = pa.recommended_avoid or "Not available"

            committee_text += f"""

  ┌─ {pa.contact_name}
  │  Title: {pa.contact_title}
  │  Buying Readiness: {readiness_stage.replace('_', ' ').title()}
  │  Messaging Resonance: {resonance.replace('_', ' ').title()}
  │  Pain Alignment: {'Ahead of org' if pa.pain_alignment.get('ahead_of_org') else 'Aligned' if pa.pain_alignment.get('aligned') else 'Behind org'}
  │
  │  ► Approach: {approach}
  │  ✗ Avoid: {avoid}
  └──────────────────────────────────"""

    # Add contacts without person-level analysis
    analyzed_names = {pa.contact_name for pa in analyzed.person_analyses}
    for contact in contacts:
        if contact.name not in analyzed_names:
            committee_text += f"""

  ┌─ {contact.name}
  │  Title: {contact.title}
  │  Buying Role: {contact.buying_role.replace('_', ' ').title()}
  │  ⚠️  Person-level analysis unavailable (no public content)
  └──────────────────────────────────"""

    if play and play.entry_point:
        committee_text += f"\n\n  ★ Recommended Entry Point: {play.entry_point}"

    sections.append(committee_text)

    # ─── Section 5: Signal Timeline ───────────────────────────────────────

    signal_text = """\

SECTION 5: SIGNAL TIMELINE
──────────────────────────"""

    sorted_signals = sorted(
        analyzed.signals,
        key=lambda s: s.detected_date,
        reverse=True,
    )

    for signal in sorted_signals:
        bar = _decay_bar(signal.decay_weight)
        confidence_tag = f"[{signal.confidence.upper()}]"
        signal_text += (
            f"\n  [{signal.detected_date}] {bar} {signal.decay_weight:.2f}  "
            f"{signal.signal_type.replace('_', ' ').title()}"
            f"\n    {signal.description}"
            f"\n    Source: {signal.source}  {confidence_tag}"
        )

    if not sorted_signals:
        signal_text += "\n  No signals detected."

    signal_text += f"""

Timing Score Breakdown:
{_render_score_tree(scores.timing_components, '  ')}"""

    sections.append(signal_text)

    # ─── Section 6: Why Now ───────────────────────────────────────────────

    why_now = analyzed.why_now
    counter = analyzed.confidence.counter_signals

    why_now_text = f"""\

SECTION 6: WHY NOW — HYPOTHESIS
───────────────────────────────

{why_now.headline or 'No hypothesis generated.'}

{why_now.narrative or 'Narrative unavailable — insufficient data for hypothesis generation.'}"""

    if why_now.trigger_event:
        why_now_text += f"\n\nTrigger Event: {why_now.trigger_event}"
    if why_now.trigger_date:
        why_now_text += f" ({why_now.trigger_date})"
    if why_now.window_estimate:
        why_now_text += f"\nEstimated Window: {why_now.window_estimate}"

    why_now_text += "\n\nCounter-Signals:"
    if counter:
        for cs in counter:
            why_now_text += f"\n  ⚠️  {cs}"
    else:
        why_now_text += "\n  ⚠️  No significant counter-signals detected."
        why_now_text += "\n      NOTE: Absence of counter-signals is unusual and may indicate analysis gaps."

    sections.append(why_now_text)

    # ─── Section 7: Recommended Play ──────────────────────────────────────

    if play:
        play_text = f"""\

SECTION 7: RECOMMENDED PLAY
────────────────────────────

Play: {play.play_name.replace('_', ' ').title()}
{play.description}

Timeline: {play.timeline}
Entry Point: {play.entry_point or 'Not specified'}
Fallback: {play.fallback_play or 'Standard nurture sequence'}

Sequence:"""
        for i, step in enumerate(play.sequence, 1):
            play_text += f"\n  {i}. {step.replace('_', ' ').title()}"

        if play.angles:
            play_text += "\n\nPer-Contact Angles:"
            for angle in play.angles:
                play_text += f"""

  ┌─ {angle.contact_name} ({angle.contact_title})
  │  Hook: {angle.opening_angle}
  │  Value: {angle.value_prop}
  │  Ask: {angle.call_to_action}
  │  Avoid: {', '.join(angle.avoid_topics) if angle.avoid_topics else 'None specified'}
  │  Objection: {angle.likely_objection}
  │  Handle: {angle.objection_response}
  └──────────────────────────────────"""

    else:
        play_text = """\

SECTION 7: RECOMMENDED PLAY
────────────────────────────

No play recommendation generated — insufficient analysis data."""

    sections.append(play_text)

    # ─── Section 8: Collection Gaps ───────────────────────────────────────

    conf = analyzed.confidence
    discovery_qs = brief.discovery_questions if brief else []
    gaps = brief.collection_gaps if brief else conf.unknowns

    gaps_text = """\

SECTION 8: COLLECTION GAPS & DISCOVERY QUESTIONS
─────────────────────────────────────────────────

Discovery Questions (for first conversation):"""

    if discovery_qs:
        for i, q in enumerate(discovery_qs, 1):
            gaps_text += f"\n  {i}. {q}"
    else:
        gaps_text += "\n  1. What is your current month-end close timeline?"
        gaps_text += "\n  2. What tools are you using for financial reporting today?"
        gaps_text += "\n  3. What's driving the urgency to evaluate new solutions now?"

    gaps_text += "\n\nEnrichment Gaps:"
    if gaps:
        for gap in gaps:
            gaps_text += f"\n  ☐ {gap}"
    else:
        gaps_text += "\n  ☐ No specific enrichment gaps identified."

    sections.append(gaps_text)

    # ─── Section 9: Appendix ─────────────────────────────────────────────

    appendix_text = """\

SECTION 9: APPENDIX — RAW SIGNALS & SOURCES
───────────────────────────────────────────"""

    appendix_text += f"""

Analysis Metadata:
  Total API Calls: {analyzed.total_api_calls}
  Input Tokens: {analyzed.total_input_tokens:,}
  Output Tokens: {analyzed.total_output_tokens:,}
  Estimated Cost: ${analyzed.estimated_cost_usd:.4f}
  Prompt Version: {analyzed.prompt_version}

Confidence Assessment:
  Overall: {conf.overall_confidence.upper()}
  Corpus Size: {conf.corpus_size} items
  Corpus Quality: {conf.corpus_quality.upper()}
  Corpus Sufficient: {'Yes' if conf.corpus_sufficient else 'No'}"""

    if conf.extracted_signals:
        appendix_text += "\n\n  Extracted Signals (multi-source corroborated):"
        for s in conf.extracted_signals:
            appendix_text += f"\n    [EXTRACTED] {s}"

    if conf.interpolated_signals:
        appendix_text += "\n\n  Interpolated Signals (pattern-consistent, single-source):"
        for s in conf.interpolated_signals:
            appendix_text += f"\n    [INTERPOLATED] {s}"

    if conf.generated_signals:
        appendix_text += "\n\n  Generated Signals (plausible but unverified):"
        for s in conf.generated_signals:
            appendix_text += f"\n    [GENERATED] {s}"

    sections.append(appendix_text)

    # ─── Footer ──────────────────────────────────────────────────────────

    sections.append(f"""
═══════════════════════════════════════════════════════════════════
END DOSSIER | {dossier_id} | Generated by PRISM v0.1
═══════════════════════════════════════════════════════════════════""")

    return "\n".join(sections)


# ─── Helpers ────────────────────────────────────────────────────────────────


def _fmt_money(amount: Optional[int]) -> str:
    """Format money amount."""
    if amount is None:
        return "Unknown"
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    if amount >= 1_000:
        return f"${amount / 1_000:.0f}K"
    return f"${amount:,}"


def _fmt_pct(value: Optional[float]) -> str:
    """Format percentage."""
    if value is None:
        return "Unknown"
    return f"{value:.0%}"


def _decay_bar(weight: float, width: int = 10) -> str:
    """Render a decay weight as a block character bar."""
    if weight <= 0:
        return "░" * width
    filled = int(weight * width)
    chars = ""
    for i in range(width):
        if i < filled:
            if weight > 0.7:
                chars += "█"
            elif weight > 0.4:
                chars += "▓"
            else:
                chars += "▒"
        else:
            chars += "░"
    return chars


def _render_score_tree(components: dict[str, float], indent: str = "") -> str:
    """Render score components as a tree structure."""
    if not components:
        return f"{indent}No components available."

    items = list(components.items())
    lines = []
    for i, (key, value) in enumerate(items):
        prefix = "└──" if i == len(items) - 1 else "├──"
        bar = _decay_bar(value, 8)
        label = key.replace("_", " ").title()
        lines.append(f"{indent}{prefix} {label}: {value:.2f}  {bar}")
    return "\n".join(lines)
