"""Tests for the scoring engine."""

from datetime import date

import pytest

from prism.analysis.scoring import (
    calculate_buying_readiness,
    calculate_composite,
    calculate_icp_fit,
    calculate_timing,
    score_account,
    score_funding_stage,
    score_geo,
    score_growth_rate,
    score_headcount,
    score_industry,
    score_new_leader,
    score_tech_stack,
)
from prism.models.account import Account
from prism.models.contact import ContactRecord
from prism.models.signal import Signal


class TestFundingStageScoring:
    """Tests for funding stage scoring."""

    def test_series_b_is_perfect(self):
        assert score_funding_stage("Series B") == 1.0

    def test_series_c_is_high(self):
        assert score_funding_stage("Series C") == 0.95

    def test_series_a_with_sufficient_funding(self):
        assert score_funding_stage("Series A", total_raised=10_000_000) == 0.70

    def test_series_a_underfunded(self):
        assert score_funding_stage("Series A", total_raised=3_000_000) == 0.40

    def test_seed_with_good_raise(self):
        assert score_funding_stage("Seed", total_raised=3_000_000) == 0.30

    def test_seed_small_raise(self):
        assert score_funding_stage("Seed", total_raised=1_000_000) == 0.15

    def test_public_company(self):
        assert score_funding_stage("Public") == 0.20

    def test_unknown_stage(self):
        assert score_funding_stage(None) == 0.50

    def test_pre_seed(self):
        assert score_funding_stage("Pre-seed") == 0.10


class TestGrowthRateScoring:
    """Tests for growth rate scoring."""

    def test_high_growth(self):
        assert score_growth_rate(0.60) == 1.0

    def test_strong_growth(self):
        assert score_growth_rate(0.35) == 0.85

    def test_moderate_growth(self):
        assert score_growth_rate(0.20) == 0.60

    def test_low_growth(self):
        assert score_growth_rate(0.08) == 0.35

    def test_flat_declining(self):
        assert score_growth_rate(-0.05) == 0.10

    def test_unknown(self):
        assert score_growth_rate(None) == 0.50


class TestTechStackScoring:
    """Tests for tech stack scoring."""

    def test_quickbooks_large_company(self):
        assert score_tech_stack("QuickBooks Online", headcount=200) == 1.0

    def test_quickbooks_medium_company(self):
        assert score_tech_stack("QuickBooks Online", headcount=75) == 0.85

    def test_quickbooks_with_migration(self):
        result = score_tech_stack("QuickBooks Online", headcount=75, migration_signals=["Evaluating NetSuite"])
        assert result == 1.0  # 0.85 + 0.20 = 1.05, capped at 1.0

    def test_spreadsheets(self):
        assert score_tech_stack("Spreadsheets", headcount=100) == 0.90

    def test_netsuite_without_migration(self):
        assert score_tech_stack("NetSuite", headcount=200) == 0.30

    def test_netsuite_with_migration(self):
        result = score_tech_stack("NetSuite", headcount=200, migration_signals=["Unhappy with NetSuite"])
        assert result == pytest.approx(0.90, abs=0.01)  # 0.70 + 0.20

    def test_sap(self):
        assert score_tech_stack("SAP", headcount=500) == 0.10

    def test_unknown(self):
        assert score_tech_stack("", headcount=100) == 0.50


class TestHeadcountScoring:
    """Tests for headcount scoring."""

    def test_sweet_spot(self):
        assert score_headcount(200) == 1.0

    def test_lower_range(self):
        assert score_headcount(75) == 0.85

    def test_upper_range(self):
        assert score_headcount(400) == 0.75

    def test_too_small(self):
        assert score_headcount(20) == 0.10

    def test_too_large(self):
        assert score_headcount(2000) == 0.15

    def test_unknown(self):
        assert score_headcount(None) == 0.50


class TestIndustryScoring:
    """Tests for industry scoring."""

    def test_saas_perfect(self):
        assert score_industry("SaaS") == 1.0

    def test_fintech_high(self):
        assert score_industry("Fintech") == 0.95

    def test_ecommerce(self):
        assert score_industry("E-commerce") == 0.90

    def test_unknown_tech(self):
        assert score_industry("AI Platform") == 0.60  # "tech" fuzzy match

    def test_non_tech(self):
        assert score_industry("Construction") == 0.30


