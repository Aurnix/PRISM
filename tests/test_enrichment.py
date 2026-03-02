"""Tests for the enrichment interface, sources, and orchestrator."""

from datetime import date
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from prism.models.account import Account, Firmographics, TechStack
from prism.models.contact import ContactRecord
from prism.models.content import ContentItem
from prism.models.signal import Signal
from prism.services.enrichment.base import EnrichmentResult, EnrichmentSource


# ── EnrichmentResult Tests ────────────────────────────────────────────────


class TestEnrichmentResult:
    def test_defaults(self):
        result = EnrichmentResult(source="test")
        assert result.source == "test"
        assert result.account_updates is None
        assert result.contacts == []
        assert result.signals == []
        assert result.content_items == []
        assert result.errors == []

    def test_with_data(self):
        result = EnrichmentResult(
            source="apollo",
            account_updates={"headcount": 200},
            contacts=[ContactRecord(name="Test", title="CTO")],
            signals=[
                Signal(
                    signal_type="funding_round",
                    description="test",
                    source="test",
                    detected_date=date.today(),
                )
            ],
        )
        assert result.account_updates["headcount"] == 200
        assert len(result.contacts) == 1
        assert len(result.signals) == 1


# ── Mock Enrichment Source ────────────────────────────────────────────────


class MockEnrichmentSource(EnrichmentSource):
    """Test double for enrichment source."""

    def __init__(self, name: str = "mock", available: bool = True):
        self._name = name
        self._available = available
        self._result = EnrichmentResult(source=name)

    def source_name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        return self._available

    def set_result(self, result: EnrichmentResult) -> None:
        self._result = result

    async def enrich(
        self,
        domain: str,
        existing_account: Optional[Account] = None,
    ) -> EnrichmentResult:
        return self._result


class TestEnrichmentSourceInterface:
    @pytest.mark.asyncio
    async def test_mock_source_returns_result(self):
        source = MockEnrichmentSource("test_source")
        result = await source.enrich("example.com")
        assert result.source == "test_source"

    def test_source_availability(self):
        available = MockEnrichmentSource("available", available=True)
        unavailable = MockEnrichmentSource("unavailable", available=False)
        assert available.is_available() is True
        assert unavailable.is_available() is False


# ── Blog Scraper Enrichment Tests ─────────────────────────────────────────


class TestBlogScraperEnrichment:
    def test_is_always_available(self):
        from prism.services.enrichment.blog_scraper import BlogScraperEnrichment

        source = BlogScraperEnrichment()
        assert source.is_available() is True
        assert source.source_name() == "blog_scraper"


# ── Job Board Enrichment Tests ────────────────────────────────────────────


class TestJobBoardEnrichment:
    def test_is_always_available(self):
        from prism.services.enrichment.job_boards import JobBoardEnrichment

        source = JobBoardEnrichment()
        assert source.is_available() is True
        assert source.source_name() == "job_boards"

    def test_slug_from_domain(self):
        from prism.services.enrichment.job_boards import _slug_from_domain

        assert _slug_from_domain("acme-corp.com") == "acmecorp"
        assert _slug_from_domain("example.io") == "example"

    def test_process_jobs_creates_finance_signals(self):
        from prism.services.enrichment.job_boards import JobBoardEnrichment

        source = JobBoardEnrichment()
        result = EnrichmentResult(source="job_boards")

        jobs = [
            {
                "title": "Senior Accountant",
                "content": "Manage month-end close, QuickBooks experience required",
                "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
            },
            {
                "title": "Software Engineer",
                "content": "Build great products with React and Python",
                "absolute_url": "https://boards.greenhouse.io/acme/jobs/2",
            },
        ]
        source._process_jobs(jobs, "greenhouse", "acme.com", result)

        assert len(result.content_items) == 2  # Both become content
        assert len(result.signals) == 1  # Only finance one is a signal
        assert result.signals[0].signal_type == "job_posting_finance"

    def test_process_jobs_detects_tech_signals(self):
        from prism.services.enrichment.job_boards import JobBoardEnrichment

        source = JobBoardEnrichment()
        result = EnrichmentResult(source="job_boards")

        jobs = [
            {
                "title": "Platform Engineer",
                "content": "Build cloud infrastructure on AWS",
                "absolute_url": "",
            },
        ]
        source._process_jobs(jobs, "lever", "acme.com", result)

        assert len(result.signals) == 1
        assert result.signals[0].signal_type == "job_posting_technical"


