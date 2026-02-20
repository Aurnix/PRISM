"""Tests for the dossier renderer."""

from datetime import date

import pytest

from prism.models.account import Account
from prism.models.analysis import (
    AnalyzedAccount,
    ConfidenceAssessment,
    ContentIntelligenceSummary,
    ScoreBreakdown,
    WhyNowHypothesis,
)
from prism.models.activation import AccountBrief, Play
from prism.models.signal import Signal
from prism.output.dossier import render_dossier


@pytest.fixture
def analyzed_account(sample_account, sample_contacts, sample_signals) -> AnalyzedAccount:
    """Create a complete analyzed account for dossier rendering."""
    return AnalyzedAccount(
        account_slug="test_company",
        company_name="Test Corp",
        domain="testcorp.com",
        analysis_date=date(2026, 2, 20),
        prompt_version="v1",
        scores=ScoreBreakdown(
            icp_fit_score=0.88,
            icp_components={
                "funding_stage_fit": 1.0,
                "growth_rate": 0.85,
                "tech_stack_fit": 1.0,
                "headcount_fit": 1.0,
                "industry_fit": 1.0,
                "geo_fit": 1.0,
            },
            buying_readiness_score=0.65,
            readiness_components={
                "journey_position": 0.80,
                "pain_coherence": 0.70,
                "new_leader_signal": 1.0,
                "org_stress_indicators": 0.40,
                "solution_sophistication": 0.30,
                "active_evaluation_signals": 0.45,
            },
            timing_score=0.72,
            timing_components={
                "trigger_event_recency": 0.85,
                "signal_freshness_avg": 0.80,
                "urgency_indicators": 0.75,
                "window_closing_signals": 1.0,
            },
            composite_score=0.73,
            priority_tier="tier_1",
        ),
        journey_position=0.45,
        journey_position_label="active_evaluation",
        journey_velocity="accelerating",
        why_now=WhyNowHypothesis(
            headline="New VP Finance at scaling Series B with legacy QuickBooks stack and 18-day close cycle",
            narrative="Test Corp's recent $28M Series B and hire of VP Finance Jane Smith from Stripe signals imminent finance infrastructure investment. Smith's LinkedIn posts explicitly reference the 18-day close cycle as unsustainable, and her Stripe background suggests high standards for financial tooling. The combination of fresh funding, a change agent in the champion seat, and explicit pain signals creates a strong buying window.",
            trigger_event="VP Finance hire from Stripe",
            trigger_date=date(2025, 11, 1),
            window_estimate="60 days",
        ),
        content_intelligence=ContentIntelligenceSummary(
            pain_coherence_score=0.72,
            primary_pain_themes=["Month-end close efficiency", "Financial visibility", "Scaling finance operations"],
            org_stress_level="elevated",
            solution_sophistication="articulate",
            stated_vs_actual_alignment=True,
            trajectory_direction="declining",
            notable_absences=["No mention of audit preparation despite Series C timeline"],
        ),
        confidence=ConfidenceAssessment(
            overall_confidence="high",
            extracted_signals=["Series B funding", "VP Finance hire", "QuickBooks usage at scale"],
            interpolated_signals=["NetSuite evaluation interest from job posting"],
            generated_signals=["Series C preparation creating finance urgency"],
            counter_signals=["CTO has no public content — technical buy-in unknown"],
            unknowns=["Current month-end close process details", "Budget allocation for finance tools"],
            corpus_size=8,
            corpus_quality="medium",
            corpus_sufficient=True,
        ),
        signals=sample_signals,
        total_api_calls=12,
        total_input_tokens=45000,
        total_output_tokens=8000,
        estimated_cost_usd=0.255,
    )