class TestGeoScoring:
    """Tests for geo scoring."""

    def test_sf(self):
        assert score_geo("San Francisco, CA") == 1.0

    def test_nyc(self):
        assert score_geo("New York, NY") == 1.0

    def test_us_non_hub(self):
        # Portland matches ", OR" pattern but not a major hub
        # However the geo scoring checks state abbreviations which match US
        assert score_geo("Portland, OR") >= 0.90

    def test_canada(self):
        # Toronto is in MAJOR_TECH_HUBS check but "Canada" triggers Canada path
        # The function checks TORONTO in MAJOR_TECH_HUBS first
        assert score_geo("Toronto, Canada") >= 0.80

    def test_uk(self):
        assert score_geo("London, UK") == 0.60

    def test_unknown(self):
        assert score_geo(None) == 0.50


class TestICPFit:
    """Tests for composite ICP fit scoring."""

    def test_perfect_account(self, sample_account):
        score, components = calculate_icp_fit(sample_account)
        assert score > 0.80
        assert components["funding_stage_fit"] == 1.0
        assert components["headcount_fit"] == 1.0

    def test_underqualified_account(self, underqualified_account):
        score, components = calculate_icp_fit(underqualified_account)
        assert score < 0.40

    def test_components_sum_correctly(self, sample_account):
        """Verify weighted components sum to the composite."""
        from prism.config import ICP_WEIGHTS
        score, components = calculate_icp_fit(sample_account)
        manual_sum = sum(components[k] * ICP_WEIGHTS[k] for k in ICP_WEIGHTS)
        assert score == pytest.approx(manual_sum, abs=0.001)


class TestNewLeaderSignal:
    """Tests for new leader signal scoring."""

    def test_new_vp_finance_in_sweet_spot(self, sample_contacts):
        # Jane Smith started 2025-11-01, ~112 days ago on 2026-02-20
        score = score_new_leader(sample_contacts, date(2026, 2, 20))
        assert score == 1.0

    def test_no_new_leaders(self):
        contacts = [
            ContactRecord(
                name="Old Timer",
                title="VP Finance",
                buying_role="champion",
                start_date_current_role=date(2020, 1, 1),
            )
        ]
        score = score_new_leader(contacts, date(2026, 2, 20))
        assert score == 0.0

    def test_very_new_leader(self):
        contacts = [
            ContactRecord(
                name="Brand New",
                title="VP Finance",
                buying_role="champion",
                start_date_current_role=date(2026, 2, 10),
            )
        ]
        score = score_new_leader(contacts, date(2026, 2, 20))
        assert score == 0.60  # < 30 days


class TestCompositeScoring:
    """Tests for composite score and tier assignment."""

    def test_tier_1(self):
        score, tier = calculate_composite(0.90, 0.80, 0.70)
        assert tier == "tier_1"
        assert score >= 0.70

    def test_tier_2(self):
        score, tier = calculate_composite(0.60, 0.50, 0.40)
        assert tier == "tier_2"

    def test_tier_3(self):
        score, tier = calculate_composite(0.40, 0.30, 0.20)
        assert tier == "tier_3"

    def test_not_qualified(self):
        score, tier = calculate_composite(0.10, 0.10, 0.10)
        assert tier == "not_qualified"
        assert score < 0.25


class TestScoreAccount:
    """Integration tests for the full scoring pipeline."""

    def test_full_scoring(self, sample_account, sample_contacts, sample_signals):
        breakdown = score_account(
            account=sample_account,
            contacts=sample_contacts,
            signals=sample_signals,
            current_date=date(2026, 2, 20),
        )
        assert breakdown.composite_score > 0.0
        assert breakdown.icp_fit_score > 0.0
        assert breakdown.priority_tier in ("tier_1", "tier_2", "tier_3", "not_qualified")
        assert len(breakdown.icp_components) == 6
        assert len(breakdown.readiness_components) == 6
        assert len(breakdown.timing_components) == 4

    def test_well_qualified_account_scores_high(self, sample_account, sample_contacts, sample_signals):
        breakdown = score_account(
            account=sample_account,
            contacts=sample_contacts,
            signals=sample_signals,
            current_date=date(2026, 2, 20),
        )
        assert breakdown.icp_fit_score > 0.75
        assert breakdown.priority_tier in ("tier_1", "tier_2")
