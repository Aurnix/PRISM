"""Content Intelligence analysis chain — the proprietary 4-stage LLM pipeline.

Stage 1: Per-item extraction (parallelizable)
Stage 2: Cross-corpus synthesis
Stage 3: Person-level analysis (per buying committee member)
Stage 4: Synthesis & composite scoring
"""

import asyncio
import json
import logging
from datetime import date
from pathlib import Path
from typing import Optional

from prism.config import PRISM_MAX_CORPUS_ITEMS, PRISM_MAX_PERSON_POSTS, PRISM_PROMPT_VERSION, PROMPTS_DIR
from prism.models.account import Account
from prism.models.analysis import (
    AnalyzedAccount,
    ConfidenceAssessment,
    ContentIntelligenceSummary,
    PersonAnalysis,
    ScoreBreakdown,
    Stage1Extraction,
    Stage2Synthesis,
    WhyNowHypothesis,
)
from prism.models.activation import Angle, Play
from prism.models.contact import ContactRecord
from prism.models.content import ContentCorpus, ContentItem
from prism.models.signal import Signal
from prism.services.llm_backend import LLMBackend

logger = logging.getLogger(__name__)


def _load_prompt(stage: str) -> str:
    """Load a prompt template from the prompts directory."""
    prompt_file = PROMPTS_DIR / PRISM_PROMPT_VERSION / f"{stage}.txt"
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
    return prompt_file.read_text()


