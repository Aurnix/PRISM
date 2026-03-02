"""Shared analysis pipeline — used by both CLI and API.

Extracts the core orchestration logic from cli.py so that the same
pipeline can be invoked from the CLI, FastAPI endpoints, or background tasks.
"""

import logging
from datetime import date
from typing import Optional

from prism.analysis.content_intel import ContentIntelligenceChain
from prism.analysis.scoring import lookup_play_fallback, score_account
from prism.analysis.signal_decay import calculate_decay_weight
from prism.config import PRISM_PROMPT_VERSION
from prism.models.account import Account
from prism.models.activation import AccountBrief, Play
from prism.models.analysis import (
    AnalyzedAccount,
    ConfidenceAssessment,
    ContentIntelligenceSummary,
    WhyNowHypothesis,
)
from prism.models.contact import ContactRecord
from prism.models.content import ContentCorpus, ContentItem
from prism.models.signal import Signal
from prism.services.llm_backend import LLMBackend

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """Core analysis pipeline that orchestrates the full PRISM analysis.

    This class owns the analysis logic. CLI and API are thin wrappers
    that handle I/O (loading data, saving output) and call this pipeline.
    """

    def __init__(self, llm: LLMBackend) -> None:
        self.llm = llm
        self.chain = ContentIntelligenceChain(llm)

    async def analyze(
        self,
        account: Account,
        contacts: list[ContactRecord],
        signals: list[Signal],
        content_items: list[ContentItem],
        *,
        run_llm: bool = True,
        current_date: Optional[date] = None,
    ) -> tuple[AnalyzedAccount, Play, AccountBrief]:
        """Run the full analysis pipeline for a single account.

        Args:
            account: Account to analyze.
            contacts: Contact records.
            signals: Known signals.
            content_items: All content items (blog, LinkedIn, job posts, etc).
            run_llm: Whether to run LLM analysis.
            current_date: Reference date for decay calculations.

        Returns:
            Tuple of (AnalyzedAccount, Play, AccountBrief).
        """
        if current_date is None:
            current_date = date.today()

        # Build content corpus
        corpus = ContentCorpus(
            account_slug=account.slug,
            assembly_date=current_date,
            items=content_items,
        )
        corpus._update_metadata()

        # Calculate signal decay weights
        for signal in signals:
            signal.decay_weight = calculate_decay_weight(
                signal.signal_type, signal.detected_date, current_date
            )

        # Run Content Intelligence chain
        stage1_results = []
        stage2_result = None
        person_analyses = []
        stage4_result = None

        if run_llm and corpus.total_items > 0:
            stage1_results, stage2_result, person_analyses, stage4_result = (
                await self.chain.analyze(
                    account=account,
                    corpus=corpus,
                    contacts=contacts,
                    signals=signals,
                    current_date=current_date,
                )
            )

        # Extract stage 4 results
        urgency_score = 0.10
        window_closing_score = 1.0
        why_now_data: dict = {}
        confidence_data: dict = {}
        play_data: dict = {}
        discovery_questions: list = []
        collection_gaps: list = []

        if stage4_result:
            urgency_score = stage4_result.get("urgency_score", 0.10)
            window_closing_score = stage4_result.get("window_closing_score", 1.0)
            why_now_data = stage4_result.get("why_now", {})
            confidence_data = stage4_result.get("confidence", {})
            play_data = stage4_result.get("recommended_play", {})
            discovery_questions = stage4_result.get("discovery_questions", [])
            collection_gaps = stage4_result.get("collection_gaps", [])

        # Score the account
        scores = score_account(
            account=account,
            contacts=contacts,
            signals=signals,
            synthesis=stage2_result,
            urgency_score=urgency_score,
            window_closing_score=window_closing_score,
            current_date=current_date,
        )

        # Build content intelligence summary
        ci_summary = None
        if stage2_result:
            ci_summary = ContentIntelligenceSummary(
                pain_coherence_score=stage2_result.pain_coherence.get("score", 0.0),
                primary_pain_themes=stage2_result.pain_coherence.get("primary_pain_themes", []),
                org_stress_level=stage2_result.stress_indicators.get("level", "low"),
                solution_sophistication=stage2_result.solution_sophistication.get("level", "unaware"),
                stated_vs_actual_alignment=stage2_result.priority_alignment.get("aligned", True),
                trajectory_direction=stage2_result.trajectory.get("direction", "stable"),
                notable_absences=[
                    a.get("expected_topic", "") for a in stage2_result.absences
                ],
            )

        # Build why-now hypothesis
        why_now = WhyNowHypothesis(
            headline=why_now_data.get("headline", ""),
            narrative=why_now_data.get("narrative", ""),
            trigger_event=why_now_data.get("trigger_event"),
            trigger_date=_safe_parse_date(why_now_data.get("trigger_date")),
            window_estimate=why_now_data.get("window_estimate", "90 days"),
        )

        # Build confidence assessment
        confidence = ConfidenceAssessment(
            overall_confidence=confidence_data.get("overall", "low"),
            extracted_signals=confidence_data.get("extracted_signals", []),
            interpolated_signals=confidence_data.get("interpolated_signals", []),
            generated_signals=confidence_data.get("generated_signals", []),
            counter_signals=stage4_result.get("counter_signals", []) if stage4_result else [],
            unknowns=confidence_data.get("unknowns", []),
            corpus_size=corpus.total_items,
            corpus_quality="high" if corpus.total_items >= 10 else "medium" if corpus.total_items >= 5 else "low",
            corpus_sufficient=corpus.meets_minimum,
        )

        if corpus.total_items < 5 or not corpus.meets_minimum:
            confidence.overall_confidence = "low"

        # Determine journey position from stage 2
        journey_position = 0.0
        journey_label = "status_quo"
        journey_velocity = "stable"
        if stage2_result:
            pain_score = stage2_result.pain_coherence.get("score", 0.0)
            soph = stage2_result.solution_sophistication.get("level", "unaware")
            soph_map = {
                "decided": 0.80, "evaluating": 0.55, "articulate": 0.35,
                "frustrated": 0.20, "unaware": 0.05,
            }
            journey_position = max(pain_score, soph_map.get(soph, 0.05))

            if journey_position >= 0.60:
                journey_label = "decision_ready"
            elif journey_position >= 0.40:
                journey_label = "active_evaluation"
            elif journey_position >= 0.25:
                journey_label = "solution_exploring"
            elif journey_position >= 0.15:
                journey_label = "problem_aware"
            else:
                journey_label = "status_quo"

            urgency_trend = stage2_result.trajectory.get("urgency_trend", "stable")
            if urgency_trend == "increasing":
                journey_velocity = "accelerating"
            elif urgency_trend == "decreasing":
                journey_velocity = "stalling"

        # Build play
        play = _build_play(
            play_data=play_data,
            journey_label=journey_label,
            stage2_result=stage2_result,
            account=account,
            contacts=contacts,
        )

        # Generate angles if we have person analyses
        if run_llm and person_analyses and stage2_result:
            angles = await self.chain.generate_angles(
                account=account,
                person_analyses=person_analyses,
                why_now_headline=why_now.headline,
                pain_themes=ci_summary.primary_pain_themes if ci_summary else [],
                stress_level=ci_summary.org_stress_level if ci_summary else "unknown",
                play=play,
            )
            play.angles = angles

        # Build analyzed account
        budget = self.llm.get_budget()
        analyzed = AnalyzedAccount(
            account_slug=account.slug,
            company_name=account.company_name,
            domain=account.domain,
            analysis_date=current_date,
            prompt_version=PRISM_PROMPT_VERSION,
            scores=scores,
            journey_position=journey_position,
            journey_position_label=journey_label,
            journey_velocity=journey_velocity,
            why_now=why_now,
            content_intelligence=ci_summary,
            stage2_synthesis=stage2_result,
            person_analyses=person_analyses,
            confidence=confidence,
            signals=signals,
            total_input_tokens=budget.total_input_tokens if run_llm else 0,
            total_output_tokens=budget.total_output_tokens if run_llm else 0,
            total_api_calls=budget.total_calls if run_llm else 0,
            estimated_cost_usd=budget.estimated_cost if run_llm else 0.0,
            limited_analysis=corpus.total_items == 0 or not run_llm,
            limited_analysis_reason=(
                "No public content corpus" if corpus.total_items == 0
                else "LLM analysis skipped" if not run_llm
                else None
            ),
        )

        brief = AccountBrief(
            company_name=account.company_name,
            priority_tier=scores.priority_tier,
            composite_score=scores.composite_score,
            one_line_why_now=why_now.headline,
            discovery_questions=discovery_questions,
            collection_gaps=collection_gaps,
        )

        return analyzed, play, brief


