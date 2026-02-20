"""Tests for Content Intelligence chain — testing degradation and data handling.

Note: LLM output quality is evaluated manually by reading dossiers,
not by automated tests. These tests verify the chain handles edge
cases gracefully.
"""

from datetime import date

import pytest

from prism.models.account import Account, Firmographics, TechStack
from prism.models.analysis import Stage1Extraction, Stage2Synthesis
from prism.models.content import ContentCorpus, ContentItem


class TestStage1Extraction:
    """Tests for Stage 1 extraction model."""

    def test_default_extraction(self):
        ext = Stage1Extraction()
        assert ext.semantic["announcements"] == []
        assert ext.tonal["overall_tone"] == ""
        assert ext.raw_signals == []

    def test_extraction_with_data(self):
        ext = Stage1Extraction(
            content_title="Test Post",
            source_type="blog",
            publish_date=date(2026, 1, 15),
            semantic={"announcements": ["Series B raised"], "metrics": ["$28M"], "claims": []},
            tonal={"overall_tone": "confident", "certainty_level": "definitive", "emotional_register": "excited"},
        )
        assert ext.semantic["announcements"] == ["Series B raised"]
        assert ext.tonal["overall_tone"] == "confident"


class TestStage2Synthesis:
    """Tests for Stage 2 synthesis model."""

    def test_default_synthesis(self):
        syn = Stage2Synthesis()
        assert syn.pain_coherence["score"] == 0.0
        assert syn.stress_indicators["level"] == "low"
        assert syn.solution_sophistication["level"] == "unaware"

    def test_synthesis_with_high_pain(self):
        syn = Stage2Synthesis(
            pain_coherence={
                "score": 0.85,
                "primary_pain_themes": ["month-end close", "revenue recognition"],
                "scattered_complaints": [],
            },
            stress_indicators={"level": "elevated", "evidence": ["urgency in recent posts"]},
            solution_sophistication={"level": "articulate", "evidence": "clear requirements stated"},
        )
        assert syn.pain_coherence["score"] == 0.85
        assert syn.stress_indicators["level"] == "elevated"


class TestContentCorpus:
    """Tests for content corpus assembly."""

    def test_empty_corpus(self):
        corpus = ContentCorpus(
            account_slug="test",
            assembly_date=date(2026, 2, 20),
        )
        assert corpus.total_items == 0
        assert not corpus.meets_minimum

    def test_corpus_metadata_calculation(self):
        items = [
            ContentItem(
                source_type="blog",
                publish_date=date(2025, 10, 1),
                raw_text="First blog post with some content about the company.",
            ),
            ContentItem(
                source_type="blog",
                publish_date=date(2025, 12, 1),
                raw_text="Second blog post discussing operational challenges.",
            ),
            ContentItem(
                source_type="linkedin",
                publish_date=date(2026, 1, 15),
                raw_text="LinkedIn post about finance pain.",
            ),
            ContentItem(
                source_type="job_posting",
                publish_date=date(2026, 2, 1),
                raw_text="Job posting for Senior Accountant role at the company.",
            ),
            ContentItem(
                source_type="press",
                publish_date=date(2026, 2, 10),
                raw_text="Press release about company funding and growth plans.",
            ),
        ]
        corpus = ContentCorpus(
            account_slug="test",
            assembly_date=date(2026, 2, 20),
            items=items,
        )
        corpus._update_metadata()

        assert corpus.total_items == 5
        assert corpus.date_range_start == date(2025, 10, 1)
        assert corpus.date_range_end == date(2026, 2, 10)
        assert corpus.source_distribution["blog"] == 2
        assert corpus.source_distribution["linkedin"] == 1
        assert corpus.meets_minimum  # 5 items, > 60 days span

    def test_corpus_below_minimum(self):
        items = [
            ContentItem(
                source_type="blog",
                publish_date=date(2026, 2, 1),
                raw_text="Only blog post available for this company.",
            ),
        ]
        corpus = ContentCorpus(
            account_slug="test",
            assembly_date=date(2026, 2, 20),
            items=items,
        )
        corpus._update_metadata()

        assert corpus.total_items == 1
        assert not corpus.meets_minimum

    def test_content_item_word_count(self):
        item = ContentItem(
            source_type="blog",
            publish_date=date(2026, 1, 1),
            raw_text="This is a test post with exactly ten words here.",
        )
        assert item.word_count == 10


class TestGracefulDegradation:
    """Tests for graceful degradation scenarios."""

    def test_empty_corpus_produces_limited_flag(self):
        """With no content, analysis should flag limited analysis."""
        corpus = ContentCorpus(
            account_slug="test",
            assembly_date=date(2026, 2, 20),
        )
        assert corpus.total_items == 0
        assert not corpus.meets_minimum

    def test_small_corpus_below_minimum(self):
        """Corpus with < 5 items should not meet minimum."""
        items = [
            ContentItem(source_type="blog", publish_date=date(2026, 1, i + 1), raw_text=f"Post {i}")
            for i in range(3)
        ]
        corpus = ContentCorpus(
            account_slug="test",
            assembly_date=date(2026, 2, 20),
            items=items,
        )
        corpus._update_metadata()
        assert not corpus.meets_minimum

    def test_short_timespan_below_minimum(self):
        """Corpus spanning < 2 months should not meet minimum."""
        items = [
            ContentItem(source_type="blog", publish_date=date(2026, 2, i + 1), raw_text=f"Post {i}" * 20)
            for i in range(6)
        ]
        corpus = ContentCorpus(
            account_slug="test",
            assembly_date=date(2026, 2, 20),
            items=items,
        )
        corpus._update_metadata()
        assert not corpus.meets_minimum  # All within same month