class ContentIntelligenceChain:
    """The 4-stage Content Intelligence analysis pipeline."""

    def __init__(self, llm: Optional[LLMBackend] = None) -> None:
        if llm is None:
            from prism.services import get_llm_backend
            llm = get_llm_backend()
        self.llm = llm

    async def analyze(
        self,
        account: Account,
        corpus: ContentCorpus,
        contacts: list[ContactRecord],
        signals: list[Signal],
        current_date: Optional[date] = None,
    ) -> tuple[
        list[Stage1Extraction],
        Optional[Stage2Synthesis],
        list[PersonAnalysis],
        Optional[dict],
    ]:
        """Run the full 4-stage analysis chain.

        Args:
            account: Account to analyze.
            corpus: Assembled content corpus.
            contacts: Known contacts.
            signals: Known signals.
            current_date: Reference date.

        Returns:
            Tuple of (stage1_results, stage2_result, person_analyses, stage4_result).
        """
        if current_date is None:
            current_date = date.today()

        # Check minimum corpus
        if corpus.total_items < 1:
            logger.warning(
                "No content items for %s — skipping Content Intelligence",
                account.slug,
            )
            return [], None, [], None

        # Stage 1: Per-item extraction (parallelized)
        logger.info("Stage 1: Extracting from %d content items...", corpus.total_items)
        items = corpus.items[:PRISM_MAX_CORPUS_ITEMS]
        stage1_results = await self._run_stage1(account, items)

        if not stage1_results:
            logger.warning("Stage 1 produced no results for %s", account.slug)
            return [], None, [], None

        # Stage 2: Cross-corpus synthesis
        logger.info("Stage 2: Cross-corpus synthesis...")
        stage2_result = await self._run_stage2(account, stage1_results, corpus)

        # Stage 3: Person-level analysis (parallelized)
        contacts_with_content = [
            c for c in contacts
            if c.linkedin_posts and len(c.linkedin_posts) > 0
        ]
        person_analyses: list[PersonAnalysis] = []
        if contacts_with_content and stage2_result:
            logger.info("Stage 3: Analyzing %d contacts...", len(contacts_with_content))
            person_analyses = await self._run_stage3(
                account, contacts_with_content, stage2_result
            )

        # Stage 4: Synthesis & scoring
        logger.info("Stage 4: Final synthesis...")
        stage4_result = await self._run_stage4(
            account, stage2_result, person_analyses, signals
        )

        return stage1_results, stage2_result, person_analyses, stage4_result

    async def _run_stage1(
        self,
        account: Account,
        items: list[ContentItem],
    ) -> list[Stage1Extraction]:
        """Stage 1: Per-item extraction (parallelizable)."""
        prompt_template = _load_prompt("stage1_extraction")

        system_prompt = (
            "You are an organizational intelligence analyst. Extract structured "
            "signals from company-generated content at multiple layers beyond "
            "surface meaning. Report what's there, not what's expected. "
            "Do not editorialize. Do not speculate beyond what the text supports.\n\n"
            "OUTPUT FORMAT: JSON"
        )

        async def extract_single(item: ContentItem) -> Optional[Stage1Extraction]:
            user_prompt = prompt_template.format(
                company_name=account.company_name,
                source_type=item.source_type,
                author=item.author or "Unknown",
                author_role=item.author_role or "Unknown",
                publish_date=item.publish_date.isoformat(),
                raw_text=item.raw_text[:5000],  # Cap input
            )

            result = await self.llm.query_json(system_prompt, user_prompt)
            if result:
                return Stage1Extraction(
                    content_title=item.title,
                    source_type=item.source_type,
                    publish_date=item.publish_date,
                    semantic=result.get("semantic", {}),
                    pragmatic=result.get("pragmatic", {}),
                    tonal=result.get("tonal", {}),
                    structural=result.get("structural", {}),
                    raw_signals=result.get("raw_signals", []),
                )
            return None

        # Run extractions in parallel (batches of 5)
        results: list[Stage1Extraction] = []
        batch_size = 5
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            batch_results = await asyncio.gather(
                *(extract_single(item) for item in batch),
                return_exceptions=True,
            )
            for r in batch_results:
                if isinstance(r, Stage1Extraction):
                    results.append(r)
                elif isinstance(r, Exception):
                    logger.warning("Stage 1 extraction error: %s", r)

        return results

    async def _run_stage2(
        self,
        account: Account,
        stage1_results: list[Stage1Extraction],
        corpus: ContentCorpus,
    ) -> Optional[Stage2Synthesis]:
        """Stage 2: Cross-corpus synthesis."""
        prompt_template = _load_prompt("stage2_synthesis")

        # Serialize extractions chronologically
        sorted_results = sorted(
            stage1_results,
            key=lambda x: x.publish_date or date.min,
        )

        extractions_text = ""
        for i, ext in enumerate(sorted_results, 1):
            extractions_text += (
                f"\n--- Item {i}: {ext.content_title or 'Untitled'} "
                f"({ext.source_type}, {ext.publish_date}) ---\n"
                f"Semantic: {json.dumps(ext.semantic)}\n"
                f"Pragmatic: {json.dumps(ext.pragmatic)}\n"
                f"Tonal: {json.dumps(ext.tonal)}\n"
                f"Structural: {json.dumps(ext.structural)}\n"
                f"Raw signals: {json.dumps(ext.raw_signals)}\n"
            )

        date_range = "unknown"
        if corpus.date_range_start and corpus.date_range_end:
            date_range = f"{corpus.date_range_start} to {corpus.date_range_end}"

        system_prompt = (
            "You are an organizational intelligence analyst performing longitudinal "
            "analysis on a company's public communications. Identify patterns that "
            "are only visible across multiple documents over time. Do not summarize "
            "individual items. Analyze TRAJECTORY and PATTERNS.\n\nOUTPUT FORMAT: JSON"
        )

        user_prompt = prompt_template.format(
            n_items=len(sorted_results),
            date_range=date_range,
            company_name=account.company_name,
            industry=account.firmographics.industry or "Unknown",
            serialized_extractions=extractions_text,
        )

        result = await self.llm.query_json(system_prompt, user_prompt, max_tokens=4096)
        if result:
            return Stage2Synthesis(
                trajectory=result.get("trajectory", {}),
                absences=result.get("absences", []),
                pain_coherence=result.get("pain_coherence", {}),
                stress_indicators=result.get("stress_indicators", {}),
                priority_alignment=result.get("priority_alignment", {}),
                solution_sophistication=result.get("solution_sophistication", {}),
                meta_signals=result.get("meta_signals", []),
            )
        return None

    async def _run_stage3(
        self,
        account: Account,
        contacts: list[ContactRecord],
        synthesis: Stage2Synthesis,
    ) -> list[PersonAnalysis]:
        """Stage 3: Person-level analysis."""
        prompt_template = _load_prompt("stage3_person")

        system_prompt = (
            "You are analyzing public communications from a specific individual "
            "at a target company. Extract signals relevant to buying readiness, "
            "communication style, and decision-making approach.\n\nOUTPUT FORMAT: JSON"
        )

        pain_themes = synthesis.pain_coherence.get("primary_pain_themes", [])
        stress_level = synthesis.stress_indicators.get("level", "unknown")
        soph = synthesis.solution_sophistication.get("level", "unknown")
        trajectory = synthesis.trajectory.get("direction", "unknown")

        async def analyze_person(contact: ContactRecord) -> Optional[PersonAnalysis]:
            posts = contact.linkedin_posts[:PRISM_MAX_PERSON_POSTS]
            corpus_text = "\n\n".join(
                f"[{post.date}] {post.text}" for post in posts
            )

            user_prompt = prompt_template.format(
                contact_name=contact.name,
                contact_title=contact.title,
                company_name=account.company_name,
                contact_corpus=corpus_text,
                primary_pain_themes=", ".join(pain_themes) if pain_themes else "None identified",
                org_stress_level=stress_level,
                solution_sophistication=soph,
                trajectory_direction=trajectory,
            )

            result = await self.llm.query_json(system_prompt, user_prompt)
            if result:
                return PersonAnalysis(
                    contact_name=contact.name,
                    contact_title=contact.title,
                    pain_alignment=result.get("pain_alignment", {}),
                    buying_readiness=result.get("buying_readiness", {}),
                    messaging_resonance=result.get("messaging_resonance", {}),
                    influence_level=result.get("influence_level", {}),
                    recommended_approach=result.get("recommended_approach", ""),
                    recommended_avoid=result.get("recommended_avoid", ""),
                )
            return None

        results = await asyncio.gather(
            *(analyze_person(c) for c in contacts),
            return_exceptions=True,
        )

        analyses = []
        for r in results:
            if isinstance(r, PersonAnalysis):
                analyses.append(r)
            elif isinstance(r, Exception):
                logger.warning("Stage 3 analysis error: %s", r)

        return analyses

    async def _run_stage4(
        self,
        account: Account,
        synthesis: Optional[Stage2Synthesis],
        person_analyses: list[PersonAnalysis],
        signals: list[Signal],
    ) -> Optional[dict]:
        """Stage 4: Synthesis & composite scoring."""
        prompt_template = _load_prompt("stage4_scoring")

        system_prompt = (
            "You are a GTM intelligence analyst producing a final assessment "
            "of a target account. Synthesize all available data to produce an "
            "actionable intelligence brief.\n\nOUTPUT FORMAT: JSON"
        )

        # Build person analyses text
        person_text = ""
        for pa in person_analyses:
            person_text += (
                f"\n{pa.contact_name} ({pa.contact_title}):\n"
                f"  Buying readiness: {pa.buying_readiness.get('stage', 'unknown')}\n"
                f"  Messaging resonance: {pa.messaging_resonance.get('primary', 'unknown')}\n"
                f"  Pain alignment: {'ahead of org' if pa.pain_alignment.get('ahead_of_org') else 'aligned' if pa.pain_alignment.get('aligned') else 'behind org'}\n"
                f"  Approach: {pa.recommended_approach}\n"
            )
        if not person_text:
            person_text = "No person-level analysis available."

        # Build signal timeline
        signal_text = ""
        sorted_signals = sorted(signals, key=lambda s: s.detected_date, reverse=True)
        for s in sorted_signals:
            signal_text += (
                f"  [{s.detected_date}] {s.signal_type}: {s.description} "
                f"(source: {s.source}, decay: {s.decay_weight:.2f})\n"
            )
        if not signal_text:
            signal_text = "No signals available."

        f = account.firmographics
        t = account.tech_stack

        pain_themes = []
        stress_level = "unknown"
        soph = "unknown"
        trajectory = "unknown"
        urgency = "unknown"
        absences = []

        if synthesis:
            pain_themes = synthesis.pain_coherence.get("primary_pain_themes", [])
            stress_level = synthesis.stress_indicators.get("level", "unknown")
            soph = synthesis.solution_sophistication.get("level", "unknown")
            trajectory = synthesis.trajectory.get("direction", "unknown")
            urgency = synthesis.trajectory.get("urgency_trend", "unknown")
            absences = [a.get("expected_topic", "") for a in synthesis.absences]

        growth_str = f"{f.headcount_growth_12mo:.0%}" if f.headcount_growth_12mo else "Unknown"

        user_prompt = prompt_template.format(
            company_name=account.company_name,
            domain=account.domain,
            industry=f.industry or "Unknown",
            funding_stage=f.funding_stage or "Unknown",
            total_raised=f.total_raised or 0,
            headcount=f.headcount or "Unknown",
            growth_rate=growth_str,
            tech_stack=f"{t.erp_accounting or 'Unknown'} (CRM: {t.crm or 'Unknown'}, Cloud: {t.cloud_provider or 'Unknown'})",
            pain_coherence_score=synthesis.pain_coherence.get("score", 0.0) if synthesis else 0.0,
            pain_themes=", ".join(pain_themes) if pain_themes else "None identified",
            stress_level=stress_level,
            solution_sophistication=soph,
            trajectory_direction=trajectory,
            urgency_trend=urgency,
            notable_absences=", ".join(absences) if absences else "None identified",
            person_analyses=person_text,
            signal_timeline=signal_text,
        )

        return await self.llm.query_json(system_prompt, user_prompt, max_tokens=4096)

    async def generate_angles(
        self,
        account: Account,
        person_analyses: list[PersonAnalysis],
        why_now_headline: str,
        pain_themes: list[str],
        stress_level: str,
        play: Play,
    ) -> list[Angle]:
        """Generate personalized outreach angles for each analyzed contact."""
        prompt_template = _load_prompt("activation_angle")

        system_prompt = (
            "You are a sales strategist generating personalized outreach angles. "
            "Be specific, relevant, and non-generic. Reference actual signals.\n\n"
            "OUTPUT FORMAT: JSON"
        )

        async def generate_single(pa: PersonAnalysis) -> Optional[Angle]:
            user_prompt = prompt_template.format(
                company_name=account.company_name,
                why_now_headline=why_now_headline,
                pain_themes=", ".join(pain_themes),
                stress_level=stress_level,
                contact_name=pa.contact_name,
                contact_title=pa.contact_title,
                buying_role="champion" if pa.influence_level.get("inferred_role") == "authority" else "influencer",
                buying_readiness=pa.buying_readiness.get("stage", "unknown"),
                messaging_resonance=pa.messaging_resonance.get("primary", "pragmatist"),
                personal_pain_themes=", ".join(pa.pain_alignment.get("personal_pain_themes", [])),
                play_name=play.play_name,
                play_description=play.description,
            )

            result = await self.llm.query_json(system_prompt, user_prompt)
            if result:
                return Angle(
                    contact_name=pa.contact_name,
                    contact_title=pa.contact_title,
                    opening_angle=result.get("opening_angle", ""),
                    value_prop=result.get("value_prop", ""),
                    call_to_action=result.get("call_to_action", ""),
                    avoid_topics=result.get("avoid_topics", []),
                    likely_objection=result.get("likely_objection", ""),
                    objection_response=result.get("objection_response", ""),
                    confidence=result.get("confidence", "medium"),
                    notes_for_ae=result.get("notes_for_ae", ""),
                )
            return None

        results = await asyncio.gather(
            *(generate_single(pa) for pa in person_analyses),
            return_exceptions=True,
        )

        angles = []
        for r in results:
            if isinstance(r, Angle):
                angles.append(r)
            elif isinstance(r, Exception):
                logger.warning("Angle generation error: %s", r)

        return angles