def _build_play(
    play_data: dict,
    journey_label: str,
    stage2_result: object,
    account: Account,
    contacts: list[ContactRecord],
) -> Play:
    """Build play from LLM output or rules-based fallback."""
    if play_data and play_data.get("play_name"):
        return Play(
            play_name=play_data.get("play_name", ""),
            description=play_data.get("description", ""),
            sequence=play_data.get("sequence", []),
            timeline=play_data.get("timeline", ""),
            entry_point=play_data.get("entry_point"),
            fallback_play=play_data.get("fallback_play"),
        )

    stress_level = "low"
    if stage2_result and hasattr(stage2_result, "stress_indicators"):
        stress_level = stage2_result.stress_indicators.get("level", "low")

    fb = lookup_play_fallback(
        journey_label=journey_label,
        stress_level=stress_level,
        tech_stack_erp=account.tech_stack.erp_accounting,
    )

    entry_contact = None
    for c in contacts:
        if c.buying_role == "champion":
            entry_contact = f"{c.name} ({c.title})"
            break
    if not entry_contact and contacts:
        entry_contact = f"{contacts[0].name} ({contacts[0].title})"

    return Play(
        play_name=fb["play"],
        description=fb["description"],
        sequence=fb["sequence"],
        timeline=fb["timeline"],
        entry_point=entry_contact,
        fallback_play="Standard nurture sequence",
    )


def _safe_parse_date(date_str: object) -> date | None:
    """Safely parse a date string."""
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        return None