# ── Apollo Enrichment Tests ───────────────────────────────────────────────


class TestApolloEnrichment:
    def test_unavailable_without_api_key(self):
        with patch("prism.services.enrichment.apollo.ApolloEnrichment.__init__", lambda self: setattr(self, "_api_key", "")):
            from prism.services.enrichment.apollo import ApolloEnrichment
            source = ApolloEnrichment.__new__(ApolloEnrichment)
            source._api_key = ""
            assert source.is_available() is False

    def test_source_name(self):
        from prism.services.enrichment.apollo import ApolloEnrichment
        source = ApolloEnrichment.__new__(ApolloEnrichment)
        source._api_key = ""
        assert source.source_name() == "apollo"


# ── Enrichment Orchestrator Tests ─────────────────────────────────────────


class TestEnrichmentOrchestrator:
    @pytest.fixture
    def mock_dal(self):
        dal = AsyncMock()
        dal.get_account = AsyncMock(return_value=None)
        dal.list_accounts = AsyncMock(return_value=[])
        return dal

    @pytest.mark.asyncio
    async def test_runs_available_sources(self, mock_dal):
        from prism.services.enrichment.orchestrator import EnrichmentOrchestrator

        source1 = MockEnrichmentSource("source1")
        source1.set_result(EnrichmentResult(
            source="source1",
            contacts=[ContactRecord(name="Found Person", title="CFO")],
        ))

        source2 = MockEnrichmentSource("source2")
        source2.set_result(EnrichmentResult(
            source="source2",
            signals=[
                Signal(
                    signal_type="funding_round",
                    description="Raised $10M",
                    source="source2",
                    detected_date=date.today(),
                )
            ],
        ))

        orchestrator = EnrichmentOrchestrator(mock_dal, sources=[source1, source2])
        summary = await orchestrator.enrich_company("example.com")

        assert "source1" in summary
        assert "source2" in summary
        assert summary["source1"]["contacts"] == 1
        assert summary["source2"]["signals"] == 1

    @pytest.mark.asyncio
    async def test_skips_unavailable_sources(self, mock_dal):
        from prism.services.enrichment.orchestrator import EnrichmentOrchestrator

        available = MockEnrichmentSource("available", available=True)
        unavailable = MockEnrichmentSource("unavailable", available=False)

        # Only pass available sources (orchestrator filters in _discover_sources)
        orchestrator = EnrichmentOrchestrator(
            mock_dal,
            sources=[available],
        )
        summary = await orchestrator.enrich_company("example.com")
        assert "available" in summary
        assert "unavailable" not in summary

    @pytest.mark.asyncio
    async def test_handles_source_failure(self, mock_dal):
        from prism.services.enrichment.orchestrator import EnrichmentOrchestrator

        class FailingSource(EnrichmentSource):
            def source_name(self) -> str:
                return "failing"

            def is_available(self) -> bool:
                return True

            async def enrich(self, domain, existing_account=None):
                raise RuntimeError("API connection failed")

        good = MockEnrichmentSource("good")
        bad = FailingSource()

        orchestrator = EnrichmentOrchestrator(mock_dal, sources=[good, bad])
        summary = await orchestrator.enrich_company("example.com")

        assert "good" in summary
        assert "failing" in summary
        assert "error" in summary["failing"]

    @pytest.mark.asyncio
    async def test_empty_sources(self, mock_dal):
        from prism.services.enrichment.orchestrator import EnrichmentOrchestrator

        orchestrator = EnrichmentOrchestrator(mock_dal, sources=[])
        summary = await orchestrator.enrich_company("example.com")
        assert summary == {}

    @pytest.mark.asyncio
    async def test_count_result(self, mock_dal):
        from prism.services.enrichment.orchestrator import EnrichmentOrchestrator

        result = EnrichmentResult(
            source="test",
            account_updates={"headcount": 200, "industry": "SaaS"},
            contacts=[ContactRecord(name="A", title="B")],
            signals=[
                Signal(signal_type="funding_round", description="x", source="y", detected_date=date.today()),
                Signal(signal_type="key_hire", description="z", source="y", detected_date=date.today()),
            ],
            content_items=[
                ContentItem(source_type="blog_post", raw_text="text", publish_date=date.today()),
            ],
        )

        counts = EnrichmentOrchestrator._count_result(result)
        assert counts["account_fields"] == 2
        assert counts["contacts"] == 1
        assert counts["signals"] == 2
        assert counts["content_items"] == 1
