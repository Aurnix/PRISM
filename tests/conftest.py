"""Shared test fixtures for PRISM tests."""

from datetime import date

import pytest

from prism.models.account import Account, Firmographics, TechStack
from prism.models.contact import ContactRecord, LinkedInPost
from prism.models.signal import Signal


@pytest.fixture
def sample_account() -> Account:
    """A well-qualified Series B SaaS company."""
    return Account(
        slug="test_company",
        company_name="Test Corp",
        domain="testcorp.com",
        blog_url="https://testcorp.com/blog",
        firmographics=Firmographics(
            founded_year=2021,
            headcount=180,
            headcount_growth_12mo=0.34,
            funding_stage="Series B",
            total_raised=42_000_000,
            last_round_amount=28_000_000,
            last_round_date=date(2025, 9, 15),
            last_round_lead="Sequoia Capital",
            industry="SaaS",
            hq_location="San Francisco, CA",
            description="B2B payments platform for scaling SaaS companies",
        ),
        tech_stack=TechStack(
            erp_accounting="QuickBooks Online",
            crm="HubSpot",
            payment_processor="Stripe",
            cloud_provider="AWS",
            primary_languages=["TypeScript", "Python"],
            stack_maturity="early",
            migration_signals=["Job posting references NetSuite evaluation"],
        ),
    )


@pytest.fixture
def sample_contacts() -> list[ContactRecord]:
    """Sample buying committee."""
    return [
        ContactRecord(
            name="Jane Smith",
            title="VP Finance",
            linkedin_url="https://linkedin.com/in/janesmith",
            start_date_current_role=date(2025, 11, 1),
            previous_company="Stripe",
            previous_title="Senior Controller",
            buying_role="champion",
            buying_role_confidence=0.9,
            linkedin_posts=[
                LinkedInPost(
                    date=date(2026, 2, 8),
                    text="Month-end close is still taking us 18 days. When you're growing 30%+ YoY, every day of delayed financial visibility is a day of flying blind. We need to fix this before our Series C process starts.",
                ),
                LinkedInPost(
                    date=date(2026, 1, 15),
                    text="Excited to join Test Corp as VP Finance! Coming from Stripe where I saw firsthand what modern finance infrastructure looks like. Ready to build something great here.",
                ),
            ],
        ),
        ContactRecord(
            name="Mike Chen",
            title="CEO",
            linkedin_url="https://linkedin.com/in/mikechen",
            start_date_current_role=date(2021, 3, 1),
            buying_role="economic_buyer",
            buying_role_confidence=0.85,
            linkedin_posts=[
                LinkedInPost(
                    date=date(2026, 1, 28),
                    text="Board meeting prep reminder: if your finance team needs 3 weeks to close the books, your board is making decisions on data that's already a month old. We're fixing this.",
                ),
            ],
        ),
        ContactRecord(
            name="Sarah Lee",
            title="CTO",
            linkedin_url="https://linkedin.com/in/sarahlee",
            start_date_current_role=date(2022, 1, 15),
            buying_role="technical_gatekeeper",
            buying_role_confidence=0.7,
            linkedin_posts=[],
        ),
    ]


@pytest.fixture
def sample_signals() -> list[Signal]:
    """Sample signal timeline."""
    return [
        Signal(
            signal_type="funding_round",
            description="$28M Series B closed",
            source="Crunchbase",
            detected_date=date(2025, 9, 15),
            confidence="extracted",
        ),
        Signal(
            signal_type="new_executive_finance",
            description="VP Finance hired from Stripe",
            source="LinkedIn",
            detected_date=date(2025, 11, 1),
            confidence="extracted",
        ),
        Signal(
            signal_type="job_posting_finance",
            description="Senior Accountant role posted — mentions QuickBooks and month-end close improvement",
            source="LinkedIn Jobs",
            detected_date=date(2026, 2, 1),
            confidence="extracted",
        ),
        Signal(
            signal_type="migration_signal",
            description="Job posting references NetSuite evaluation",
            source="LinkedIn Jobs",
            detected_date=date(2026, 1, 20),
            confidence="interpolated",
        ),
        Signal(
            signal_type="linkedin_post_pain",
            description="VP Finance posts about 18-day close cycle",
            source="LinkedIn",
            detected_date=date(2026, 2, 8),
            confidence="extracted",
        ),
    ]


@pytest.fixture
def underqualified_account() -> Account:
    """A poorly-qualified small bootstrapped company."""
    return Account(
        slug="small_co",
        company_name="Small Co",
        domain="smallco.com",
        firmographics=Firmographics(
            founded_year=2024,
            headcount=15,
            headcount_growth_12mo=0.10,
            funding_stage="Pre-seed",
            total_raised=500_000,
            industry="Non-tech",
            hq_location="Rural, MT",
        ),
        tech_stack=TechStack(
            erp_accounting="Spreadsheets",
            stack_maturity="early",
        ),
    )
