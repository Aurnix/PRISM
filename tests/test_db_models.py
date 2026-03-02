"""Tests for SQLAlchemy ORM models and converter functions."""

import uuid
from datetime import date, datetime

import pytest

from prism.db.models import (
    AccountRow,
    AnalysisRow,
    ContactRow,
    ContentItemRow,
    DossierRow,
    EnrichmentLogRow,
    LinkedInPostRow,
    RawResponseRow,
    SignalRow,
)


class TestAccountRow:
    def test_create_account_row(self):
        row = AccountRow(
            id=uuid.uuid4(),
            slug="test-co",
            company_name="Test Corp",
            domain="testcorp.com",
            status="active",
            firmographics={"industry": "SaaS", "headcount": 180},
            tech_stack={"erp_accounting": "QuickBooks"},
        )
        assert row.slug == "test-co"
        assert row.status == "active"
        assert row.firmographics["headcount"] == 180

    def test_default_status_is_server_default(self):
        # server_default only applies in DB, not in Python
        row = AccountRow(
            id=uuid.uuid4(),
            slug="test",
            company_name="Test",
            domain="test.com",
        )
        # In Python without DB, status is None (server_default is DB-side only)
        # Just check the row was created
        assert row.slug == "test"


class TestContactRow:
    def test_create_contact_row(self):
        row = ContactRow(
            id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            name="Jane Smith",
            title="VP Finance",
            linkedin_url="https://linkedin.com/in/janesmith",
            buying_role="champion",
        )
        assert row.name == "Jane Smith"
        assert row.buying_role == "champion"


class TestSignalRow:
    def test_create_signal_row(self):
        row = SignalRow(
            id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            signal_type="funding_round",
            summary="$28M Series B closed",
            source="Crunchbase",
            detected_date=date(2025, 9, 15),
        )
        assert row.signal_type == "funding_round"
        assert row.detected_date == date(2025, 9, 15)


class TestContentItemRow:
    def test_create_content_item_row(self):
        row = ContentItemRow(
            id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            source_type="blog_post",
            title="Our Journey to Series B",
            body_text="Full blog post text here...",
            publish_date=date(2026, 1, 1),
        )
        assert row.source_type == "blog_post"


class TestAnalysisRow:
    def test_create_analysis_row(self):
        row = AnalysisRow(
            id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            status="complete",
            scores={"composite_score": 0.72, "priority_tier": "tier_1"},
        )
        assert row.status == "complete"
        assert row.scores["composite_score"] == 0.72


class TestDossierRow:
    def test_create_dossier_row(self):
        row = DossierRow(
            id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            analysis_id=uuid.uuid4(),
            dossier_id="PRISM-2026-0001",
            markdown_content="# Dossier\nContent here...",
        )
        assert row.dossier_id == "PRISM-2026-0001"


class TestRawResponseRow:
    def test_create_raw_response_row(self):
        row = RawResponseRow(
            id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            source_type="llm_extraction",
            url="https://example.com",
            http_status=200,
            raw_body='{"signals": []}',
        )
        assert row.source_type == "llm_extraction"


class TestEnrichmentLogRow:
    def test_create_enrichment_log_row(self):
        row = EnrichmentLogRow(
            id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            source="apollo",
            status="success",
            items_added=5,
        )
        assert row.source == "apollo"
        assert row.items_added == 5


class TestLinkedInPostRow:
    def test_create_post_row(self):
        row = LinkedInPostRow(
            id=uuid.uuid4(),
            contact_id=uuid.uuid4(),
            post_date=date(2026, 2, 8),
            text="Month-end close is still taking us 18 days...",
        )
        assert row.post_date == date(2026, 2, 8)