class TestDossierRendering:
    """Tests for dossier rendering."""

    def test_dossier_contains_all_sections(self, sample_account, analyzed_account, sample_contacts):
        dossier = render_dossier(sample_account, analyzed_account, sample_contacts)

        assert "P R I S M" in dossier
        assert "SECTION 1: EXECUTIVE SUMMARY" in dossier
        assert "SECTION 2: SUBJECT PROFILE" in dossier
        assert "SECTION 3: ORGANIZATIONAL INTELLIGENCE ASSESSMENT" in dossier
        assert "SECTION 4: KEY PERSONNEL" in dossier
        assert "SECTION 5: SIGNAL TIMELINE" in dossier
        assert "SECTION 6: WHY NOW" in dossier
        assert "SECTION 7: RECOMMENDED PLAY" in dossier
        assert "SECTION 8: COLLECTION GAPS" in dossier
        assert "SECTION 9: APPENDIX" in dossier
        assert "END DOSSIER" in dossier

    def test_dossier_contains_company_info(self, sample_account, analyzed_account, sample_contacts):
        dossier = render_dossier(sample_account, analyzed_account, sample_contacts)

        assert "Test Corp" in dossier
        assert "testcorp.com" in dossier
        assert "Series B" in dossier
        assert "QuickBooks Online" in dossier

    def test_dossier_contains_scores(self, sample_account, analyzed_account, sample_contacts):
        dossier = render_dossier(sample_account, analyzed_account, sample_contacts)

        assert "Composite Score:" in dossier
        assert "ICP Fit:" in dossier
        assert "Buying Readiness:" in dossier
        assert "Timing:" in dossier

    def test_dossier_contains_tier(self, sample_account, analyzed_account, sample_contacts):
        dossier = render_dossier(sample_account, analyzed_account, sample_contacts)
        assert "TIER 1" in dossier

    def test_dossier_contains_contacts(self, sample_account, analyzed_account, sample_contacts):
        dossier = render_dossier(sample_account, analyzed_account, sample_contacts)
        assert "Jane Smith" in dossier
        assert "Mike Chen" in dossier
        assert "Sarah Lee" in dossier

    def test_dossier_contains_signals(self, sample_account, analyzed_account, sample_contacts):
        dossier = render_dossier(sample_account, analyzed_account, sample_contacts)
        assert "Series B closed" in dossier or "funding_round" in dossier.lower()

    def test_dossier_contains_why_now(self, sample_account, analyzed_account, sample_contacts):
        dossier = render_dossier(sample_account, analyzed_account, sample_contacts)
        assert "New VP Finance" in dossier

    def test_dossier_contains_counter_signals(self, sample_account, analyzed_account, sample_contacts):
        dossier = render_dossier(sample_account, analyzed_account, sample_contacts)
        assert "counter" in dossier.lower() or "CTO has no public content" in dossier

    def test_dossier_has_discovery_questions(self, sample_account, analyzed_account, sample_contacts):
        brief = AccountBrief(
            company_name="Test Corp",
            priority_tier="tier_1",
            composite_score=0.73,
            discovery_questions=[
                "What is your current month-end close timeline?",
                "Have you evaluated any accounting platforms recently?",
                "What's the timeline for your Series C process?",
            ],
        )
        dossier = render_dossier(sample_account, analyzed_account, sample_contacts, brief=brief)
        assert "month-end close timeline" in dossier

    def test_dossier_with_play(self, sample_account, analyzed_account, sample_contacts):
        play = Play(
            play_name="direct_solution",
            description="They're actively looking. Skip education, go direct.",
            sequence=["personalized_demo_offer", "roi_calculator", "reference_call"],
            timeline="3-day accelerated",
            entry_point="Jane Smith (VP Finance)",
        )
        dossier = render_dossier(sample_account, analyzed_account, sample_contacts, play=play)
        assert "Direct Solution" in dossier
        assert "Jane Smith" in dossier

    def test_dossier_not_empty(self, sample_account, analyzed_account, sample_contacts):
        dossier = render_dossier(sample_account, analyzed_account, sample_contacts)
        assert len(dossier) > 1000  # Should be substantial

    def test_dossier_uses_box_drawing_chars(self, sample_account, analyzed_account, sample_contacts):
        dossier = render_dossier(sample_account, analyzed_account, sample_contacts)
        assert "═" in dossier
        assert "━" in dossier
        assert "─" in dossier
        assert "├" in dossier
        assert "└" in dossier
